import random
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
from string import Template
import shutil
import tempfile

logger = logging.getLogger(__name__)
client = docker.from_env()

HOST_URL = 'brainpower-ai.net'
HOST_PORT_RANGE_START = 32768
HOST_PORT_RANGE_END = 60999
NGINX_SITES_DYNAMIC = '/etc/nginx/sites-dynamic'


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
                dynamic_url = f"{HOST_URL}:{host_port}/{user_id}/{file_name}"
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
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                exec_result = container.exec_run([
                    "sh", "-c",
                    f"echo {encoded_code} | base64 -d > /app/src/component.js"
                ])
                if exec_result.exit_code != 0:
                    raise Exception(f"Failed to update component.js in container: {exec_result.output.decode()}")
                break
            except docker.errors.APIError as e:
                if attempt == max_attempts - 1:
                    raise
                logger.warning(f"API error on attempt {attempt + 1}, retrying: {str(e)}")
                time.sleep(1)

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
                    logger.error(
                        f"Failed to create empty CSS file {css_file_path} in container: {exec_result.output.decode()}")
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
                        logger.error(
                            f"Failed to create empty file {import_path} in container: {exec_result.output.decode()}")
                    else:
                        logger.info(f"Created empty file {import_path} in container")

        exec_result = container.exec_run(["touch", "/app/src/component.js"])
        if exec_result.exit_code != 0:
            raise Exception(f"Failed to touch component.js in container: {exec_result.output.decode()}")
        logger.info("Touched component.js in container")

    except Exception as e:
        logger.error(f"Error updating code in container: {str(e)}", exc_info=True)
        raise


@api_view(['GET'])
def check_container_ready(request):
    container_id = request.GET.get('container_id')
    user_id = request.GET.get('user_id', 'default')
    file_name = request.GET.get('file_name')
    logger.info(
        f"Checking container readiness for container_id: {container_id}, user_id: {user_id}, file_name: {file_name}")

    if not container_id:
        return JsonResponse({'error': 'No container ID provided'}, status=400)

    try:
        container = client.containers.get(container_id)
        container.reload()
        container_status = container.status
        logger.info(f"Container status: {container_status}")

        # Get all logs and print them
        all_logs = container.logs(stdout=True, stderr=True).decode('utf-8').strip()
        logger.info(f"All container logs:\n{all_logs}")

        # Get recent logs
        recent_logs = container.logs(stdout=True, stderr=True, tail=50).decode('utf-8').strip()
        latest_log = recent_logs.split('\n')[-1] if recent_logs else "No recent logs"

        if container_status != 'running':
            return JsonResponse({'status': 'container_starting', 'log': latest_log})

        port_mapping = container.ports.get('3001/tcp')
        if not port_mapping:
            return JsonResponse({'status': 'waiting_for_port', 'log': latest_log})

        host_port = port_mapping[0]['HostPort']
        dynamic_url = f"http://{host_port}.{HOST_URL}/{user_id}/{file_name}"

        # Check for compilation status
        if "Compiled successfully!" in all_logs:
            return JsonResponse({
                'status': 'ready',
                'url': dynamic_url,
                'log': "Compiled successfully!"
            })
        elif "Starting the development server..." in all_logs:
            return JsonResponse({'status': 'compiling', 'log': "Starting the development server..."})
        else:
            return JsonResponse({'status': 'preparing', 'log': latest_log})

    except docker.errors.NotFound:
        return JsonResponse({'error': 'Container not found', 'log': 'Container not found'}, status=404)
    except Exception as e:
        logger.error(f"Error checking container status: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Error checking container status', 'details': str(e), 'log': str(e)}, status=500)


import os
import shutil
import socket


def get_available_port(start, end):
    while True:
        port = random.randint(start, end)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        if result != 0:
            return port


@api_view(['POST'])
def check_or_create_container(request):
    data = request.data
    code = data.get('main_code')
    language = data.get('language')
    user_id = data.get('user_id', '0')
    file_name = data.get('file_name', 'component.js')
    main_file_path = data.get('main_file_path', "Root/Project/DailyInspirationApp/component.js")

    logger.info(f"Received request to check or create container for user {user_id}, file {file_name}")

    if not all([code, language, file_name]):
        return JsonResponse({'error': 'Missing required fields'}, status=400)
    if language != 'react':
        return JsonResponse({'error': 'Unsupported language'}, status=400)

    react_renderer_path = '/home/ubuntu/brainpower-ai/react_renderer'
    container_name = f'react_renderer_{user_id}_{file_name}'

    try:
        container = client.containers.get(container_name)
        logger.info(f"Existing container found: {container_name}")

        if container.status != 'running':
            logger.info(f"Starting existing container: {container_name}")
            container.start()

        container.reload()
        host_port = container.ports.get('3001/tcp')[0]['HostPort']
        logger.info(f"Container {container_name} is running on port {host_port}")

    except docker.errors.NotFound:
        logger.info(f"Container {container_name} not found. Creating new container.")
        host_port = get_available_port(HOST_PORT_RANGE_START, HOST_PORT_RANGE_END)
        logger.info(f"Selected port {host_port} for new container")

        try:
            container = client.containers.run(
                'react_renderer',
                detach=True,
                name=container_name,
                environment={
                    'USER_ID': user_id,
                    'REACT_APP_USER_ID': user_id,
                    'FILE_NAME': file_name,
                    'PORT': str(3001),
                    'NODE_OPTIONS': '--max-old-space-size=8192'  # Increase Node.js memory limit
                },
                volumes={
                    os.path.join(react_renderer_path, 'src'): {'bind': '/app/src', 'mode': 'rw'},
                    os.path.join(react_renderer_path, 'public'): {'bind': '/app/public', 'mode': 'rw'},
                    os.path.join(react_renderer_path, 'package.json'): {'bind': '/app/package.json', 'mode': 'ro'},
                    os.path.join(react_renderer_path, 'package-lock.json'): {'bind': '/app/package-lock.json',
                                                                             'mode': 'ro'},
                },
                ports={'3001/tcp': host_port},
                mem_limit='8g',  # Increased to 8g
                memswap_limit='16g',  # Increased swap
                cpu_quota=100000,  # Increased to 100% of CPU
                restart_policy={"Name": "on-failure", "MaximumRetryCount": 5}
            )
            logger.info(f"New container created: {container_name}")
        except docker.errors.APIError as e:
            logger.error(f"Failed to create container: {str(e)}", exc_info=True)
            return JsonResponse({'error': f'Failed to create container: {str(e)}'}, status=500)

    try:
        update_code_internal(container, code, user_id, file_name, main_file_path)
        logger.info(f"Code updated in container {container_name}")
    except Exception as e:
        logger.error(f"Failed to update code in container: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'Failed to update code in container: {str(e)}'}, status=500)

    container.reload()
    port_mapping = container.ports.get('3001/tcp')
    if port_mapping:
        dynamic_url = f"http://{host_port}.{HOST_URL}/{user_id}/{file_name}"
        logger.info(f"Container {container_name} running successfully: {dynamic_url}")
        return JsonResponse({
            'status': 'success',
            'message': 'Container is running',
            'container_id': container.id,
            'url': dynamic_url,
            'can_deploy': True,
        })
    else:
        logger.error(f"Failed to get port mapping for container {container_name}")
        return JsonResponse({'error': 'Failed to get port mapping'}, status=500)


import time


@csrf_exempt
@api_view(['POST'])
def stop_container(request):
    container_id = request.data.get('container_id')
    user_id = request.data.get('user_id')
    file_name = request.data.get('file_name')

    if not container_id:
        return JsonResponse({'error': 'No container ID provided'}, status=400)

    try:
        container = client.containers.get(container_id)
    except docker.errors.NotFound:
        logger.info(f"Container {container_id} not found, considering it already removed")
        return JsonResponse({'status': 'Container not found, possibly already removed'})

    try:
        logger.info(f"Attempting to stop container {container_id}")
        container.stop(timeout=10)  # Give it 10 seconds to stop gracefully

        # Wait for the container to stop
        max_wait = 15
        start_time = time.time()
        while time.time() - start_time < max_wait:
            container.reload()
            if container.status == 'exited':
                break
            time.sleep(1)

        if container.status != 'exited':
            logger.warning(f"Container {container_id} did not stop gracefully, forcing removal")

        container.remove(force=True)
        logger.info(f"Container {container_id} stopped and removed successfully")
        return JsonResponse({'status': 'Container stopped and removed'})
    except Exception as e:
        logger.error(f"Error stopping container {container_id}: {str(e)}", exc_info=True)
        return JsonResponse({'error': f"Failed to stop container: {str(e)}"}, status=500)


import time


@csrf_exempt
@api_view(['POST'])
def update_code(request):
    container_id = request.data.get('container_id')
    main_code = request.data.get('main_code')
    user_id = request.data.get('user_id')
    file_name = request.data.get('file_name')
    main_file_path = request.data.get('main_file_path', "Root/Project")
    logger.info(
        f"Received update request for container: {container_id}, original file: {file_name}, main file path: {main_file_path}")

    if not all([container_id, main_code, user_id, main_file_path]):
        logger.warning("Missing required data in update request")
        return JsonResponse({'error': 'Missing required data'}, status=400)

    try:
        container = client.containers.get(container_id)

        # Check if the container is running
        container.reload()
        if container.status != 'running':
            logger.info(f"Container {container_id} is not running. Attempting to start it.")
            container.start()
            container.reload()

            # Wait for the container to be in the running state
            max_attempts = 10
            for _ in range(max_attempts):
                if container.status == 'running':
                    break
                time.sleep(1)
                container.reload()

            if container.status != 'running':
                raise Exception(f"Failed to start container {container_id}")

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


import re
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.http import JsonResponse
import logging
import docker
import json
from django.conf import settings
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)

NGINX_SITES_PATH = '/etc/nginx/sites-available'
NGINX_SITES_ENABLED_PATH = '/etc/nginx/sites-enabled'
REACT_APPS_ROOT = '/var/www/react-apps'


def update_index_html(file_path):
    with open(file_path, 'r') as file:
        content = file.read()

    # Update script src and link href to use relative paths
    content = re.sub(r'(src|href)="/static/', r'\1="./static/', content)

    with open(file_path, 'w') as file:
        file.write(content)


@method_decorator(csrf_exempt, name='dispatch')
class DeployToProductionView_dev(View):
    def options(self, request, *args, **kwargs):
        response = JsonResponse({})
        response["Access-Control-Allow-Origin"] = "http://localhost:3000"
        response["Access-Control-Allow-Methods"] = "POST, OPTIONS"
        response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type"
        return response

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            container_id = data.get('container_id')
            user_id = data.get('user_id')
            file_name = data.get('file_name')

            if not all([container_id, user_id, file_name]):
                return JsonResponse({'error': 'Missing required data'}, status=400)

            # 1. Run npm build in the container
            client = docker.from_env()
            container = client.containers.get(container_id)
            exec_result = container.exec_run("npm run build")
            if exec_result.exit_code != 0:
                raise Exception(f"Build failed: {exec_result.output.decode()}")

            # 2. Copy the build files from the container to a local directory
            app_name = f"{user_id}_{file_name.replace('.', '-')}"
            production_dir = os.path.join(settings.BASE_DIR, 'deployed_apps', app_name)

            # Remove existing directory if it exists
            if os.path.exists(production_dir):
                shutil.rmtree(production_dir)

            os.makedirs(production_dir, exist_ok=True)

            # Use docker cp to copy files from container to host
            os.system(f"docker cp {container_id}:/app/build/. {production_dir}")

            # Update index.html to use relative paths
            index_path = os.path.join(production_dir, 'index.html')
            update_index_html(index_path)

            # Print directory contents for debugging
            print(f"Contents of {production_dir}:")
            for root, dirs, files in os.walk(production_dir):
                level = root.replace(production_dir, '').count(os.sep)
                indent = ' ' * 4 * (level)
                print(f"{indent}{os.path.basename(root)}/")
                subindent = ' ' * 4 * (level + 1)
                for f in files:
                    print(f"{subindent}{f}")

            # 3. In a local environment, we'll skip Nginx configuration
            # Instead, we'll assume we're serving these files directly through Django

            # 4. Return the new URL to the client
            production_url = f"http://{request.get_host()}/deployed/{app_name}/"
            return JsonResponse({
                'status': 'success',
                'message': 'Application deployed locally',
                'production_url': production_url
            })

        except Exception as e:
            logger.error(f"Error in local deployment: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)


class ServeReactApp(TemplateView):
    template_name = 'index.html'

    def get_template_names(self):
        app_name = self.kwargs['app_name']
        template_path = f'{settings.DEPLOYED_COMPONENTS_ROOT}/{app_name}/index.html'
        return [template_path]


import json
import os
import shutil
import time
import logging
import docker
import subprocess
import psutil


from django.views import View
from django.http import JsonResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings


@method_decorator(csrf_exempt, name='dispatch')
class DeployToProductionView_prod(View):
    def create_deployment_container(self, user_id, file_name):
        client = docker.from_env()
        container_name = f'deploy_container_{user_id}_{file_name}_{int(time.time())}'

        try:
            container = client.containers.run(
                'react_renderer',
                name=container_name,
                command='tail -f /dev/null',  # Keep container running
                detach=True,
                environment={
                    'NODE_OPTIONS': '--max-old-space-size=8192',
                    'USER_ID': user_id,
                    'FILE_NAME': file_name,
                },
                mem_limit='8g',
                memswap_limit='16g',
                cpu_quota=100000,  # 100% of CPU
                volumes={
                    '/home/ubuntu/brainpower-ai/react_renderer/src': {'bind': '/app/src', 'mode': 'rw'},
                    '/home/ubuntu/brainpower-ai/react_renderer/public': {'bind': '/app/public', 'mode': 'rw'},
                    '/home/ubuntu/brainpower-ai/react_renderer/package.json': {'bind': '/app/package.json',
                                                                               'mode': 'ro'},
                    '/home/ubuntu/brainpower-ai/react_renderer/package-lock.json': {'bind': '/app/package-lock.json',
                                                                                    'mode': 'ro'},
                }
            )
            return container
        except docker.errors.APIError as e:
            raise Exception(f"Failed to create deployment container: {str(e)}")

    def post(self, request, *args, **kwargs):
        return StreamingHttpResponse(self.stream_deployment(request), content_type='text/plain')

    def stream_deployment(self, request):
        deployment_container = None
        build_successful = False
        try:
            data = json.loads(request.body)
            user_id = data.get('user_id')
            file_name = data.get('file_name')

            if not all([user_id, file_name]):
                yield "Error: Missing required data\n"
                return

            yield f"Starting deployment for user: {user_id}, file: {file_name}\n"

            deployment_container = self.create_deployment_container(user_id, file_name)

            yield "Deployment container created. Starting build process...\n"
            build_command = """
            cd /app && 
            export NODE_OPTIONS="--max-old-space-size=8192" &&
            export GENERATE_SOURCEMAP=false &&
            npm run build -- --verbose
            """
            exec_result = deployment_container.exec_run(
                f"sh -c '{build_command}'",
                stream=True
            )
            for line in exec_result.output:
                decoded_line = line.decode()
                yield f"Build process: {decoded_line}\n"
                if "Compiled successfully." in decoded_line:
                    build_successful = True

            if not build_successful:
                yield f"Build failed. Check the logs above for errors.\n"
                raise Exception("Build process failed")

            yield "Build completed successfully.\n"

            # Copy build files from the deployment container
            yield "Copying build files...\n"
            copy_start = time.time()
            app_name = f"{user_id}_{file_name.replace('.', '-')}"
            production_dir = os.path.join(settings.DEPLOYED_COMPONENTS_ROOT, app_name)

            if os.path.exists(production_dir):
                shutil.rmtree(production_dir)
            os.makedirs(production_dir, exist_ok=True)

            subprocess.run(["docker", "cp", f"{deployment_container.id}:/app/build/.", production_dir], check=True)
            yield f"Files copied successfully in {time.time() - copy_start:.2f} seconds\n"

            # Generate the URL for the deployed application
            production_url = f"http://{request.get_host()}/deployed/{app_name}/"
            yield f"Deployment completed. Production URL: {production_url}\n"

            yield json.dumps({
                "status": "success",
                "message": "Application deployed successfully",
                "production_url": production_url
            })

        except Exception as e:
            yield f"Error in deployment: {str(e)}\n"
            yield json.dumps({"status": "error", "message": str(e)})
        finally:
            if deployment_container:
                try:
                    deployment_container.stop()
                    deployment_container.remove()
                    yield f"Stopped and removed deployment container: {deployment_container.name}\n"
                except Exception as e:
                    yield f"Error stopping deployment container: {str(e)}\n"

    def create_nginx_config(self, app_name, app_path):
        logger.info(f"Creating Nginx config for {app_name}")
        config_content = f"""
    server {{
        listen 80;
        server_name {app_name}.{self.request.get_host()};

        location / {{
            alias {app_path};
            try_files $uri $uri/ /index.html;
        }}
    }}
        """

        config_file = os.path.join(NGINX_SITES_PATH, f"{app_name}")
        with open(config_file, 'w') as f:
            f.write(config_content)

        # Create symlink in sites-enabled if it doesn't exist
        symlink_path = os.path.join(NGINX_SITES_ENABLED_PATH, app_name)
        if not os.path.exists(symlink_path):
            os.symlink(config_file, symlink_path)

        logger.info(f"Nginx config created for {app_name}")

