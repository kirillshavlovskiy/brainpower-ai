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
logger = logging.getLogger(__name__)
client = docker.from_env()

HOST_URL = 'brainpower-ai.net'
HOST_PORT_RANGE_START = 32768
HOST_PORT_RANGE_END = 60999
NGINX_SITES_DYNAMIC = '/etc/nginx/sites-dynamic'


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


@api_view(['GET'])
def check_container(request):
    user_id = request.GET.get('user_id', '0')
    file_name = request.GET.get('file_name', 'test-component.js')

    container_name = f'react_renderer_{user_id}_{file_name}'


    try:
        container = client.containers.get(container_name)
        # Get the container creation timestamp

        container.reload()
        container_info = {
            'container_name': container.name,
            'created_at': container.attrs['Created'],
            'status': container.status,
            'ports': container.ports,
            'image': container.image.tags[0] if container.image.tags else 'Unknown',
            'id': container.id
        }
        if container.status == 'running':
            port_mapping = container.ports.get('3001/tcp')
            file_structure = get_container_file_structure(container)
            check_result = container.exec_run("test -d /app/src && echo 'exists' || echo 'not found'")
            logger.info(f"Check /app/src directory result: {check_result.output.decode().strip()}")



            if check_result:
                file_structure = get_container_file_structure(container)
                logger.info(f"Check /app/src directory result: {check_result.output.decode().strip()}")
                logger.info(f"/app/src directory structure: {file_structure}")

            if port_mapping:
                host_port = port_mapping[0]['HostPort']

                return JsonResponse({
                    'status': 'ready',
                    'container_id': container.id,
                    'container_info': container_info,
                    'url': f"https://{host_port}.{HOST_URL}",
                    'file_list': file_structure,
                    'detailed_logs': detailed_logger.get_logs(),

                })
            else:
                return JsonResponse({'status': 'not_ready', 'container_id': container.id})
        else:
            return JsonResponse({'status': 'not_ready', 'container_id': container.id})
    except docker.errors.NotFound:
        return JsonResponse({'status': 'not_found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def set_container_permissions(container):
    """Set proper permissions for container directories with read-only handling"""
    try:
        # Check if src directory exists
        check_result = container.exec_run(
            "test -d /app/src || mkdir -p /app/src",
            user='root'
        )

        # Only try to set permissions for writable directories
        commands = [
            "chown -R node:node /app/src",
            "chmod -R 755 /app/src",
            "chmod -R g+w /app/src",
            "touch /app/compilation_status",
            "chown node:node /app/compilation_status",
            "chmod 644 /app/compilation_status"
        ]

        for cmd in commands:
            try:
                exec_result = container.exec_run(
                    ["sh", "-c", cmd],
                    user='root'
                )
                if exec_result.exit_code != 0:
                    logger.warning(f"Command {cmd} failed with: {exec_result.output.decode()}")
            except Exception as cmd_error:
                logger.warning(f"Error executing {cmd}: {str(cmd_error)}")
                continue

        logger.info("Container permissions set successfully for writable directories")
        return True

    except Exception as e:
        logger.error(f"Error setting container permissions: {str(e)}")
        return False


def update_code_internal(container, code, user, file_name, main_file_path):
    files_added = []
    build_output= []
    try:
        # Update component.js
        set_container_permissions(container)
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
                files_added.append('/app/src/component.js')
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

        # Handle all imports (CSS, JS, TS, JSON, etc.)
        import_pattern = r"import\s+(?:(?:{\s*[\w\s,]+\s*})|(?:[\w]+)|\*\s+as\s+[\w]+)\s+from\s+['\"](.+?)['\"]|import\s+['\"](.+?)['\"]"
        imports = re.findall(import_pattern, code)

        for import_match in imports:
            import_path = import_match[0] or import_match[1]  # Get the non-empty group
            if import_path:
                logger.info(f"Attempting to retrieve content for imported file: {import_path}")
                file_content = FileStructureConsumer.get_file_content_for_container(user, import_path, base_path)
                if file_content is not None:
                    logger.info(f"Retrieved content for file: {import_path}")
                    encoded_content = base64.b64encode(file_content.encode()).decode()
                    container_path = f"/app/src/{import_path}"
                    exec_result = container.exec_run([
                        "sh", "-c",
                        f"mkdir -p $(dirname {container_path}) && echo {encoded_content} | base64 -d > {container_path}"
                    ])
                    if exec_result.exit_code != 0:
                        raise Exception(f"Failed to update {import_path} in container: {exec_result.output.decode()}")
                    logger.info(f"Updated {import_path} in container")
                    files_added.append(container_path)
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
                        files_added.append(container_path)

        # Check for non-standard imports
        non_standard_imports = check_non_standard_imports(code)
        if non_standard_imports:
            logger.info(f"Detected non-standard imports: {', '.join(non_standard_imports)}")
            installed_packages, failed_packages = install_packages(container, non_standard_imports)

            if failed_packages:
                logger.warning(f"Some packages failed to install: {', '.join(failed_packages)}")

            # You might want to decide here if you want to continue or raise an exception if some packages failed to install

        else:
            logger.info("No non-standard imports detected")

        # Start the development server
        logger.info("Starting the development server with 'yarn start'")
        exec_result = exec_command_with_retry(container, ["sh", "-c", "cd /app && yarn start"])

        # Process the output
        output_lines = exec_result.decode().split('\n')
        build_output = output_lines
        compilation_status = ContainerStatus.COMPILING

        logger.info("Analyzing build output...")
        for line in output_lines:
            if "Compiled successfully" in line:
                compilation_status = ContainerStatus.READY
                logger.info("Compilation successful")
                break
            elif "Compiled with warnings" in line:
                compilation_status = ContainerStatus.WARNING
                logger.warning("Compilation completed with warnings")
                break
            elif "Failed to compile" in line:
                compilation_status = ContainerStatus.COMPILATION_FAILED
                logger.error("Compilation failed")
                break

        # Save compilation status
        exec_command_with_retry(container, ["sh", "-c", f"echo {compilation_status} > /app/compilation_status"])
        logger.info(f"Saved compilation status: {compilation_status}")

        # Log container status
        container.reload()
        logger.info(f"Container status after yarn start: {container.status}")
        logger.info(f"Container state: {container.attrs['State']}")

        return "\n".join(build_output), files_added, installed_packages, compilation_status

    except Exception as e:
        logger.error(f"Error updating code in container: {str(e)}", exc_info=True)
        raise


def get_compilation_status(container):
    try:
        # Try to read the compilation status file
        status_result = exec_command_with_retry(container, ["cat", "/app/compilation_status"])
        saved_status = status_result.decode().strip()

        if saved_status and saved_status in [ContainerStatus.READY, ContainerStatus.WARNING,
                                             ContainerStatus.COMPILATION_FAILED]:
            return saved_status

        # If no valid status is saved, or if it's still COMPILING, we need to check the logs
        logs = container.logs(tail=100).decode('utf-8')

        if "Compiled successfully" in logs:
            return ContainerStatus.READY
        elif "Compiled with warnings" in logs:
            return ContainerStatus.WARNING
        elif "Failed to compile" in logs:
            return ContainerStatus.COMPILATION_FAILED
        else:
            return ContainerStatus.COMPILING
    except Exception as e:
        logger.error(f"Error getting compilation status: {str(e)}")
        return ContainerStatus.ERROR


@api_view(['GET'])
def check_container_ready(request):
    container_id = request.GET.get('container_id')
    user_id = request.GET.get('user_id', 'default')
    file_name = request.GET.get('file_name')

    logger.info(f"Checking container ready: container_id={container_id}, user_id={user_id}, file_name={file_name}")

    if not container_id:
        logger.error("No container ID provided")
        return JsonResponse({'status': ContainerStatus.ERROR, 'error': 'No container ID provided'}, status=400)

    try:
        container = client.containers.get(container_id)
        container.reload()
        logger.info(f"Container status: {container.status}")

        compilation_status = get_compilation_status(container)
        logger.info(f"Compilation status: {compilation_status}")

        if not compilation_status:
            compilation_status = ContainerStatus.COMPILING

        all_logs = container.logs(stdout=True, stderr=True).decode('utf-8').strip()
        recent_logs = container.logs(stdout=True, stderr=True, tail=50).decode('utf-8').strip()
        latest_log = recent_logs.split('\n')[-1] if recent_logs else "No recent logs"

        if container.status != 'running':
            return JsonResponse({'status': ContainerStatus.CREATING, 'log': latest_log})

        port_mapping = container.ports.get('3001/tcp')
        if not port_mapping:
            return JsonResponse({'status': ContainerStatus.BUILDING, 'log': latest_log})

        host_port = port_mapping[0]['HostPort']
        dynamic_url = f"https://{host_port}.{HOST_URL}"

        response_data = {
            'status': compilation_status,
            'url': dynamic_url,
            'log': latest_log,
            'detailed_logs': all_logs
        }

        if compilation_status == ContainerStatus.WARNING:
            warnings = re.findall(r"warning.*\n.*\n.*\n", all_logs, re.IGNORECASE)
            response_data['warnings'] = warnings

        if compilation_status == ContainerStatus.COMPILATION_FAILED:
            errors = re.findall(r"error.*\n.*\n.*\n", all_logs, re.IGNORECASE)
            response_data['errors'] = errors

        return JsonResponse(response_data)

    except docker.errors.NotFound:
        return JsonResponse({'status': ContainerStatus.NOT_FOUND, 'log': 'Container not found'}, status=404)
    except Exception as e:
        logger.error(f"Error checking container status: {str(e)}", exc_info=True)
        return JsonResponse({'status': ContainerStatus.ERROR, 'error': str(e), 'log': str(e)}, status=500)

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
    file_structure = []
    data = request.data
    code = data.get('main_code')
    language = data.get('language')
    user_id = data.get('user_id', '0')
    file_name = data.get('file_name', 'component.js')
    main_file_path = data.get('main_file_path')

    detailed_logger.log('info', f"Received request to check or create container for user {user_id}, file {file_name}, file path {main_file_path}")

    if not all([code, language, file_name]):
        return JsonResponse({'error': 'Missing required fields'}, status=400)
    if language != 'react':
        return JsonResponse({'error': 'Unsupported language'}, status=400)

    react_renderer_path = '/home/ubuntu/brainpower-ai/react_renderer'
    container_name = f'react_renderer_{user_id}_{file_name}'
    app_name = f"{user_id}_{file_name.replace('.', '-')}"

    container_info = {
        'container_name': container_name,
        'created_at': datetime.now().isoformat(),
        'files_added': [],
        'build_status': 'pending'
    }

    try:
        container = client.containers.get(container_name)
        detailed_logger.log('info', f"Found existing container: {container.id}")

        # Check if the container is running, if not, start it
        if container.status != 'running':
            detailed_logger.log('info', f"Container {container.id} is not running. Attempting to start it.")
            container.start()
            container.reload()
            time.sleep(5)  # Wait for container to fully start

        # Here's where we need to check the actual compilation status
        compilation_status = get_compilation_status(container)

        container_info = {
            'container_name': container.name,
            'created_at': datetime.now().isoformat(),
            'status': container.status,
            'ports': container.ports,
            'image': container.image.tags[0] if container.image.tags else 'Unknown',
            'id': container.id
        }


        # Get the host port
        port_bindings = container.attrs['NetworkSettings']['Ports']
        host_port = None
        if '3001/tcp' in port_bindings and port_bindings['3001/tcp']:
            host_port = port_bindings['3001/tcp'][0]['HostPort']
        dynamic_url = f"https://{host_port}.{HOST_URL}"

        try:
            # Check for non-standard imports
            non_standard_imports = check_non_standard_imports(code)
            installed_packages = []
            if non_standard_imports:
                installed_packages = install_packages(container, non_standard_imports)

            # Check for local imports
            missing_local_imports = check_local_imports(container, code)

            build_output, files_added, failed_packages, compilation_status = update_code_internal(container, code, user_id, file_name,
                                                                                 main_file_path)

            datailed_logs = container.logs(tail=200).decode('utf-8')  # Get last 200 lines of logs
            file_structure = get_container_file_structure(container)

            return JsonResponse({
                'status': 'success',
                'message': 'Container is running',
                'container_id': container.id,
                'url': dynamic_url,
                'can_deploy': True,
                'container_info': container_info,
                'build_output': build_output,
                'detailed_logs': detailed_logger.get_logs(),
                'file_list': file_structure,
                'installed_packages': installed_packages,
                'failed_packages': failed_packages,  # New field
                'files_added': files_added,
                'compilation_status': compilation_status,  # New field
            })
        except Exception as update_error:
            detailed_logger.log('error', f"Failed to update code: {str(update_error)}")
            return JsonResponse({
                'status': 'error',
                'message': str(update_error),
                'build_output': getattr(update_error, 'build_output', None),
                'detailed_logs': detailed_logger.get_logs(),
                'file_list': file_structure,
            }, status=500)

    except docker.errors.NotFound:
        detailed_logger.log('info', f"Container {container_name} not found. Creating new container.")
        host_port = get_available_port(HOST_PORT_RANGE_START, HOST_PORT_RANGE_END)
        detailed_logger.log('info', f"Selected port {host_port} for new container")
        try:
            container = client.containers.run(
                'react_renderer_cra',
                command=["sh", "-c", "yarn start"],
                detach=True,
                name=container_name,
                environment={
                    'USER_ID': user_id,
                    'REACT_APP_USER_ID': user_id,
                    'FILE_NAME': file_name,
                    'PORT': str(3001),
                    'NODE_ENV': 'production',
                    'NODE_OPTIONS': '--max-old-space-size=8192'
                },
                volumes={
                    os.path.join(react_renderer_path, 'src'): {'bind': '/app/src', 'mode': 'rw'},
                    os.path.join(react_renderer_path, 'public'): {'bind': '/app/public', 'mode': 'rw'},
                    os.path.join(react_renderer_path, 'package.json'): {'bind': '/app/package.json', 'mode': 'ro'},
                    os.path.join(react_renderer_path, 'package-lock.json'): {'bind': '/app/package-lock.json', 'mode': 'ro'},
                    os.path.join(react_renderer_path, 'build'): {'bind': '/app/build', 'mode': 'rw'},
                },
                ports={'3001/tcp': host_port},
                mem_limit='8g',
                memswap_limit='16g',
                cpu_quota=100000,
                restart_policy={"Name": "on-failure", "MaximumRetryCount": 5}
            )
            detailed_logger.log('info', f"New container created: {container_name}")
            container_info['build_status'] = 'created'
        except docker.errors.APIError as e:
            detailed_logger.log('error', f"Failed to create container: {str(e)}")
            return JsonResponse({
                'error': f'Failed to create container: {str(e)}',
                'container_info': container_info,
                'detailed_logs': detailed_logger.get_logs(),
                'file_list': detailed_logger.get_file_list(),
            }, status=500)

        try:

            # Check for non-standard imports
            non_standard_imports = check_non_standard_imports(code)
            installed_packages = []
            if non_standard_imports:
                installed_packages = install_packages(container, non_standard_imports)

            # Check for local imports
            missing_local_imports = check_local_imports(container, code)

            build_output, files_added, installed_packages, compilation_status = update_code_internal(container, code, user_id, file_name,
                                                                                 main_file_path)
            container_info['build_status'] = 'updated'

            file_structure = get_container_file_structure(container)
            datailed_logs = container.logs(tail=200).decode('utf-8')  # Get last 200 lines of logs
            detailed_logger.log('warning', f"File structure: {file_structure}, \nbuild output {build_output}")
            container_info['file_structure'] = file_structure

            container.reload()
            port_mapping = container.ports.get('3001/tcp')
            detailed_logger.log('warning', "check that container reload successful, port mapping successful")
            if port_mapping:
                dynamic_url = f"https://{host_port}.{HOST_URL}"
                detailed_logger.log('info', f"Container {container_name} running successfully: {dynamic_url}")
                return JsonResponse({
                    'status': 'success',
                    'message': 'Container is running',
                    'container_id': container.id,
                    'url': dynamic_url,
                    'can_deploy': True,
                    'container_info': container_info,
                    'build_output': build_output,
                    'detailed_logs': detailed_logger.get_logs(),
                    'file_list': file_structure,
                    'installed_packages': installed_packages,
                    'files_added': files_added
                })
            else:
                detailed_logger.log('error', f"Failed to get port mapping for container {container_name}")
                return JsonResponse({
                    'error': 'Failed to get port mapping',
                    'container_info': container_info,
                    'build_output': build_output,
                    'detailed_logs': detailed_logger.get_logs(),
                    'file_list': file_structure,
                    'installed_packages': installed_packages,
                    'files_added': files_added
                }, status=500)
        except Exception as e:
            detailed_logger.log('error', f"!!!Failed to update code in container: {str(e)}")
            return JsonResponse({
                'error': f'Failed to update code in container: {str(e)}',
                'container_info': container_info,
                'detailed_logs': detailed_logger.get_logs(),
                'file_list': [],
            }, status=500)

    except Exception as e:
        detailed_logger.log('error', f"Unexpected error: {str(e)}")
        return JsonResponse({
            'error': f'Unexpected error: {str(e)}',
            'container_info': container_info if 'container_info' in locals() else None,
            'detailed_logs': detailed_logger.get_logs(),
            'file_list': detailed_logger.get_file_list(),
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
            f"[ -f /app/src/{imp}.js ] || [ -f /app/src/{imp}.ts ] && echo 'exists' || echo 'not found'")
        if check_file.output.decode().strip() == 'not found':
            missing_imports.append(imp)

    return missing_imports


def get_container_file_structure(container):
    exec_result = container.exec_run("find /app/src -printf '%P\\t%s\\t%T@\\t%y\\n'")
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
        # container.reload()
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
            production_url = f"https://8000.brainpower-ai.net/{app_name}/"
            if container.status != 'running':
                raise Exception(f"Container {container_id} is not running.")

            self.send_update(channel_layer, task_id, "Production build process started...", production_url)
            build_command = f"""
            export NODE_OPTIONS="--max-old-space-size=8192" && \
            export GENERATE_SOURCEMAP=false && \
            export PUBLIC_URL="/{app_name}" && \
            yarn build
            """
            exec_result = container.exec_run(["sh", "-c", build_command], demux=True)
            stdout, stderr = exec_result.output
            if exec_result.exit_code != 0:
                error_message = stderr.decode() if stderr else 'Unknown error'
                raise Exception(f"Build failed: {error_message}")

            # Remove existing directory if it exists
            self.send_update(channel_layer, task_id, "Production build process completed. Copying build files...", production_url)
            subprocess.run(f"sudo rm -rf {production_dir}", shell=True, check=True)

            # Create production directory
            subprocess.run(f"sudo mkdir -p {production_dir}", shell=True, check=True)

            # Copy files from container to host
            copy_command = f"sudo docker cp {container_id}:/app/build/. {production_dir}"
            copy_result = subprocess.run(copy_command, shell=True, capture_output=True, text=True)
            if copy_result.returncode != 0:
                logger.error(f"Error copying files: {copy_result.stderr}")
                raise Exception(f"Failed to copy build files: {copy_result.stderr}")
            logger.info("Files copied successfully")

            # Update index.html to use correct static file paths
            update_index_command = f"""
                sudo sed -i 's|"/static/|"/{app_name}/static/|g' {os.path.join(production_dir, 'index.html')}
            """
            update_index_result = subprocess.run(update_index_command, shell=True, check=True)
            if copy_result.returncode != 0:
                logger.error(f"Error copying files: {update_index_result.stderr}")
                raise Exception(f"Failed to copy build files: {update_index_result.stderr}")
            logger.info("Index updated successfully")

            self.send_update(channel_layer, task_id, "Verifying deployed files...", production_url=production_url)
            list_command = f"ls -R {production_dir}"
            result = subprocess.run(list_command, shell=True, capture_output=True, text=True)
            # self.send_update(channel_layer, task_id, f"Deployed files:\n{result.stdout}", production_url)

            # # Update other static files (JS, CSS)
            # self.send_update(channel_layer, task_id, "Updating static file paths...")
            # update_static_files_command = f"""
            #         sudo find {production_dir} -type f \( -name '*.js' -o -name '*.css' \) -exec sudo sed -i 's|/static/|/{app_name}/static/|g' {{}} +
            #         """
            # subprocess.run(update_static_files_command, shell=True, check=True)
            # logger.info("Static file paths updated")

            # Set correct permissions
            self.send_update(channel_layer, task_id, "Setting correct permissions...", production_url=production_url)
            subprocess.run(f"sudo chown -R ubuntu:ubuntu {production_dir}", shell=True, check=True)
            subprocess.run(f"sudo chmod -R 755 {production_dir}", shell=True, check=True)

            index_path = os.path.join(production_dir, 'index.html')
            if os.path.exists(index_path):
                logger.info(f"Deployment completed. Production URL: {production_url}")
                self.send_update(channel_layer, task_id, "DEPLOYMENT_COMPLETE", production_url=production_url)

                # Perform health check
                self.send_update(channel_layer, task_id, "Performing health check...", production_url=production_url)
                try:
                    host_response = requests.get(production_url, timeout=10)
                    logger.info(f"Server response: {host_response}")
                    if host_response.status_code == 200:
                        self.send_update(channel_layer, task_id, "Health check passed", production_url=production_url)
                    else:
                        raise Exception(f"Health check failed. Status code: {host_response.status_code}")
                except requests.RequestException as e:
                    raise Exception(f"Health check failed. Error: {str(e)}")

                self.send_update(channel_layer, task_id, "DEPLOYMENT_COMPLETE", production_url=production_url)
            else:
                raise Exception(f"Deployment failed: index.html not found at {index_path}")

        except Exception as e:
            logger.error(f"Error in deployment: {str(e)}")
            self.send_update(channel_layer, task_id, f"Error: {str(e)}", error_trace=traceback.format_exc())

    def send_update(self, channel_layer, task_id, message, production_url=None, error_trace=None):
        logger.info(f"deployment url: {production_url}")
        update = {
            "type": "deployment_update",
            "message": message,
            "production_url": production_url,
        }
        if production_url:
            update["production_url"] = production_url
        if error_trace:
            update["error_trace"] = error_trace

        logger.info(f"Sending update: {update}")
        async_to_sync(channel_layer.group_send)(f"deployment_{task_id}", update)
        logger.info(f"Sent update for task {task_id}: {message}")






