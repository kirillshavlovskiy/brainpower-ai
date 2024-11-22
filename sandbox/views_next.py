from datetime import datetime
import time
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
import os
import shutil
import socket
import json

logger = logging.getLogger(__name__)
client = docker.from_env()

HOST_URL = 'brainpower-ai.net'
HOST_PORT_RANGE_START = 32768
HOST_PORT_RANGE_END = 60999
NGINX_SITES_DYNAMIC = '/etc/nginx/sites-dynamic'

# Add this with other global variables at the top
react_renderer_path = os.path.join(settings.BASE_DIR, 'react_renderer')


class CompilationMessages:
    NEXT_READY = "Ready in"
    NEXT_COMPILING = "Compiling"
    NEXT_BUILDING = "Creating an optimized production build"
    NEXT_ERROR = "Failed to compile"
    NEXT_WARNING = "Compiled with warnings"


class ContainerStatus:
    CREATING = 'creating'
    WARNING = 'warning'
    BUILDING = 'building'
    COMPILING = 'compiling'
    READY = 'ready'
    FAILED = 'failed'
    COMPILATION_FAILED = 'compilation_failed'
    ERROR = 'error'
    NOT_FOUND = 'not_found'


class DetailedLogger:
    def __init__(self):
        self.logs = []
        self.file_list = []

    def log(self, level, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S,%f")[:-3]
        log_entry = f"{timestamp} {level.upper()} {message}"
        self.logs.append(log_entry)
        logger.log(getattr(logging, level.upper()), message)

    def add_file(self, file_path, size, creation_date):
        self.file_list.append({
            'path': file_path,
            'size': size,
            'created_at': creation_date
        })

    def get_logs(self):
        return "\n".join(self.logs)

    def get_file_list(self):
        return self.file_list


detailed_logger = DetailedLogger()

import time

from docker.errors import NotFound, APIError


def exec_command_with_retry(container, command, max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            container.reload()  # Refresh container status
            if container.status != 'running':
                logger.info(f"Container {container.id} is not running. Attempting to start it.")
                container.start()
                container.reload()
                time.sleep(5)  # Wait for container to fully start

            exec_id = container.client.api.exec_create(container.id, command)
            output = container.client.api.exec_start(exec_id)
            exec_info = container.client.api.exec_inspect(exec_id)

            if exec_info['ExitCode'] != 0:
                raise Exception(f"Command failed with exit code {exec_info['ExitCode']}: {output.decode()}")

            return output  # This is already bytes
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds...")
            time.sleep(delay)


# In views.py - Update container info handling

@api_view(['GET'])
def check_container(request):
    user_id = request.GET.get('user_id', '0')
    file_name = request.GET.get('file_name', 'test-component.js')
    container_name = f'react_renderer_next_{user_id}_{file_name}'

    try:
        container = client.containers.get(container_name)
        container.reload()

        # Basic container info that's always available
        container_info = {
            'container_name': container.name,
            'created_at': container.attrs.get('Created', 'N/A'),
            'status': container.status,
            'id': container.id
        }

        # Optional container info
        try:
            container_info.update({
                'ports': container.ports or {},
                'image': container.image.tags[0] if container.image.tags else 'Unknown'
            })
        except Exception as e:
            logger.warning(f"Non-critical container info error: {str(e)}")

        if container.status == 'running':
            port_mapping = container.ports.get('3001/tcp')
            file_structure = get_container_file_structure(container)

            if port_mapping:
                host_port = port_mapping[0]['HostPort']
                return JsonResponse({
                    'status': 'ready',
                    'container_id': container.id,
                    'container_info': container_info,
                    'url': f"https://{host_port}.{HOST_URL}",
                    'file_list': file_structure or [],
                    'detailed_logs': container.logs(tail=50).decode('utf-8')
                })
            else:
                return JsonResponse({
                    'status': 'not_ready',
                    'container_id': container.id,
                    'container_info': container_info
                })
        else:
            return JsonResponse({
                'status': 'not_ready',
                'container_id': container.id,
                'container_info': container_info
            })

    except docker.errors.NotFound:
        return JsonResponse({
            'status': 'not_found',
            'container_info': {
                'container_name': container_name,
                'status': 'not_found'
            }
        })
    except Exception as e:
        logger.error(f"Error checking container: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'container_info': {
                'container_name': container_name,
                'status': 'error'
            }
        }, status=500)


def set_container_permissions(container):
    """Set proper permissions for container directories and mount style files"""
    try:
        # First, ensure the container is running
        container.reload()
        if container.status != 'running':
            logger.error(f"Container not running, status: {container.status}")
            return False

        # Define config path
        config_path = "/home/ubuntu/brainpower-ai/react_renderer_next"
        logger.info(f"Using config path: {config_path}")

        # Create directories
        init_commands = [
            "mkdir -p /app/components/dynamic",
            "mkdir -p /app/src/app",
            "mkdir -p /app/src/lib",
            "mkdir -p /app/styles",
            "touch /app/compilation_status"
        ]

        for cmd in init_commands:
            result = container.exec_run(cmd, user='root')
            if result.exit_code != 0:
                logger.error(f"Failed to execute {cmd}: {result.output.decode()}")
                return False

        # Mount configuration files from working directory
        files_to_mount = {
            "/app/tailwind.config.ts": f"{config_path}/tailwind.config.ts",
            "/app/postcss.config.js": f"{config_path}/postcss.config.js",
            "/app/src/app/globals.css": f"{config_path}/src/app/globals.css",
            "/app/src/lib/utils.ts": f"{config_path}/src/lib/utils.ts"
        }

        # Mount and verify each file
        for container_path, host_path in files_to_mount.items():
            try:
                # Check if host file exists
                if not os.path.exists(host_path):
                    logger.error(f"Host file does not exist: {host_path}")
                    continue

                # Read host file
                with open(host_path, 'r') as f:
                    content = f.read()
                    encoded_content = base64.b64encode(content.encode()).decode()

                # Create directory if needed
                dir_path = os.path.dirname(container_path)
                container.exec_run(f"mkdir -p {dir_path}", user='root')

                # Write to container
                result = container.exec_run(
                    ["sh", "-c", f"echo {encoded_content} | base64 -d > {container_path}"],
                    user='root'
                )
                if result.exit_code != 0:
                    logger.error(f"Failed to mount {host_path} to {container_path}: {result.output.decode()}")
                    continue

                # Verify file content in container
                verify_result = container.exec_run(f"cat {container_path}")
                if verify_result.exit_code != 0:
                    logger.error(f"Failed to verify {container_path}: {verify_result.output.decode()}")
                    continue

                logger.info(f"Successfully mounted and verified {container_path}")

            except Exception as e:
                logger.error(f"Failed to process {host_path}: {str(e)}")
                continue

        # Set permissions
        perm_commands = [
            "chown -R node:node /app/components",
            "chown -R node:node /app/src",
            "chown -R node:node /app/styles",
            "chown node:node /app/compilation_status",
            "chown node:node /app/tailwind.config.ts",
            "chown node:node /app/postcss.config.js",
            "chmod -R 755 /app/components",
            "chmod -R 755 /app/src",
            "chmod -R 755 /app/styles",
            "chmod 644 /app/compilation_status",
            "chmod 644 /app/tailwind.config.ts",
            "chmod 644 /app/postcss.config.js"
        ]

        for cmd in perm_commands:
            result = container.exec_run(cmd, user='root')
            if result.exit_code != 0:
                logger.error(f"Failed to execute {cmd}: {result.output.decode()}")
                return False

        # Final verification
        logger.info("Verifying final container state:")
        verify_commands = [
            "ls -la /app/components/dynamic",
            "ls -la /app/src/app",
            "ls -la /app/src/lib",
            "ls -la /app/tailwind.config.ts",
            "ls -la /app/postcss.config.js",
            "ls -la /app/src/app/globals.css",
            "ls -la /app/src/lib/utils.ts"
        ]

        for cmd in verify_commands:
            result = container.exec_run(cmd)
            logger.info(f"{cmd}: {result.output.decode()}")

        logger.info("Container files and permissions set successfully")
        return True

    except Exception as e:
        logger.error(f"Error setting container permissions: {str(e)}")
        return False


def update_code_internal(container, code, user, file_name, main_file_path):
    files_added = []
    build_output = []
    try:
        # Write component code directly - directory already exists
        target_path = "/app/components/dynamic/placeholder.tsx"
        logger.info(f"Writing component to path: {target_path}")

        encoded_code = base64.b64encode(code.encode()).decode()
        exec_result = container.exec_run([
            "sh", "-c",
            f"echo {encoded_code} | base64 -d > {target_path}"
        ], user='node')

        if exec_result.exit_code != 0:
            raise Exception(f"Failed to write component to {target_path}: {exec_result.output.decode()}")

        files_added.append(target_path)
        logger.info(f"Successfully wrote component to {target_path}")

        # Get container logs to check compilation status
        logs = container.logs(tail=100).decode('utf-8')
        compilation_status = ContainerStatus.COMPILING

        # Check Next.js specific messages
        if CompilationMessages.NEXT_READY in logs:
            compilation_status = ContainerStatus.READY
            logger.info("Next.js compilation successful")
        elif CompilationMessages.NEXT_WARNING in logs:
            compilation_status = ContainerStatus.WARNING
            logger.warning("Next.js compilation completed with warnings")
        elif CompilationMessages.NEXT_ERROR in logs:
            compilation_status = ContainerStatus.COMPILATION_FAILED
            logger.error("Next.js compilation failed")

        return logs, files_added, compilation_status

    except Exception as e:
        logger.error(f"Error updating code in container: {str(e)}", exc_info=True)
        raise


def get_compilation_status(container):
    try:
        recent_logs = container.logs(tail=100).decode('utf-8')

        # Check for Next.js specific messages
        if CompilationMessages.NEXT_READY in recent_logs:
            return ContainerStatus.READY
        elif CompilationMessages.NEXT_WARNING in recent_logs:
            return ContainerStatus.WARNING
        elif CompilationMessages.NEXT_ERROR in recent_logs:
            return ContainerStatus.COMPILATION_FAILED
        elif CompilationMessages.NEXT_COMPILING in recent_logs:
            return ContainerStatus.COMPILING
        elif CompilationMessages.NEXT_BUILDING in recent_logs:
            return ContainerStatus.BUILDING

        # Check container health
        container.reload()
        if container.status != 'running':
            return ContainerStatus.ERROR

        # Default to compiling if no clear status is found
        return ContainerStatus.COMPILING

    except Exception as e:
        logger.error(f"Error getting compilation status: {str(e)}")
        return ContainerStatus.ERROR


def extract_build_info(logs):
    """Extract build time and other Next.js specific information"""
    build_info = {}

    # Find the "Ready in XXms" message
    ready_match = re.search(r"Ready in (\d+)(?:\.?\d*)(?:ms|s)", logs)
    if ready_match:
        build_info['build_time'] = ready_match.group(1)

    # Extract any warnings
    warnings = re.findall(r"(?:⚠|warning).*?\n(?:(?!\n).)*", logs, re.MULTILINE | re.DOTALL)
    if warnings:
        build_info['warnings'] = warnings

    # Extract any errors
    errors = re.findall(r"(?:error|×).*?\n(?:(?!\n).)*", logs, re.MULTILINE | re.DOTALL)
    if errors:
        build_info['errors'] = errors

    return build_info


@api_view(['GET'])
def check_container_ready(request):
    container_id = request.GET.get('container_id')

    if not container_id:
        return JsonResponse({'error': 'No container ID provided'}, status=400)

    try:
        container = client.containers.get(container_id)
        container.reload()

        recent_logs = container.logs(tail=100).decode('utf-8')
        compilation_status = get_compilation_status(container)
        build_info = extract_build_info(recent_logs)

        port_mapping = container.ports.get('3001/tcp')
        if not port_mapping:
            return JsonResponse({
                'status': ContainerStatus.BUILDING,
                'message': 'Waiting for port mapping',
                'logs': recent_logs
            })

        host_port = port_mapping[0]['HostPort']
        dynamic_url = f"https://{host_port}.{HOST_URL}"

        response_data = {
            'status': compilation_status,
            'url': dynamic_url,
            'log': recent_logs.split('\n')[-1] if recent_logs else "No recent logs",
            'detailed_logs': recent_logs
        }

        # Add build info to response
        if build_info:
            response_data.update(build_info)

        return JsonResponse(response_data)

    except docker.errors.NotFound:
        return JsonResponse({
            'status': ContainerStatus.NOT_FOUND,
            'message': 'Container not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error checking container status: {str(e)}")
        return JsonResponse({
            'status': ContainerStatus.ERROR,
            'message': str(e)
        }, status=500)


@api_view(['GET'])
def get_container_logs(request):
    container_id = request.GET.get('container_id')
    if not container_id:
        return JsonResponse({'error': 'No container ID provided'}, status=400)

    try:
        container = client.containers.get(container_id)
        logs = container.logs(tail=100).decode('utf-8')  # Get last 100 lines of logs
        return JsonResponse({'logs': logs})
    except docker.errors.NotFound:
        return JsonResponse({'error': 'Container not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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
    try:
        data = request.data
        code = data.get('main_code')
        language = data.get('language')
        user_id = "0"  # Always use "0" as user_id
        file_name = "placeholder.tsx"
        main_file_path = "/components/dynamic/placeholder.tsx"

        # Define container name
        container_name = f'react_renderer_next_{user_id}_{file_name}'

        # Add request logging
        logger.info(f"Received request for container: {container_name}")
        logger.info(f"Request data: {json.dumps(data, indent=2)}")

        if not code:
            return JsonResponse({
                'error': 'No code provided',
                'detailed_logs': detailed_logger.get_logs()
            }, status=400)

        try:
            # First, check for any existing containers (including stopped ones)
            all_containers = client.containers.list(all=True, filters={'name': container_name})

            if all_containers:
                # Remove any existing containers
                for container in all_containers:
                    logger.info(f"Removing existing container: {container.name}, status: {container.status}")
                    try:
                        container.remove(force=True)
                    except Exception as e:
                        logger.warning(f"Error removing container {container.name}: {str(e)}")

            # Create new container
            logger.info(f"Creating new container: {container_name}")
            # Base path for mounted files
            base_path = "/home/ubuntu/brainpower-ai/react_renderer_next"

            container = client.containers.run(
                'react_renderer_next',
                command=["sh", "-c", "yarn dev & node watch-components.js"],
                user='node',
                detach=True,
                name=container_name,
                environment={
                    'PORT': '3001',
                    'USER_ID': user_id,
                    'FILE_NAME': file_name,
                    'HOSTNAME': '0.0.0.0'
                },
                volumes={
                    # Only mount directories, not individual files
                    os.path.join(base_path, 'components/dynamic'): {'bind': '/app/components/dynamic', 'mode': 'rw'},
                    os.path.join(base_path, 'components/ui'): {'bind': '/app/components/ui', 'mode': 'rw'},
                    os.path.join(base_path, 'src'): {'bind': '/app/src', 'mode': 'rw'}
                },
                ports={'3001/tcp': 3001},
                mem_limit='8g',
                memswap_limit='16g',
                restart_policy={"Name": "on-failure", "MaximumRetryCount": 5}
            )

            # Wait for container to be ready
            max_retries = 10
            retry_count = 0
            while retry_count < max_retries:
                container.reload()
                if container.status == 'running':
                    break
                time.sleep(1)
                retry_count += 1
                logger.info(f"Waiting for container... Status: {container.status}")

            if container.status != 'running':
                return JsonResponse({
                    'error': f'Container failed to start. Status: {container.status}',
                    'detailed_logs': detailed_logger.get_logs()
                }, status=500)

            # Set permissions for new container
            if not set_container_permissions(container):
                return JsonResponse({
                    'error': 'Failed to set container permissions for new container',
                    'detailed_logs': detailed_logger.get_logs()
                }, status=500)

            # Write initial component code
            logs, files_added, compilation_status = update_code_internal(
                container, code, user_id, file_name, main_file_path
            )

            response_data = {
                'status': 'success',
                'container_id': container.id,
                'url': 'https://3001.brainpower-ai.net',
                'detailed_logs': detailed_logger.get_logs()
            }

            logger.info(f"Returning response: {json.dumps(response_data, indent=2)}")
            return JsonResponse(response_data)

        except docker.errors.APIError as e:
            error_msg = f'Docker API error: {str(e)}'
            logger.error(error_msg)
            return JsonResponse({
                'error': error_msg,
                'detailed_logs': detailed_logger.get_logs()
            }, status=500)

    except Exception as e:
        error_msg = f'Unexpected error: {str(e)}'
        logger.error(error_msg)
        return JsonResponse({
            'error': error_msg,
            'detailed_logs': detailed_logger.get_logs()
        }, status=500)


def install_packages(container, packages):
    installed_packages = []
    failed_packages = []

    logger.info(f"Attempting to install packages: {', '.join(packages)}")

    for package in packages:
        try:
            logger.info(f"Installing package: {package}")
            result = exec_command_with_retry(container, ["yarn", "add", package])

            if result.exit_code == 0:
                installed_packages.append(package)
                logger.info(f"Successfully installed package: {package}")
            else:
                error_output = result.output.decode() if hasattr(result, 'output') else "No error output available"
                logger.error(
                    f"Failed to install package {package}. Exit code: {result.exit_code}. Error: {error_output}")
                failed_packages.append(package)

        except APIError as e:
            logger.error(f"Docker API error while installing {package}: {str(e)}")
            failed_packages.append(package)
        except Exception as e:
            logger.error(f"Unexpected error while installing {package}: {str(e)}", exc_info=True)
            failed_packages.append(package)

    if installed_packages:
        logger.info(f"Successfully installed packages: {', '.join(installed_packages)}")
    if failed_packages:
        logger.warning(f"Failed to install packages: {', '.join(failed_packages)}")

    return installed_packages, failed_packages


def check_non_standard_imports(code):
    import_pattern = r'import\s+(?:{\s*[\w\s,]+\s*}|[\w]+|\*\s+as\s+[\w]+)\s+from\s+[\'"](.+?)[\'"]|require\([\'"](.+?)[\'"]\)'
    imports = re.findall(import_pattern, code)

    standard_packages = {
        'react', 'react-dom', 'prop-types', 'react-router', 'react-router-dom',
        'redux', 'react-redux', 'axios', 'lodash', 'moment', 'styled-components',
        # Add moment-timezone to the list of standard packages
    }

    non_standard_imports = []
    for imp in imports:
        package_name = imp[0] or imp[1]  # Get the non-empty group
        if package_name and not package_name.startswith('.') and package_name not in standard_packages:
            non_standard_imports.append(package_name)

    return non_standard_imports


def check_local_imports(container, code):
    local_import_pattern = r'from\s+[\'"]\.\/(\w+)[\'"]'
    local_imports = re.findall(local_import_pattern, code)
    missing_imports = []

    for imp in local_imports:
        check_file = container.exec_run(
            f"[ -f /app/components/{imp}.js ] || [ -f /app/components/{imp}.ts ] && echo 'exists' || echo 'not found'")
        if check_file.output.decode().strip() == 'not found':
            missing_imports.append(imp)

    return missing_imports


def get_container_file_structure(container):
    exec_result = container.exec_run("find /app/components -printf '%P\\t%s\\t%T@\\t%y\\n'")
    logger.info(f"Find command exit code: {exec_result.exit_code}")
    logger.info(f"Find command output: {exec_result.output.decode()}")
    if exec_result.exit_code == 0:
        files = []
        for line in exec_result.output.decode().strip().split('\n'):
            parts = line.split(maxsplit=3)
            if len(parts) == 4:
                path, size, timestamp, type = parts
                files.append({
                    'path': path,
                    'size': int(size),
                    'created_at': datetime.fromtimestamp(float(timestamp)).isoformat(),
                    'type': 'file' if type == 'f' else 'folder'
                })

        return files
    else:
        logger.error(f"Error executing find command. Exit code: {exec_result.exit_code}")
        logger.error(f"Error output: {exec_result.output.decode()}")
    return []


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


@api_view(['POST'])
def update_code(request):
    container_id = request.data.get('container_id')
    main_code = request.data.get('main_code')
    user_id = request.data.get('user_id')
    file_name = request.data.get('file_name')
    main_file_path = request.data.get('main_file_path', "Root/Project")
    logger.info(
        f"Received update request from user {user_id} for container: {container_id}, original file: {file_name}, main file path: {main_file_path}, file code{main_code}")

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

