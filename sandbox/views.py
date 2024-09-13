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
import tempfile

logger = logging.getLogger(__name__)
client = docker.from_env()


SERVER_IP = '13.61.3.236'  # Replace with your actual server IP
SERVER_PORT = 8000


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
                dynamic_url = f"http://localhost:{host_port}"
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

        logs = container.logs(tail=10).decode('utf-8').strip()
        latest_log = logs.split('\n')[-1] if logs else "No logs available"

        if container_status != 'running':
            return JsonResponse({'status': 'container_starting', 'log': latest_log})

        port_mapping = container.ports.get(f'{SERVER_PORT}/tcp')
        if not port_mapping:
            return JsonResponse({'status': 'waiting_for_port', 'log': latest_log})

        host_port = port_mapping[0]['HostPort']
        dynamic_url = f"http://{SERVER_IP}:{host_port}"

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
                return JsonResponse(
                    {'status': 'server_error', 'details': f'Server responded with status code {response.status_code}',
                     'log': latest_log})
        except requests.RequestException:
            return JsonResponse({'status': 'server_starting', 'log': latest_log})

    except docker.errors.NotFound:
        return JsonResponse({'error': 'Container not found', 'log': 'Container not found'}, status=404)
    except Exception as e:
        logger.error(f"Error checking container status: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Error checking container status', 'details': str(e), 'log': str(e)}, status=500)


@api_view(['POST'])
def check_or_create_container(request):
    logger.info(f"Received request data: {request.data}")
    code = request.data.get('main_code')
    language = request.data.get('language')
    user_id = request.data.get('user_id', '0')
    file_name = request.data.get('file_name', 'component.js')
    main_file_path = request.data.get('main_file_path', "Root/Project")
    if not all([code, language, file_name]):
        logger.warning(
            f"Missing required fields. code: {bool(code)}, language: {bool(language)}, file_name: {bool(file_name)}")
        return JsonResponse({'error': 'Missing required fields'}, status=400)
    if language != 'react':
        return JsonResponse({'error': 'Unsupported language'}, status=400)

    react_renderer_path = '/path/to/react_renderer'  # Update this path
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
                'PORT': str(SERVER_PORT)  # Set the server port
            },
            volumes={
                react_renderer_path: {'bind': '/app', 'mode': 'rw'}
            },
            ports={f'{SERVER_PORT}/tcp': None}  # Map to a random host port
        )

    update_code_internal(container, code, user_id, file_name, main_file_path)

    container.reload()
    port_mapping = container.ports.get(f'{SERVER_PORT}/tcp')
    if port_mapping:
        host_port = port_mapping[0]['HostPort']
        dynamic_url = f"http://{SERVER_IP}:{host_port}"
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


class DeployToProductionView_prod(View):
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

            # 2. Copy the build files from the container to the React apps directory
            app_name = f"{user_id}_{file_name.replace('.', '-')}"
            production_dir = os.path.join(REACT_APPS_ROOT, app_name)

            # Remove existing directory if it exists
            if os.path.exists(production_dir):
                shutil.rmtree(production_dir)

            os.makedirs(production_dir, exist_ok=True)

            # Use docker cp to copy files from container to host
            subprocess.run(["docker", "cp", f"{container_id}:/app/build/.", production_dir], check=True)

            # 3. Create Nginx configuration for the React app
            self.create_nginx_config(app_name, production_dir)

            # 4. Reload Nginx to apply changes
            subprocess.run(["sudo", "nginx", "-s", "reload"], check=True)

            # 5. Return the new URL to the client
            production_url = f"http://{request.get_host()}/deployed/{app_name}/"
            return JsonResponse({
                'status': 'success',
                'message': 'Application deployed to production',
                'production_url': production_url
            })

        except Exception as e:
            logger.error(f"Error in deploy_to_production: {str(e)}")
            return JsonResponse({'error': str(e)}, status=500)

    def create_nginx_config(self, app_name, app_path):
        config_content = f"""
    server {{
        listen 80;
        server_name {self.request.get_host()};

        location /{app_name} {{
            alias {app_path};
            try_files $uri $uri/ /{app_name}/index.html;
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