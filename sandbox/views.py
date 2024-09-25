import random
import traceback
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


@api_view(['GET'])
def check_container(request):
    container_id = request.GET.get('container_id')
    user_id = request.GET.get('user_id', 'default')
    file_name = request.GET.get('file_name')

    if not container_id:
        return JsonResponse({'error': 'No container ID provided'}, status=400)

    try:
        container = client.containers.get(container_id)
        container.reload()

        logs = container.logs(tail=50).decode('utf-8').strip()
        if "Accepting connections at http://localhost:3001" in logs:
            port_mapping = container.ports.get('3001/tcp')
            if port_mapping:
                host_port = port_mapping[0]['HostPort']
                return JsonResponse({
                    'status': 'ready',
                    'url': f"http://{host_port}.{HOST_URL}/dev",
                    'log': "Server is ready"
                })
            else:
                return JsonResponse({'status': 'waiting_for_port', 'log': "Waiting for port mapping"})
        else:
            return JsonResponse({'status': 'not_ready', 'log': logs.split('\n')[-1]})

    except docker.errors.NotFound:
        return JsonResponse({'error': 'Container not found', 'log': 'Container not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': 'Error checking container status', 'details': str(e), 'log': str(e)}, status=500)


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

            # Build the project
            exec_result = container.exec_run(["sh", "-c", "cd /app && yarn start"])
            if exec_result.exit_code != 0:
                raise Exception(f"Failed to build project: {exec_result.output.decode()}")

        logger.info("Project rebuilt and server restarted successfully")

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
        dynamic_url = f"http://{host_port}.{HOST_URL}/dev"

        # Check for compilation status
        if "Compiled successfully!" in all_logs:
            return JsonResponse({
                'status': 'ready',
                'url': dynamic_url,
                'log': "Compiled successfully!"
            })
        if "Compiled with warnings" in all_logs:
            return JsonResponse({
                'status': 'ready',
                'url': dynamic_url,
                'log': "Compiled successfully!"
            })
        if "Accepting connections at http://localhost:3001" in all_logs:
            return JsonResponse({
                'status': 'ready',
                'url': dynamic_url,
                'log': "Server is ready"
            })
        elif "Compiling..." in all_logs:
            return JsonResponse({'status': 'compiling', 'log': "Compiling..."})

        elif "Creating an optimized production build..." in all_logs:
            return JsonResponse({'status': 'building', 'log': "Creating an optimized production build..."})

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
    main_file_path = data.get('main_file_path')

    logger.info(f"Received request to check or create container for user {user_id}, file {file_name}, file path {main_file_path}")

    if not all([code, language, file_name]):
        return JsonResponse({'error': 'Missing required fields'}, status=400)
    if language != 'react':
        return JsonResponse({'error': 'Unsupported language'}, status=400)

    react_renderer_path = '/home/ubuntu/brainpower-ai/react_renderer'
    container_name = f'react_renderer_{user_id}_{file_name}'
    app_name = f"{user_id}_{file_name.replace('.', '-')}"
    try:
        container = client.containers.get(container_name)
        logger.info(f"Existing container found: {container_name}")

        if container.status != 'running':
            logger.info(f"Starting existing container: {container_name}")
            container.start()
            # Ensure the container builds and serves the production build
            command = [
                "sh", "-c", "yarn start"
            ]
            container.exec_run(command, detach=True)

        container.reload()
        host_port = container.ports.get('3001/tcp')[0]['HostPort']
        logger.info(f"Container {container_name} is running on port {host_port}")

    except docker.errors.NotFound:
        logger.info(f"Container {container_name} not found. Creating new container.")
        host_port = get_available_port(HOST_PORT_RANGE_START, HOST_PORT_RANGE_END)
        logger.info(f"Selected port {host_port} for new container")
        try:
            container = client.containers.run(
                'react_renderer_prod',
                command=[
                    "sh", "-c", "yarn start"
                ],  # Build and serve production
                detach=True,
                name=container_name,
                environment={
                    'USER_ID': user_id,
                    'REACT_APP_USER_ID': user_id,
                    'FILE_NAME': file_name,
                    'PORT': str(3001),
                    'NODE_ENV': 'production',  # Set to production
                    'NODE_OPTIONS': '--max-old-space-size=8192'
                },
                volumes={
                    os.path.join(react_renderer_path, 'src'): {'bind': '/app/src', 'mode': 'rw'},
                    os.path.join(react_renderer_path, 'public'): {'bind': '/app/public', 'mode': 'rw'},
                    os.path.join(react_renderer_path, 'package.json'): {'bind': '/app/package.json', 'mode': 'ro'},
                    os.path.join(react_renderer_path, 'package-lock.json'): {'bind': '/app/package-lock.json',
                                                                             'mode': 'ro'},
                    os.path.join(react_renderer_path, 'build'): {'bind': '/app/build', 'mode': 'rw'},  # Add this line
                },
                ports={'3001/tcp': host_port},
                mem_limit='8g',
                memswap_limit='16g',
                cpu_quota=100000,
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
        dynamic_url = f"http://{host_port}.{HOST_URL}/dev"
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


@csrf_exempt
@api_view(['POST'])
def stop_container(request):
    container_id = request.data.get('container_id')

    if not container_id:
        return JsonResponse({'error': 'No container ID provided'}, status=400)

    try:
        container = client.containers.get(container_id)
        container.stop(timeout=10)
        container.remove(force=True)
        return JsonResponse({'status': 'Container stopped and removed'})
    except docker.errors.NotFound:
        return JsonResponse({'status': 'Container not found, possibly already removed'})
    except Exception as e:
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
from channels.layers import get_channel_layer

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
            production_url = f"http://{request.get_host()}/deployed_apps/{app_name}/"
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

import pwd
import grp
import os
import json
import asyncio
import shutil
import logging
import traceback
import subprocess
from django.conf import settings
from django.http import JsonResponse
from django.views import View
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from docker import from_env as docker_from_env
import threading

# Initialize Docker client and logger
client = docker_from_env()
logger = logging.getLogger(__name__)

@method_decorator(csrf_exempt, name='dispatch')
class DeployToProductionView_prod(View):
    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.body)
            container_id = data.get('container_id')
            user_id = data.get('user_id')
            file_name = data.get('file_name')

            if not all([container_id, user_id, file_name]):
                return JsonResponse({"status": "error", "message": "Missing required data"}, status=400)

            task_id = f"deploy_{user_id}_{file_name}"

            # Start the deployment process in a separate thread
            threading.Thread(target=self.deploy_async, args=(container_id, user_id, file_name, task_id)).start()

            return JsonResponse({
                "status": "processing",
                "task_id": task_id,
                "message": "Deployment started"
            })
        except Exception as e:
            logger.error(f"Error initiating deployment: {str(e)}")
            return JsonResponse({"status": "error", "message": str(e)}, status=500)

    def deploy_async(self, container_id, user_id, file_name, task_id):
        channel_layer = get_channel_layer()
        try:
            self.send_update(channel_layer, task_id, "Starting deployment process...")

            container = client.containers.get(container_id)
            app_name = f"{user_id}_{file_name.replace('.', '-')}"
            production_dir = os.path.join(settings.DEPLOYED_COMPONENTS_ROOT, app_name)

            # Ensure the container is running
            if container.status != 'running':
                raise Exception(f"Container {container_id} is not running.")

            # Start production build without stopping yarn start
            self.send_update(channel_layer, task_id, "Starting production build...")
            build_command = f"""
            export NODE_OPTIONS="--max-old-space-size=8192" && \
            export GENERATE_SOURCEMAP=false && \
            export PUBLIC_URL="/deployed_apps/{app_name}" && \
            yarn build
            """
            exec_result = container.exec_run(["sh", "-c", build_command], demux=True)
            stdout, stderr = exec_result.output
            if exec_result.exit_code != 0:
                error_message = stderr.decode() if stderr else 'Unknown error'
                raise Exception(f"Build failed: {error_message}")

            # Remove existing production_dir if it exists
            if os.path.exists(production_dir):
                self.send_update(channel_layer, task_id, "Removing existing production directory...")
                shutil.rmtree(production_dir)

            # Create production_dir
            os.makedirs(production_dir, exist_ok=True)

            # Copy files from container to host
            self.send_update(channel_layer, task_id, "Copying build files...")
            copy_command = ["docker", "cp", f"{container_id}:/app/build/.", production_dir]
            copy_result = subprocess.run(copy_command, capture_output=True, text=True)
            if copy_result.returncode != 0:
                logger.error(f"Error copying files: {copy_result.stderr}")
                raise Exception(f"Failed to copy build files: {copy_result.stderr}")

            logger.info("Files copied successfully")

            # No need to adjust permissions since we're running as root

            production_url = f"/deployed_apps/{app_name}/index.html"
            self.send_update(channel_layer, task_id, "DEPLOYMENT_COMPLETE", production_url=production_url)

        except Exception as e:
            logger.error(f"Error in deployment: {str(e)}")
            self.send_update(channel_layer, task_id, f"Error: {str(e)}", error_trace=traceback.format_exc())


    def send_update(self, channel_layer, task_id, message, production_url=None, error_trace=None):
        update = {
            "type": "deployment_update",
            "message": message
        }
        if production_url:
            update["production_url"] = production_url
        if error_trace:
            update["error_trace"] = error_trace

        async_to_sync(channel_layer.group_send)(f"deployment_{task_id}", update)
        logger.info(f"Sent update for task {task_id}: {message}")






