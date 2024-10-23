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


@api_view(['GET'])
def check_container(request):
    """
    Primary container status check - verifies container existence and basic health
    """
    user_id = request.GET.get('user_id', '0')
    file_name = request.GET.get('file_name', 'test-component.js')
    container_name = f'react_renderer_{user_id}_{file_name}'

    logger.info(f"Checking container status for {container_name}")

    try:
        container = client.containers.get(container_name)
        container.reload()

        # Get comprehensive container info
        container_info = {
            'container_name': container.name,
            'created_at': container.attrs['Created'],
            'status': container.status,
            'ports': container.ports,
            'image': container.image.tags[0] if container.image.tags else 'Unknown',
            'id': container.id,
            'health_status': container.attrs.get('State', {}).get('Health', {}).get('Status', 'unknown'),
            'state_details': container.attrs.get('State', {}),
            'exit_code': container.attrs.get('State', {}).get('ExitCode', None)
        }

        # Extended container state check
        if container.status != 'running':
            try:
                logger.info(f"Starting container {container_name}")
                container.start()

                # Wait for container to fully start
                start_time = time.time()
                max_wait = 30  # seconds
                while time.time() - start_time < max_wait:
                    container.reload()
                    if container.status == 'running':
                        # Additional check for service readiness
                        logs = container.logs(tail=50).decode('utf-8')
                        if 'ready started server' in logs or 'Listening on port 3001' in logs:
                            break
                    time.sleep(1)

                container.reload()
                if container.status != 'running':
                    raise Exception(f"Container failed to start properly. Exit code: {container_info['exit_code']}")

            except Exception as start_error:
                error_logs = container.logs(tail=100).decode('utf-8')
                logger.error(f"Container start failed: {str(start_error)}\nLogs:\n{error_logs}")
                return JsonResponse({
                    'status': 'error',
                    'container_id': container.id,
                    'message': f"Failed to start container: {str(start_error)}",
                    'container_info': container_info,
                    'logs': error_logs
                })

        # Verify port mapping
        port_mapping = container.ports.get('3001/tcp')
        if not port_mapping:
            logs = container.logs(tail=50).decode('utf-8')
            logger.warning(f"No port mapping. Container logs:\n{logs}")
            return JsonResponse({
                'status': 'not_ready',
                'container_id': container.id,
                'message': 'Container running but port not mapped',
                'container_info': container_info,
                'logs': logs
            })

        # Verify Next.js setup
        check_commands = [
            "test -d /app/pages && echo 'pages exists' || echo 'pages missing'",
            "test -d /app/components && echo 'components exists' || echo 'components missing'",
            "test -f /app/next.config.js && echo 'config exists' || echo 'config missing'",
            "test -d /app/node_modules && echo 'modules exist' || echo 'modules missing'"
        ]

        structure_status = {}
        for cmd in check_commands:
            result = container.exec_run(cmd, user='root')
            structure_status[cmd.split()[3]] = result.output.decode().strip()

        # Get complete status
        compilation_status = get_compilation_status(container)
        file_structure = get_container_file_structure(container)
        recent_logs = container.logs(tail=100).decode('utf-8')

        # Build response URL
        host_port = port_mapping[0]['HostPort']
        url = f"https://{host_port}.{HOST_URL}"

        # Determine if container is truly ready
        is_ready = all([
            container.status == 'running',
            compilation_status in [ContainerStatus.READY, ContainerStatus.WARNING],
            bool(port_mapping),
            all('exists' in status for status in structure_status.values())
        ])

        response_data = {
            'status': 'ready' if is_ready else 'initializing',
            'container_id': container.id,
            'container_info': container_info,
            'url': url,
            'file_list': file_structure,
            'compilation_status': compilation_status,
            'structure_status': structure_status,
            'detailed_logs': detailed_logger.get_logs(),
            'recent_logs': recent_logs,
            'port': host_port,
            'next_js_status': {
                'ready': 'ready started server' in recent_logs,
                'port_bound': bool(port_mapping),
                'structure_complete': all('exists' in status for status in structure_status.values())
            },
            'message': 'Container is ready' if is_ready else 'Container is initializing'
        }

        return JsonResponse(response_data)

    except docker.errors.NotFound:
        logger.warning(f"Container {container_name} not found")
        return JsonResponse({
            'status': 'not_found',
            'message': f"Container {container_name} not found"
        }, status=404)

    except Exception as e:
        logger.error(f"Error checking container {container_name}: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'error_details': traceback.format_exc()
        }, status=500)


def exec_command_with_retry(container, command, user='node', max_retries=3, delay=1):
    for attempt in range(max_retries):
        try:
            container.reload()
            if container.status != 'running':
                logger.info(f"Container {container.id} is not running. Attempting to start it.")
                container.start()
                container.reload()
                time.sleep(5)  # Wait for container to fully start

            exec_result = container.exec_run(
                cmd=command,
                user=user,
                stdout=True,
                stderr=True
            )

            if exec_result.exit_code != 0:
                raise Exception(f"Command failed with exit code {exec_result.exit_code}: {exec_result.output.decode()}")

            return exec_result
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            logger.warning(f"Attempt {attempt + 1} failed: {str(e)}. Retrying in {delay} seconds...")
            time.sleep(delay)


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
    build_output = []
    try:
        # Encode the code to base64 to handle special characters
        encoded_code = base64.b64encode(code.encode()).decode()

        # Determine target file path inside the container based on file type
        if file_name.endswith(('.js', '.jsx', '.ts', '.tsx')):
            # Set appropriate file extension for the dynamic component
            is_typescript = file_name.endswith(('.ts', '.tsx'))
            target_file = '/app/components/DynamicComponent.' + ('tsx' if is_typescript else 'js')

            # Ensure components directory exists with correct permissions
            exec_commands = [
                "mkdir -p /app/components",
                "chown -R node:node /app/components",
                "chmod -R 755 /app/components",
                f"echo {encoded_code} | base64 -d > {target_file}",
                "chmod 644 " + target_file
            ]

            for cmd in exec_commands:
                exec_result = container.exec_run(["sh", "-c", cmd], user='root')
                if exec_result.exit_code != 0:
                    raise Exception(f"Failed to execute command: {cmd}: {exec_result.output.decode()}")

            files_added.extend([target_file, '/app/pages/index.js'])

            # Don't modify index.js as it's already in the mounted volume
            logger.info(f"Component file created: {target_file}")

        else:
            raise Exception(f"Unsupported file type: {file_name}")

        # Process imports
        base_path = os.path.dirname(main_file_path)
        import_pattern = r"import\s+(?:(?:{\s*[\w\s,]+\s*})|(?:[\w]+)|\*\s+as\s+[\w]+)\s+from\s+['\"](.+?)['\"]|import\s+['\"](.+?)['\"]"
        imports = re.findall(import_pattern, code)

        for import_match in imports:
            import_path = import_match[0] or import_match[1]
            if import_path:
                file_content = FileStructureConsumer.get_file_content_for_container(user, import_path, base_path)
                if file_content is not None:
                    # Determine correct path based on import type
                    if import_path.endswith('.css'):
                        container_path = f"/app/styles/{os.path.basename(import_path)}"
                    else:
                        container_path = f"/app/components/{os.path.basename(import_path)}"

                    encoded_content = base64.b64encode(file_content.encode()).decode()

                    # Create directory and set permissions before writing file
                    exec_commands = [
                        f"mkdir -p $(dirname {container_path})",
                        f"chown -R node:node $(dirname {container_path})",
                        f"chmod -R 755 $(dirname {container_path})",
                        f"echo {encoded_content} | base64 -d > {container_path}",
                        f"chmod 644 {container_path}",
                        f"chown node:node {container_path}"
                    ]

                    for cmd in exec_commands:
                        exec_result = container.exec_run(["sh", "-c", cmd], user='root')
                        if exec_result.exit_code != 0:
                            raise Exception(f"Failed to execute command: {cmd}: {exec_result.output.decode()}")

                    files_added.append(container_path)
                    logger.info(f"Added imported file: {container_path}")

        # Check and install dependencies
        non_standard_imports = check_non_standard_imports(code)
        if non_standard_imports:
            installed_packages, failed_packages = install_packages(container, non_standard_imports)
            if failed_packages:
                logger.warning(f"Failed to install packages: {', '.join(failed_packages)}")

        # Ensure all project directories have correct permissions
        exec_result = container.exec_run(
            ["sh", "-c", "chown -R node:node /app && chmod -R 755 /app"],
            user='root'
        )
        if exec_result.exit_code != 0:
            logger.warning(f"Failed to set project permissions: {exec_result.output.decode()}")

        # Start Next.js development server
        logger.info("Starting Next.js development server")
        exec_result = container.exec_run(
            ["sh", "-c", "cd /app && yarn dev -p 3001"],
            user='node',
            detach=True
        )

        if exec_result.exit_code != 0:
            raise Exception(f"Failed to start Next.js server: {exec_result.output.decode()}")

        # Wait for server startup and monitor logs
        time.sleep(5)

        # Process build output and status
        build_output = container.logs(tail=100).decode('utf-8').split('\n')
        compilation_status = ContainerStatus.COMPILING

        for line in build_output:
            if "compiled successfully" in line.lower():
                compilation_status = ContainerStatus.READY
                break
            elif "compiled with warnings" in line.lower():
                compilation_status = ContainerStatus.WARNING
                break
            elif "failed to compile" in line.lower():
                compilation_status = ContainerStatus.COMPILATION_FAILED
                break

        # Save status
        container.exec_run(
            ["sh", "-c", f"echo {compilation_status} > /app/compilation_status"],
            user='node'
        )

        return "\n".join(build_output), files_added, compilation_status, installed_packages

    except Exception as e:
        logger.error(f"Error updating code: {str(e)}", exc_info=True)
        raise


def get_compilation_status(container):
    """Get detailed Next.js compilation status with improved detection"""
    try:
        logs = container.logs(tail=100).decode('utf-8')

        # Define status indicators
        status_indicators = {
            'ready': ('✓ Ready in', 'ready - started server on', 'Local:        http://localhost:3001'),
            'compiling': ('- Compiling...', 'Creating an optimized production build'),
            'warning': ('Disabled SWC', '`compiler` options', 'warning'),
            'error': ('Failed to compile', 'Error:', 'error')
        }

        # Check for successful compilation and running server
        for indicator in status_indicators['ready']:
            if indicator in logs:
                # Only return READY if we see the port is actually bound
                if container.ports.get('3001/tcp'):
                    return ContainerStatus.READY
                else:
                    logger.warning("Next.js reports ready but port 3001 is not bound")
                    return ContainerStatus.BUILDING

        # Check for compilation in progress
        for indicator in status_indicators['compiling']:
            if indicator in logs:
                return ContainerStatus.COMPILING

        # Check for warnings (but still running)
        for indicator in status_indicators['warning']:
            if indicator in logs:
                # If we have warnings but server is running, return WARNING
                if 'Ready in' in logs and container.ports.get('3001/tcp'):
                    return ContainerStatus.WARNING
                return ContainerStatus.COMPILING

        # Check for errors
        for indicator in status_indicators['error']:
            if indicator in logs:
                return ContainerStatus.COMPILATION_FAILED

        # If no specific status found but container is running, assume still compiling
        return ContainerStatus.COMPILING

    except Exception as e:
        logger.error(f"Error getting compilation status: {str(e)}")
        return ContainerStatus.ERROR


@api_view(['GET'])
def check_container_ready(request):
    """Enhanced container readiness check for Next.js"""
    container_id = request.GET.get('container_id')
    user_id = request.GET.get('user_id', 'default')
    file_name = request.GET.get('file_name')

    detailed_logger.log('info', f"Checking container ready: container_id={container_id}, user_id={user_id}")

    if not container_id:
        return JsonResponse({
            'status': ContainerStatus.ERROR,
            'error': 'No container ID provided'
        }, status=400)

    try:
        container = client.containers.get(container_id)
        container.reload()

        # Get all relevant logs
        logs = container.logs(stdout=True, stderr=True).decode('utf-8').strip()
        recent_logs = logs.split('\n')[-50:] if logs else []

        # Check if Next.js is actually ready
        nextjs_ready = False
        port_bound = False
        has_warnings = False

        # Parse logs for specific Next.js status
        for log in recent_logs:
            if '✓ Ready in' in log:
                nextjs_ready = True
            if 'http://localhost:3001' in log:
                port_bound = True
            if 'warning' in log.lower():
                has_warnings = True

        # Verify port binding
        port_mapping = container.ports.get('3001/tcp')
        if port_mapping:
            host_port = port_mapping[0]['HostPort']
            url = f"https://{host_port}.{HOST_URL}"
        else:
            url = None

        # Check container's network settings
        network_settings = container.attrs.get('NetworkSettings', {})
        port_bindings = network_settings.get('Ports', {}).get('3001/tcp', [])

        # Build detailed status response
        status_info = {
            'container_running': container.status == 'running',
            'nextjs_ready': nextjs_ready,
            'port_bound': bool(port_mapping),
            'port_bindings': port_bindings,
            'network_mode': network_settings.get('NetworkMode', 'unknown'),
            'has_warnings': has_warnings,
            'url': url,
            'host_port': host_port if port_mapping else None,
        }

        # Determine overall status
        if not status_info['container_running']:
            detailed_logger.log('warning', "Container is not running")
            return JsonResponse({
                'status': ContainerStatus.ERROR,
                'message': 'Container is not running',
                'status_info': status_info,
                'logs': '\n'.join(recent_logs)
            })

        if nextjs_ready and port_bound:
            status = ContainerStatus.READY if not has_warnings else ContainerStatus.WARNING
            message = "Next.js server is ready"
        else:
            status = ContainerStatus.COMPILING
            message = "Next.js server is starting"

        # Network check command
        try:
            # Test network connectivity
            exec_result = container.exec_run(
                ["sh", "-c", "nc -zv localhost 3001 2>&1"]
            )
            network_test = exec_result.output.decode()
            status_info['network_test'] = network_test
        except Exception as e:
            status_info['network_test_error'] = str(e)

        response_data = {
            'status': status,
            'message': message,
            'url': url,
            'status_info': status_info,
            'port': host_port if port_mapping else None,
            'logs': '\n'.join(recent_logs),
            'warnings': [log for log in recent_logs if 'warning' in log.lower()] if has_warnings else []
        }

        # Add detailed connection info if we have warnings
        if has_warnings or not nextjs_ready:
            try:
                exec_result = container.exec_run(
                    ["sh", "-c", "netstat -tlnp | grep 3001"]
                )
                response_data['port_status'] = exec_result.output.decode()
            except Exception as e:
                response_data['port_status_error'] = str(e)

        return JsonResponse(response_data)

    except docker.errors.NotFound:
        return JsonResponse({
            'status': ContainerStatus.NOT_FOUND,
            'message': 'Container not found'
        }, status=404)

    except Exception as e:
        error_message = str(e)
        detailed_logger.log('error', f"Error checking container status: {error_message}", exc_info=True)
        return JsonResponse({
            'status': ContainerStatus.ERROR,
            'error': error_message,
            'logs': container.logs().decode() if 'container' in locals() else 'No logs available'
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
    data = request.data
    code = data.get('main_code')
    language = data.get('language')
    user_id = data.get('user_id', '0')
    file_name = data.get('file_name', 'component.js')
    main_file_path = data.get('main_file_path')

    detailed_logger.log('info', f"Starting container setup for user {user_id}, file {file_name}")

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
        # Try to get existing container
        container = client.containers.get(container_name)
        detailed_logger.log('info', f"Found existing container: {container.id}")

        # Check container status and start if needed
        if container.status != 'running':
            detailed_logger.log('info', f"Starting existing container: {container.id}")

            # Ensure proper permissions on mounted volume before starting
            container.exec_run(
                ["sh", "-c", "chown -R node:node /app && chmod -R 755 /app"],
                user='root'
            )

            container.start()
            container.reload()
            time.sleep(5)  # Wait for container to initialize

            # Start Next.js development server
            exec_result = container.exec_run(
                ["sh", "-c", "cd /app && NODE_ENV=development yarn dev -p 3001"],
                detach=True,
                user='node'
            )

        # Get container status and port information
        container.reload()
        container_info.update({
            'status': container.status,
            'ports': container.ports,
            'image': container.image.tags[0] if container.image.tags else 'Unknown',
            'id': container.id
        })

        # Get port mapping
        port_mapping = container.ports.get('3001/tcp')
        if not port_mapping:
            detailed_logger.log('warning', "No port mapping found. Checking container logs...")
            logs = container.logs().decode('utf-8')
            return JsonResponse({
                'status': 'error',
                'message': 'No port mapping found',
                'container_info': container_info,
                'logs': logs
            }, status=500)

        host_port = port_mapping[0]['HostPort']
        dynamic_url = f"https://{host_port}.{HOST_URL}"

        try:
            # Update component code
            build_output, files_added, compilation_status, installed_packages = update_code_internal(container, code,
                                                                                                     user_id, file_name,
                                                                                                     main_file_path)
            container_info['build_status'] = 'updated'
            container_info['files_added'] = files_added

            # Get file structure and logs
            file_structure = get_container_file_structure(container)
            detailed_logs = container.logs(tail=200).decode('utf-8')

            return JsonResponse({
                'status': 'success',
                'message': 'Container is running',
                'container_id': container.id,
                'url': dynamic_url,
                'can_deploy': True,
                'container_info': container_info,
                'build_output': build_output,
                'detailed_logs': detailed_logs,
                'file_list': file_structure,
                'files_added': files_added,
                'compilation_status': compilation_status,
                'installed_packages': installed_packages
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
        detailed_logger.log('info', f"Creating new container: {container_name}")
        host_port = get_available_port(HOST_PORT_RANGE_START, HOST_PORT_RANGE_END)

        try:
            # Create new container with Next.js setup
            container = client.containers.run(
                'react_renderer_prod',
                command=["sh", "-c", "cd /app && yarn dev -p 3001"],
                detach=True,
                name=container_name,
                environment={
                    'PORT': '3001',
                    'HOST': '0.0.0.0',
                    'NODE_ENV': 'development',
                    'NODE_OPTIONS': '--max-old-space-size=8192',
                    'NEXT_TELEMETRY_DISABLED': '1',
                    'WATCHPACK_POLLING': 'true'  # Enable polling for file changes
                },
                volumes={
                    # Mount entire app directory
                    react_renderer_path: {
                        'bind': '/app',
                        'mode': 'rw'
                    }
                },
                ports={'3001/tcp': host_port},
                mem_limit='8g',
                memswap_limit='16g',
                cpu_quota=100000,
                working_dir='/app',
                user='node'  # Start with node user
            )

            detailed_logger.log('info', f"New container created: {container_name}")
            container_info['build_status'] = 'created'

            # Set proper permissions for mounted volume
            container.exec_run(
                ["sh", "-c", "chown -R node:node /app && chmod -R 755 /app"],
                user='root'
            )

            # Wait for container readiness
            max_wait = 30
            wait_count = 0
            while wait_count < max_wait:
                container.reload()
                logs = container.logs().decode('utf-8')
                if ('Ready' in logs or 'Compiled successfully' in logs) and container.status == 'running':
                    break
                if container.status == 'exited':
                    raise Exception(f"Container exited. Logs:\n{logs}")
                time.sleep(1)
                wait_count += 1

            # Update component code
            build_output, files_added, compilation_status, installed_packages = update_code_internal(container, code,
                                                                                                     user_id, file_name,
                                                                                                     main_file_path)
            container_info['build_status'] = 'updated'

            # Get final status
            file_structure = get_container_file_structure(container)
            detailed_logs = container.logs(tail=200).decode('utf-8')

            container.reload()
            port_mapping = container.ports.get('3001/tcp')

            if port_mapping:
                dynamic_url = f"https://{host_port}.{HOST_URL}"
                detailed_logger.log('info', f"Container ready: {dynamic_url}")
                return JsonResponse({
                    'status': 'success',
                    'message': 'Container is running',
                    'container_id': container.id,
                    'url': dynamic_url,
                    'can_deploy': True,
                    'container_info': container_info,
                    'build_output': build_output,
                    'detailed_logs': detailed_logs,
                    'file_list': file_structure,
                    'files_added': files_added,
                    'compilation_status': compilation_status,
                    'installed_packages': installed_packages
                })
            else:
                raise Exception("No port mapping found after container setup")

        except Exception as e:
            detailed_logger.log('error', f"Container setup failed: {str(e)}")
            return JsonResponse({
                'error': str(e),
                'container_info': container_info,
                'detailed_logs': detailed_logger.get_logs(),
                'file_list': locals().get('file_structure', [])
            }, status=500)


# def get_compilation_status(container):
#     """Get compilation status with error recovery"""
#     try:
#         # Try to read the compilation status file
#         status_result = container.exec_run(
#             [
#                 "sh", "-c",
#                 "cat /app/compilation_status 2>/dev/null || echo 'COMPILING'"
#             ],
#             user='root'
#         )
#         saved_status = status_result.output.decode().strip()
#
#         if saved_status and saved_status in [
#             ContainerStatus.READY,
#             ContainerStatus.WARNING,
#             ContainerStatus.COMPILATION_FAILED
#         ]:
#             return saved_status
#
#         # Create status file if it doesn't exist
#         container.exec_run(
#             [
#                 "sh", "-c",
#                 "touch /app/compilation_status && chown node:node /app/compilation_status && chmod 644 /app/compilation_status"
#             ],
#             user='root'
#         )
#
#         # Check logs for status
#         logs = container.logs(tail=100).decode('utf-8')
#
#         if "Compiled successfully" in logs:
#             new_status = ContainerStatus.READY
#         elif "Compiled with warnings" in logs:
#             new_status = ContainerStatus.WARNING
#         elif "Failed to compile" in logs:
#             new_status = ContainerStatus.COMPILATION_FAILED
#         else:
#             new_status = ContainerStatus.COMPILING
#
#         # Save the new status
#         container.exec_run(
#             ["sh", "-c", f"echo {new_status} > /app/compilation_status"],
#             user='root'
#         )
#
#         return new_status
#
#     except Exception as e:
#         logger.error(f"Error getting compilation status: {str(e)}")
#         return ContainerStatus.ERROR


@api_view(['GET'])
def check_container(request):
    """
    Check container status and return detailed information about its state
    """
    user_id = request.GET.get('user_id', '0')
    file_name = request.GET.get('file_name', 'test-component.js')
    container_name = f'react_renderer_{user_id}_{file_name}'

    logger.info(f"Checking container status for {container_name}")

    try:
        container = client.containers.get(container_name)
        container.reload()

        # Get basic container info
        container_info = {
            'container_name': container.name,
            'created_at': container.attrs['Created'],
            'status': container.status,
            'ports': container.ports,
            'image': container.image.tags[0] if container.image.tags else 'Unknown',
            'id': container.id,
            'health_status': container.attrs.get('State', {}).get('Health', {}).get('Status', 'unknown')
        }

        # Check if container is running
        if container.status != 'running':
            try:
                logger.info(f"Container {container_name} not running, attempting to start")
                container.start()
                container.reload()
                time.sleep(5)  # Wait for container to start
            except Exception as start_error:
                logger.error(f"Failed to start container: {str(start_error)}")
                return JsonResponse({
                    'status': 'error',
                    'container_id': container.id,
                    'message': f"Failed to start container: {str(start_error)}",
                    'container_info': container_info
                })

        # Check port mapping
        port_mapping = container.ports.get('3001/tcp')
        if not port_mapping:
            logger.warning(f"No port mapping found for container {container_name}")
            return JsonResponse({
                'status': 'not_ready',
                'container_id': container.id,
                'message': 'Container running but port not mapped',
                'container_info': container_info
            })

        # Check directory permissions and structure
        try:
            # Run directory check as root to avoid permission issues
            check_result = container.exec_run(
                "test -d /app/src && echo 'exists' || echo 'not found'",
                user='root'
            )

            if check_result.exit_code != 0 or 'not found' in check_result.output.decode():
                logger.warning(f"/app/src directory not found in container {container_name}")
                # Attempt to fix directory permissions
                set_container_permissions(container)

            # Get file structure
            file_structure = get_container_file_structure(container)

            # Get compilation status
            compilation_status = get_compilation_status(container)

            # Get container logs
            logs = container.logs(tail=100).decode('utf-8')

            host_port = port_mapping[0]['HostPort']
            url = f"https://{host_port}.{HOST_URL}"

            # Check if container is actually ready
            ready_status = (
                    container.status == 'running' and
                    compilation_status in [ContainerStatus.READY, ContainerStatus.WARNING] and
                    bool(port_mapping)
            )

            return JsonResponse({
                'status': 'ready' if ready_status else 'initializing',
                'container_id': container.id,
                'container_info': container_info,
                'url': url,
                'file_list': file_structure,
                'compilation_status': compilation_status,
                'detailed_logs': detailed_logger.get_logs(),
                'recent_logs': logs,
                'port': host_port,
                'message': 'Container is ready' if ready_status else 'Container is initializing'
            })

        except Exception as check_error:
            logger.error(f"Error checking container structure: {str(check_error)}")
            return JsonResponse({
                'status': 'error',
                'container_id': container.id,
                'message': f"Error checking container structure: {str(check_error)}",
                'container_info': container_info
            })

    except docker.errors.NotFound:
        logger.warning(f"Container {container_name} not found")
        return JsonResponse({
            'status': 'not_found',
            'message': f"Container {container_name} not found"
        }, status=404)

    except Exception as e:
        logger.error(f"Error checking container {container_name}: {str(e)}", exc_info=True)
        return JsonResponse({
            'status': 'error',
            'message': str(e),
            'error_details': traceback.format_exc()
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


def install_packages(container, packages):
    installed_packages = []
    failed_packages = []

    logger.info(f"Attempting to install packages: {', '.join(packages)}")

    try:
        # First ensure proper permissions
        if not set_container_permissions(container):
            raise Exception("Failed to set container permissions for package installation")

        for package in packages:
            try:
                logger.info(f"Installing package: {package}")
                # Run yarn commands as node user but with proper permissions
                result = container.exec_run(
                    ["sh", "-c", f"cd /app && yarn add {package}"],
                    user='node',  # Use node user for yarn commands
                    environment={
                        'NODE_OPTIONS': '--max-old-space-size=8192'
                    }
                )

                if result.exit_code == 0:
                    installed_packages.append(package)
                    logger.info(f"Successfully installed package: {package}")

                    # Set proper permissions for installed package
                    fix_permissions = container.exec_run(
                        ["sh", "-c", "chown -R node:node /app/node_modules && chmod -R 755 /app/node_modules"],
                        user='root'
                    )
                    if fix_permissions.exit_code != 0:
                        logger.warning(f"Failed to set permissions for package {package}")
                else:
                    error_output = result.output.decode() if hasattr(result, 'output') else "No error output available"
                    logger.error(
                        f"Failed to install package {package}. Exit code: {result.exit_code}. Error: {error_output}")
                    failed_packages.append(package)

            except docker.errors.APIError as e:
                logger.error(f"Docker API error while installing {package}: {str(e)}")
                failed_packages.append(package)
            except Exception as e:
                logger.error(f"Unexpected error while installing {package}: {str(e)}", exc_info=True)
                failed_packages.append(package)

    except Exception as e:
        logger.error(f"Error in package installation process: {str(e)}")
        if packages not in failed_packages:
            failed_packages.extend(packages)

    finally:
        # Log final status
        if installed_packages:
            logger.info(f"Successfully installed packages: {', '.join(installed_packages)}")
        if failed_packages:
            logger.warning(f"Failed to install packages: {', '.join(failed_packages)}")

        return installed_packages, failed_packages


def check_non_standard_imports(code):
    """
    Check for non-standard imports in React code with improved pattern matching and package recognition.
    Returns a list of non-standard package names that need to be installed.
    """
    try:
        # Enhanced import patterns to catch more variations
        import_patterns = [
            # Standard imports
            r'import\s+(?:{\s*[\w\s,]+\s*}|[\w]+|\*\s+as\s+[\w]+)\s+from\s+[\'"](@?[a-zA-Z0-9\-_/]+(?:\/[a-zA-Z0-9\-_]+)*)[\'"]',
            # Require statements
            r'require\([\'"](@?[a-zA-Z0-9\-_/]+(?:\/[a-zA-Z0-9\-_]+)*?)[\'"]\)',
            # Dynamic imports
            r'import\([\'"](@?[a-zA-Z0-9\-_/]+(?:\/[a-zA-Z0-9\-_]+)*?)[\'"]\)',
            # CSS/Style imports
            r'import\s+[\'"](@?[a-zA-Z0-9\-_/]+(?:\/[a-zA-Z0-9\-_]+)*?\.css)[\'"]'
        ]

        # Standard packages that don't need installation
        standard_packages = {
            # React ecosystem
            'react', 'react-dom', 'react-router', 'react-router-dom', 'prop-types',
            'react-redux', 'redux', 'redux-thunk', 'redux-saga', 'recoil',
            '@redux-toolkit', '@reduxjs/toolkit',

            # UI libraries
            'styled-components', '@emotion/react', '@emotion/styled',
            '@material-ui/core', '@mui/material', '@mui/icons-material',
            '@chakra-ui/react', 'antd', 'tailwindcss',

            # Utilities
            'axios', 'lodash', 'moment', 'date-fns', 'uuid', 'classnames',
            'query-string', 'formik', 'yup', 'zod',

            # Testing
            'jest', '@testing-library/react', '@testing-library/jest-dom',

            # Build tools
            'webpack', 'babel', '@babel/core', '@babel/runtime',
            'typescript', '@types/react', '@types/node',

            # Next.js specific
            'next', 'next/router', 'next/image', 'next/link', 'next/head',
            '@next/font', '@vercel/analytics',
        }

        found_imports = set()
        for pattern in import_patterns:
            matches = re.finditer(pattern, code)
            for match in matches:
                # Get the main package name (first part before any '/')
                full_import = match.group(1)
                package_name = full_import.split('/')[0]

                # Handle scoped packages (e.g., @mui/material)
                if package_name.startswith('@'):
                    package_name = '/'.join(full_import.split('/')[:2])

                found_imports.add(package_name)

        # Filter out standard packages and local imports
        non_standard_imports = [
            imp for imp in found_imports
            if not any([
                imp in standard_packages,
                imp.startswith('.'),
                imp.startswith('/'),
                imp.endswith('.css'),
                imp.endswith('.scss'),
                imp.endswith('.less'),
                imp.endswith('.svg'),
                imp.endswith('.png'),
                imp.endswith('.jpg'),
                imp.endswith('.jpeg')
            ])
        ]

        # Log findings
        if non_standard_imports:
            logger.info(f"Found non-standard imports: {', '.join(non_standard_imports)}")
        else:
            logger.info("No non-standard imports found")

        return list(set(non_standard_imports))  # Remove duplicates

    except Exception as e:
        logger.error(f"Error checking non-standard imports: {str(e)}", exc_info=True)
        # Return empty list on error to prevent installation attempts
        return []


def normalize_package_name(package_name):
    """Normalize package names for comparison"""
    return package_name.lower().replace('-', '').replace('_', '')


def is_subpackage(package, standard_package):
    """Check if a package is a subpackage of a standard package"""
    normalized_package = normalize_package_name(package)
    normalized_standard = normalize_package_name(standard_package)
    return normalized_package.startswith(normalized_standard)


def check_local_imports(container, code):
    """Check local imports with proper permissions and detailed error handling"""
    try:
        local_import_pattern = r'from\s+[\'"]\.\/(\w+)[\'"]|import\s+[\'"]\.\/(\w+)[\'"]'
        local_imports = set()

        # Find all local imports
        for match in re.finditer(local_import_pattern, code):
            imp = match.group(1) or match.group(2)
            if imp:
                local_imports.add(imp)

        if not local_imports:
            return []

        missing_imports = []

        # Create check script with proper permissions
        check_script = """
            for file in "$@"; do
                if [ -f "/app/src/${file}.js" ] || [ -f "/app/src/${file}.jsx" ] || \
                   [ -f "/app/src/${file}.ts" ] || [ -f "/app/src/${file}.tsx" ]; then
                    echo "${file}:exists"
                else
                    echo "${file}:missing"
                fi
            done
        """

        # Write and execute check script with proper permissions
        exec_result = container.exec_run(
            ["sh", "-c", check_script + " " + " ".join(local_imports)],
            user='root'
        )

        if exec_result.exit_code == 0:
            for line in exec_result.output.decode().strip().split('\n'):
                if line:
                    file_name, status = line.split(':')
                    if status == 'missing':
                        missing_imports.append(file_name)
                        logger.warning(f"Missing local import: {file_name}")
        else:
            logger.error(f"Error checking local imports: {exec_result.output.decode()}")
            raise Exception(f"Failed to check local imports: {exec_result.output.decode()}")

        return missing_imports

    except Exception as e:
        logger.error(f"Error checking local imports: {str(e)}", exc_info=True)
        # Return all imports as missing in case of error
        return list(local_imports) if 'local_imports' in locals() else []


def get_container_file_structure(container):
    """Get the file structure of the container with proper permissions and error handling"""
    try:
        # Run find command as root to avoid permission issues
        exec_result = container.exec_run(
            [
                "sh", "-c",
                "find /app/src -printf '%P\t%s\t%T@\t%y\t%U:%G\t%m\n'"
            ],
            user='root'
        )

        logger.info(f"Find command exit code: {exec_result.exit_code}")

        if exec_result.exit_code == 0:
            files = []
            output = exec_result.output.decode().strip()

            if not output:  # Empty directory
                logger.warning("No files found in /app/src")
                return []

            for line in output.split('\n'):
                try:
                    parts = line.split('\t')
                    if len(parts) >= 6:
                        path, size, timestamp, type, ownership, perms = parts[:6]
                        files.append({
                            'path': path,
                            'size': int(size),
                            'created_at': datetime.fromtimestamp(float(timestamp)).isoformat(),
                            'type': 'file' if type == 'f' else 'folder',
                            'ownership': ownership,
                            'permissions': perms,
                            'last_modified': datetime.fromtimestamp(float(timestamp)).isoformat()
                        })
                except Exception as parse_error:
                    logger.error(f"Error parsing file entry: {line}. Error: {str(parse_error)}")
                    continue

            return files
        else:
            error_output = exec_result.output.decode()
            logger.error(f"Error executing find command. Exit code: {exec_result.exit_code}")
            logger.error(f"Error output: {error_output}")

            # Try to create src directory if it doesn't exist
            if "No such file or directory" in error_output:
                logger.info("Attempting to create /app/src directory")
                create_result = container.exec_run(
                    ["sh", "-c", "mkdir -p /app/src && chown -R node:node /app/src && chmod -R 755 /app/src"],
                    user='root'
                )
                if create_result.exit_code == 0:
                    return []  # Return empty list for newly created directory
                else:
                    raise Exception(f"Failed to create /app/src directory: {create_result.output.decode()}")

            return []

    except Exception as e:
        logger.error(f"Error getting container file structure: {str(e)}", exc_info=True)
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






