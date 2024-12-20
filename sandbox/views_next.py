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
import psutil
from pathlib import Path

logger = logging.getLogger(__name__)
client = docker.from_env()

HOST_URL = 'brainpower-ai.net'
HOST_PORT_RANGE_START = 32768
HOST_PORT_RANGE_END = 60999
NGINX_SITES_DYNAMIC = '/etc/nginx/sites-dynamic'

# Add this with other global variables at the top
react_renderer_path = os.path.join(settings.BASE_DIR, 'react_renderer')

REUSABLE_COMPONENTS_HOST_PATH = '/home/ubuntu/brainpower-ai/react_renderer_next/components/reusable-components'
CONTAINER_COMPONENTS_PATH = '/app/components/reusable-components'


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

        # Check if container is actually running
        if container.status != 'running':
            logger.error(f"Container {container_name} is not running. Status: {container.status}")
            return JsonResponse({
                'status': 'error',
                'message': f'Container is not running. Status: {container.status}'
            }, status=500)

        # Test the connection to the container
        try:
            response = requests.get('http://localhost:3001', timeout=5)
            if response.status_code != 200:
                logger.error(f"Container health check failed. Status code: {response.status_code}")
                return JsonResponse({
                    'status': 'error',
                    'message': f'Container health check failed. Status code: {response.status_code}'
                }, status=500)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to connect to container: {str(e)}")
            return JsonResponse({
                'status': 'error',
                'message': f'Failed to connect to container: {str(e)}'
            }, status=500)

        return JsonResponse({
            'status': 'ready',
            'container_id': container.id,
            'url': 'https://3001.brainpower-ai.net',
            'container_info': {
                'status': container.status,
                'ports': container.ports,
                'name': container.name
            }
        })

    except docker.errors.NotFound:
        return JsonResponse({
            'status': 'not_found',
            'message': f'Container {container_name} not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error checking container: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
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

        # Create directories and initial files
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

        # Create page.tsx with proper dynamic import
        page_content = '''
import dynamic from 'next/dynamic'

const DynamicComponent = dynamic(() => import('../../components/dynamic/placeholder'), {
  loading: () => <p>Loading...</p>,
  ssr: false
})

export default function Home() {
  return (
    <div className="min-h-screen p-4">
      <DynamicComponent />
    </div>
  )
}
'''
        # Write page.tsx
        encoded_page = base64.b64encode(page_content.encode()).decode()
        result = container.exec_run(
            ["sh", "-c", f"echo {encoded_page} | base64 -d > /app/src/app/page.tsx"],
            user='root'
        )
        if result.exit_code != 0:
            logger.error(f"Failed to write page.tsx: {result.output.decode()}")
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
    try:
        # First mount/update reusable components
        logger.info("Mounting reusable components before code update")
        mount_reusable_components(container)

        # Then write component code
        target_path = "/app/components/dynamic/placeholder.tsx"
        logger.info(f"Writing component to path: {target_path}")

        # Clean up the code
        clean_code = code.replace('\\"', '"')
        clean_code = clean_code.replace('\\n', '\n')

        # Write the code using heredoc
        exec_result = container.exec_run([
            "sh", "-c",
            f"""cat << 'EOL' > {target_path}
{clean_code}
EOL"""
        ], user='node')

        if exec_result.exit_code != 0:
            raise Exception(f"Failed to write component to {target_path}: {exec_result.output.decode()}")

        # Verify the written code
        verify_result = container.exec_run(["cat", target_path])
        logger.info(f"Written file contents:\n{verify_result.output.decode()}")

        files_added.append(target_path)
        logger.info(f"Successfully wrote component to {target_path}")

        # Get container logs
        logs = container.logs(tail=100).decode('utf-8')
        compilation_status = ContainerStatus.COMPILING

        return logs, files_added, compilation_status

    except Exception as e:
        logger.error(f"Error updating code in container: {str(e)}")
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


def check_system_resources():
    """Check if system has enough resources to create a new container"""
    try:
        # Check CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)

        # Check memory
        memory = psutil.virtual_memory()

        # Check disk space
        disk = psutil.disk_usage('/')

        # Define thresholds
        CPU_THRESHOLD = 80  # 80% CPU usage
        MEMORY_THRESHOLD = 80  # 80% memory usage
        DISK_THRESHOLD = 80  # 80% disk usage

        # Simple status check
        if cpu_percent > CPU_THRESHOLD or \
                memory.percent > MEMORY_THRESHOLD or \
                disk.percent > DISK_THRESHOLD:
            return False

        return True

    except Exception as e:
        logger.error(f"Error checking system resources: {str(e)}")
        return False


def mount_reusable_components(container):
    """Mount all reusable components into the container"""
    try:
        logger.info(f"Mounting reusable components to container {container.id}")

        # Create reusable components directory in container
        container.exec_run(f"mkdir -p {CONTAINER_COMPONENTS_PATH}", user='root')

        # List of all reusable components to mount
        components = [
            'solution-card.tsx',
            'pricing-card.tsx',
            'chart-widget.tsx',
            'clock-widget.tsx',
            'payment-form-widget.tsx'
        ]

        # Copy each component file from host to container
        for component_name in components:
            try:
                component_path = os.path.join(REUSABLE_COMPONENTS_HOST_PATH, component_name)
                if not os.path.exists(component_path):
                    logger.warning(f"Component file not found: {component_path}")
                    continue

                with open(component_path, 'r') as f:
                    content = f.read()
                    encoded_content = base64.b64encode(content.encode()).decode()

                target_path = f"{CONTAINER_COMPONENTS_PATH}/{component_name}"

                # Write component file to container
                result = container.exec_run(
                    ["sh", "-c", f"echo {encoded_content} | base64 -d > {target_path}"],
                    user='root'
                )

                if result.exit_code != 0:
                    logger.error(f"Failed to write {component_name}: {result.output.decode()}")
                    continue

                # Set proper permissions
                container.exec_run(f"chown node:node {target_path}", user='root')
                container.exec_run(f"chmod 644 {target_path}", user='root')

                logger.info(f"Successfully mounted {component_name}")

            except Exception as e:
                logger.error(f"Error mounting {component_name}: {str(e)}")
                continue

        return True

    except Exception as e:
        logger.error(f"Error mounting reusable components: {str(e)}")
        return False


@api_view(['POST'])
def check_or_create_container(request):
    try:
        data = request.data
        code = data.get('main_code')
        user_id = "0"
        file_name = "placeholder.tsx"
        main_file_path = "/components/dynamic/placeholder.tsx"

        container_name = f'react_renderer_next_{user_id}_{file_name}'
        logger.info(f"Checking container: {container_name}")

        try:
            # Try to get existing container
            container = client.containers.get(container_name)
            container.reload()

            if container.status != 'running':
                logger.info(f"Container exists but not running. Starting it...")
                container.start()

            # Mount reusable components first
            mount_reusable_components(container)

            # Then update code
            logs, files_added, compilation_status = update_code_internal(
                container, code, user_id, file_name, main_file_path
            )

            logger.info(f"Updated code in existing container: {container.id}")

        except docker.errors.NotFound:
            logger.info(f"Container not found, creating new one...")
            # Create new container
            container = client.containers.run(
                'react_renderer_next',
                detach=True,
                name=container_name,
                environment={
                    'PORT': '3001',
                    'NODE_ENV': 'development',
                    'HOST': '0.0.0.0'
                },
                volumes={
                    os.path.join(react_renderer_path, 'components/dynamic'): {
                        'bind': '/app/components/dynamic',
                        'mode': 'rw'
                    },
                    REUSABLE_COMPONENTS_HOST_PATH: {
                        'bind': CONTAINER_COMPONENTS_PATH,
                        'mode': 'rw'
                    }
                },
                ports={'3001/tcp': 3001},
                mem_limit='1g',
                memswap_limit='2g',
                cpu_period=100000,
                cpu_quota=50000,
                restart_policy={"Name": "on-failure", "MaximumRetryCount": 5}
            )

            # Mount reusable components first
            mount_reusable_components(container)

            # Then write initial code
            logs, files_added, compilation_status = update_code_internal(
                container, code, user_id, file_name, main_file_path
            )

        return JsonResponse({
            'status': 'success',
            'container_id': container.id,
            'url': 'https://3001.brainpower-ai.net',
            'detailed_logs': logs
        })

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'detailed_logs': []
        }, status=500)


def cleanup_old_containers():
    """Clean up old containers and unused images"""
    try:
        # Remove stopped containers
        containers = client.containers.list(all=True)
        for container in containers:
            if container.status == 'exited':
                container.remove()

        # Remove unused images
        client.images.prune()

        # Remove unused volumes
        client.volumes.prune()

    except Exception as e:
        logger.error(f"Cleanup error: {str(e)}")


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

    try:
        container = client.containers.get(container_id)

        # Update code without restarting container
        logs, files_added, compilation_status = update_code_internal(
            container, main_code, user_id, file_name, main_file_path
        )

        return JsonResponse({
            'status': 'success',
            'container_id': container_id,
            'url': 'https://3001.brainpower-ai.net',
            'compilation_status': compilation_status,
            'logs': logs
        })

    except docker.errors.NotFound:
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


def cleanup_old_images():
    """Clean up old react_renderer_next images keeping only the latest"""
    try:
        # Get all react_renderer_next images
        images = client.images.list(name='react_renderer_next')

        # Sort by creation time (newest first)
        sorted_images = sorted(images, key=lambda x: x.attrs['Created'], reverse=True)

        # Keep the latest, remove the rest
        if len(sorted_images) > 1:
            for image in sorted_images[1:]:
                try:
                    logger.info(f"Removing old image: {image.id}")
                    client.images.remove(image.id, force=True)
                except Exception as e:
                    logger.warning(f"Failed to remove image {image.id}: {str(e)}")

        # Remove any dangling images
        client.images.prune()

    except Exception as e:
        logger.error(f"Error cleaning up old images: {str(e)}")


@api_view(['POST'])
def execute_next(request):
    try:
        data = request.data
        logger.info(f"Received request data: {data}")

        code = data.get('main_code')
        logger.info(f"Extracted code: {code}")

        # Log the code being written
        logger.info(f"Writing code to placeholder.tsx: {code}")

        # ... rest of the function
    except Exception as e:
        logger.error(f"Error in execute_next: {str(e)}")
        return JsonResponse({
            'error': str(e),
            'status': 'error'
        }, status=500)

