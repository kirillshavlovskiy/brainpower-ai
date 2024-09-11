from socket import socket
import requests
import os
import base64
import re
from mylms import settings
from rest_framework.decorators import api_view as async_api_view
from docker.errors import NotFound, APIError
from courses.consumers import FileStructureConsumer
import os
import subprocess
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
import logging
import docker
import shutil

logger = logging.getLogger(__name__)
client = docker.from_env()


@csrf_exempt
@async_api_view(['POST'])
def check_container(request):
    user_id = request.data.get('user_id', '0')
    file_name = request.data.get('file_name', 'rendered_component')
    if not file_name:
        return JsonResponse({'error': 'Missing file_name'}, status=400)
    container_name = f'react_renderer_{user_id}_{file_name}'
    try:
        container = client.containers.get(container_name)
        if container.status == 'running':
            container.reload()
            port_mapping = container.ports.get('3001/tcp')
            if port_mapping:
                host_port = port_mapping[0]['HostPort']
                dynamic_url = f"http://localhost:{host_port}/{user_id}/{file_name}"
                return JsonResponse({
                    'status': 'running',
                    'container_id': container.id,
                    'url': dynamic_url,
                })
        return JsonResponse({'status': 'stopped'})
    except docker.errors.NotFound:
        return JsonResponse({'status': 'not_found'})
    except Exception as e:
        logger.error(f"Error checking container status: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


def update_code_internal(container, code, user, file_name, main_file_path):
    try:
        encoded_code = base64.b64encode(code.encode()).decode()
        exec_result = container.exec_run([
            "sh", "-c",
            f"echo {encoded_code} | base64 -d > /app/src/component.js"
        ])
        if exec_result.exit_code != 0:
            raise Exception(f"Failed to update component.js in container: {exec_result.output.decode()}")
        logger.info(f"Updated component.js in container with content from {file_name} at path {main_file_path}")
        logger.info(f"Processing for user: {user}")
        # Get the directory of the main file
        base_path = os.path.dirname(main_file_path)
        logger.info(f"Base path derived from main file: {base_path}")
        css_import_matches = re.findall(r"import\s+['\"](.+\.css)['\"];?", code)
        logger.info(f"Found CSS imports: {css_import_matches}")
        for css_file_path in css_import_matches:
            logger.info(f"Attempting to retrieve content for CSS file: {css_file_path}")
            css_content = FileStructureConsumer.get_file_content_for_container(user, css_file_path, base_path)
            if css_content is not None:
                logger.info(f"Retrieved content for CSS file: {css_file_path}")
                encoded_css = base64.b64encode(css_content.encode()).decode()
                container_css_path = f"/app/src/{css_file_path}"
                exec_result = container.exec_run([
                    "sh", "-c",
                    f"mkdir -p $(dirname {container_css_path}) && echo {encoded_css} | base64 -d > {container_css_path}"
                ])
                if exec_result.exit_code != 0:
                    logger.error(f"Failed to update {css_file_path} in container: {exec_result.output.decode()}")
                    raise Exception(f"Failed to update {css_file_path} in container: {exec_result.output.decode()}")
                logger.info(f"Updated {css_file_path} in container")
            else:
                logger.warning(f"CSS file {css_file_path} not found or empty. Creating empty file in container.")
                container_css_path = f"/app/src/{css_file_path}"
                exec_result = container.exec_run([
                    "sh", "-c",
                    f"mkdir -p $(dirname {container_css_path}) && touch {container_css_path}"
                ])
                if exec_result.exit_code != 0:
                    logger.error(f"Failed to create empty CSS file {css_file_path} in container: {exec_result.output.decode()}")
                else:
                    logger.info(f"Created empty CSS file {css_file_path} in container")

        # Handle other imports (if any)
        import_pattern = r"import\s+(?:(?:{\s*[\w\s,]+\s*})|(?:[\w]+))\s+from\s+['\"](.+?)['\"]"
        imports = re.findall(import_pattern, code)

        for import_path in imports:
            if import_path.endswith('.js') or import_path.endswith('.json'):
                file_content = FileStructureConsumer.get_file_content_for_container(user, import_path, base_path)
                if file_content is not None:
                    encoded_content = base64.b64encode(file_content.encode()).decode()
                    container_path = f"/app/src/{import_path}"
                    exec_result = container.exec_run([
                        "sh", "-c",
                        f"mkdir -p $(dirname {container_path}) && echo {encoded_content} | base64 -d > {container_path}"
                    ])
                    if exec_result.exit_code != 0:
                        raise Exception(f"Failed to update {import_path} in container: {exec_result.output.decode()}")
                    logger.info(f"Updated {import_path} in container")
                else:
                    logger.warning(f"File {import_path} not found or empty. Creating empty file in container.")
                    container_path = f"/app/src/{import_path}"
                    exec_result = container.exec_run([
                        "sh", "-c",
                        f"mkdir -p $(dirname {container_path}) && touch {container_path}"
                    ])
                    if exec_result.exit_code != 0:
                        logger.error(f"Failed to create empty file {import_path} in container: {exec_result.output.decode()}")
                    else:
                        logger.info(f"Created empty file {import_path} in container")

        exec_result = container.exec_run(["touch", "/app/src/component.js"])
        if exec_result.exit_code != 0:
            raise Exception(f"Failed to touch component.js in container: {exec_result.output.decode()}")
        logger.info("Touched component.js in container")

    except Exception as e:
        logger.error(f"Error updating code in container: {str(e)}", exc_info=True)
        raise


@csrf_exempt
@api_view(['POST'])
def check_or_create_container(request):
    logger.info(f"Received request data: {request.data}")
    code = request.data.get('main_code')
    language = request.data.get('language')
    user_id = request.data.get('user_id', '0')
    file_name = request.data.get('file_name', 'component.js')
    main_file_path = request.data.get('main_file_path', "Root/Project")
    if not all([code, language, file_name]):
        logger.warning(f"Missing required fields. code: {bool(code)}, language: {bool(language)}, file_name: {bool(file_name)}")
        return JsonResponse({'error': 'Missing required fields'}, status=400)
    if language != 'react':
        return JsonResponse({'error': 'Unsupported language'}, status=400)
    react_renderer_path = '/Users/kirillshavlovskiy/mylms/react_renderer'
    container_name = f'react_renderer_{user_id}_{file_name}'
    try:
        container = client.containers.get(container_name)
        if container.status != 'running':
            container.start()
        logger.info(f"Using existing container: {container_name}")
    except docker.errors.NotFound:
        logger.info(f"Creating new container: {container_name}")
        container = client.containers.run(
            'react_renderer',
            detach=True,
            name=container_name,
            environment={
                'USER_ID': user_id,
                'REACT_APP_USER_ID': user_id,
                'FILE_NAME': file_name,
            },
            volumes={
                react_renderer_path: {'bind': '/app', 'mode': 'rw'}
            },
            ports={'3001/tcp': None}
        )

    update_code_internal(container, code, user_id, file_name, main_file_path)

    container.reload()
    port_mapping = container.ports.get('3001/tcp')
    if port_mapping:
        host_port = port_mapping[0]['HostPort']
        dynamic_url = f"http://localhost:{host_port}/{user_id}/{file_name}"
        logger.info(f"Dynamic URL: {dynamic_url}")
        return JsonResponse({
            'status': 'success',
            'message': 'Container is running',
            'container_id': container.id,
            'url': dynamic_url,
            'can_deploy': True,
        })
    else:
        return JsonResponse({'error': 'Failed to get port mapping'}, status=500)


@csrf_exempt
@api_view(['POST'])
def stop_container(request):
    container_id = request.data.get('container_id')
    user_id = request.data.get('user_id')
    file_name = request.data.get('file_name')
    if not container_exists(container_id):
        return JsonResponse({'status': 'Container not found, possibly already removed'})

    try:
        container = client.containers.get(container_id)
        container.stop()
        container.remove()
        return JsonResponse({'status': 'Container stopped and removed'})
    except Exception as e:
        logger.error(f"Error stopping container: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@csrf_exempt
@api_view(['POST'])
def update_code(request):
    container_id = request.data.get('container_id')
    main_code = request.data.get('main_code')
    user_id = request.data.get('user_id')
    file_name = request.data.get('file_name')
    main_file_path = request.data.get('main_file_path', "Root/Project")  # Get this from the request
    logger.info(f"Received update request for container: {container_id}, original file: {file_name}, main file path: {main_file_path}")

    if not all([container_id, main_code, user_id, main_file_path]):
        logger.warning("Missing required data in update request")
        return JsonResponse({'error': 'Missing required data'}, status=400)

    try:
        container = client.containers.get(container_id)
        update_code_internal(container, main_code, user_id, file_name, main_file_path)
        return JsonResponse({'status': 'Code updated successfully'})

    except docker.errors.NotFound:
        logger.error(f"Container not found: {container_id}")
        return JsonResponse({'error': 'Container not found'}, status=404)
    except Exception as e:
        logger.error(f"Error updating code: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

def container_exists(container_id):
    try:
        client.containers.get(container_id)
        return True
    except docker.errors.NotFound:
        return False

@csrf_exempt
@api_view(['GET'])
def check_container_ready(request):
    container_id = request.GET.get('container_id')
    user_id = request.GET.get('user_id', 'default')
    file_name = request.GET.get('file_name')
    logger.info(f"Checking container readiness for container_id: {container_id}, user_id: {user_id}, file_name: {file_name}")

    if not container_id:
        return JsonResponse({'error': 'No container ID provided'}, status=400)

    try:
        container = client.containers.get(container_id)
        container.reload()
        container_status = container.status
        logger.info(f"Container status: {container_status}")

        # Get the latest logs
        logs = container.logs(tail=10).decode('utf-8').strip()
        latest_log = logs.split('\n')[-1] if logs else "No logs available"

        if container_status != 'running':
            return JsonResponse({'status': 'container_starting', 'log': latest_log})

        # Get the assigned port
        port_mapping = container.ports.get('3001/tcp')
        if not port_mapping:
            return JsonResponse({'status': 'waiting_for_port', 'log': latest_log})

        host_port = port_mapping[0]['HostPort']
        dynamic_url = f"http://localhost:{host_port}/{user_id}/{file_name}"

        # Check if the dev server is responding and the content is available
        try:
            response = requests.get(dynamic_url, timeout=5)
            if response.status_code == 200:
                if 'root' in response.text and 'react' in response.text.lower():
                    return JsonResponse({
                        'status': 'ready',
                        'url': dynamic_url,
                        'log': latest_log
                    })
                else:
                    return JsonResponse({'status': 'content_loading', 'log': latest_log})
            else:
                return JsonResponse({'status': 'server_error', 'details': f'Server responded with status code {response.status_code}', 'log': latest_log})
        except requests.RequestException:
            return JsonResponse({'status': 'server_starting', 'log': latest_log})

    except docker.errors.NotFound:
        return JsonResponse({'error': 'Container not found', 'log': 'Container not found'}, status=404)
    except Exception as e:
        logger.error(f"Error checking container status: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Error checking container status', 'details': str(e), 'log': str(e)}, status=500)

@csrf_exempt
@api_view(['POST'])
def deploy_to_production(request):
    container_id = request.data.get('container_id')
    user_id = request.data.get('user_id')
    file_name = request.data.get('file_name')

    if not all([container_id, user_id, file_name]):
        return JsonResponse({'error': 'Missing required data'}, status=400)

    try:
        # 1. Run npm build in the container
        container = client.containers.get(container_id)
        exec_result = container.exec_run("npm run build")
        if exec_result.exit_code != 0:
            raise Exception(f"Build failed: {exec_result.output.decode()}")

        # 2. Copy the build files from the container
        subdomain = f"{user_id}-{file_name.replace('.', '-')}"
        production_dir = os.path.join(settings.PRODUCTION_APPS_ROOT, subdomain)
        if os.path.exists(production_dir):
            shutil.rmtree(production_dir)
        os.makedirs(production_dir, exist_ok=True)

        # Use docker cp to copy files from container to host
        subprocess.run(f"docker cp {container_id}:/app/build/. {production_dir}", shell=True, check=True)

        # 3. Start a simple HTTP server for the app
        port = find_available_port()
        start_http_server(production_dir, port)

        # 4. Return the new URL to the client
        production_url = f"http://localhost:{port}"
        return JsonResponse({
            'status': 'success',
            'message': 'Application deployed to production',
            'production_url': production_url
        })

    except Exception as e:
        logger.error(f"Error in deploy_to_production: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

def find_available_port(start_port=8000, max_port=9000):
    for port in range(start_port, max_port):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.bind(("", port))
            s.close()
            return port
        except OSError:
            continue
    raise IOError("No free ports")

def start_http_server(directory, port):
    os.chdir(directory)
    subprocess.Popen(["python", "-m", "http.server", str(port)])

# Make sure to stop any running servers when the Django server stops
import atexit

@atexit.register
def stop_all_servers():
    subprocess.run(["pkill", "-f", "python -m http.server"])


