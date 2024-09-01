import subprocess
import json
import traceback
import docker
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import logging

logger = logging.getLogger(__name__)

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json


@csrf_exempt
@require_http_methods(["POST"])
def test_docker(request):
    try:
        data = json.loads(request.body)
        command = data.get('command', 'echo "Default Docker test"')

        client = docker.from_env()
        container = client.containers.run(
            'react-renderer',
            volumes={tmpdir: {'bind': '/app', 'mode': 'rw'}},
            detach=True
        )

        output = container.decode('utf-8').strip()
        return JsonResponse({'output': output})

    except docker.errors.DockerException as e:
        return JsonResponse({'error': f'Docker error: {str(e)}'}, status=500)
    except Exception as e:
        return JsonResponse({'error': f'Unexpected error: {str(e)}'}, status=500)

import logging


logger = logging.getLogger(__name__)

import subprocess
import os
from django.http import JsonResponse
from rest_framework.decorators import api_view
import requests

logger = logging.getLogger(__name__)

@api_view(['POST'])
def execute_code(request):
    logger.info("Received POST request to execute_code")
    code = request.data.get('code')
    language = request.data.get('language')

    if language != 'react':
        logger.error("Unsupported language")
        return JsonResponse({'error': 'Unsupported language'}, status=400)

    react_renderer_path = '/Users/kirillshavlovskiy/mylms/react_renderer'
    logger.info(f"Using react_renderer_path: {react_renderer_path}")

    try:
        os.makedirs(os.path.join(react_renderer_path, 'src'), exist_ok=True)
        logger.info("Directory structure ensured")
    except Exception as e:
        logger.error(f"Error ensuring directory structure: {e}")
        return JsonResponse({'error': f"Error ensuring directory structure: {e}"}, status=500)

    try:
        with open(os.path.join(react_renderer_path, 'src', 'component.js'), 'w') as f:
            f.write(code)
        logger.info("Code written to component.js")
    except Exception as e:
        logger.error(f"Error writing component.js: {e}")
        return JsonResponse({'error': f"Error writing component.js: {e}"}, status=500)

    # Stop and remove any existing containers
    try:
        subprocess.run(['docker', 'ps', '-q', '--filter', 'name=react_renderer'], capture_output=True, text=True)
        container_id = subprocess.run(['docker', 'ps', '-q', '--filter', 'name=react_renderer'], capture_output=True, text=True).stdout.strip()
        if container_id:
            subprocess.run(['docker', 'stop', container_id], check=True)
            subprocess.run(['docker', 'rm', container_id], check=True)
            logger.info(f"Stopped and removed existing container: {container_id}")
    except Exception as e:
        logger.error(f"Error stopping/removing existing container: {e}")

    try:
        build_result = subprocess.run(
            ['docker', 'build', '-t', 'react_renderer', react_renderer_path],
            capture_output=True,
            text=True
        )
        logger.info(f"Docker build result: {build_result.stdout}")
        if build_result.returncode != 0:
            raise Exception(build_result.stderr)
        logger.info("Docker image built successfully")
    except Exception as e:
        logger.error(f"Error building Docker image: {e}")
        return JsonResponse({'error': f"Error building Docker image: {e}"}, status=500)

    try:
        run_result = subprocess.run(
            ['docker', 'run', '--rm', '-d', '--name', 'react_renderer', '-p', '3001:3001', 'react_renderer'],
            capture_output=True,
            text=True,
            check=True
        )
        container_id = run_result.stdout.strip()
        logger.info(f"Docker container is running with ID: {container_id}")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running Docker container: {e.stderr}")
        return JsonResponse({'error': f"Error running Docker container: {e.stderr}"}, status=500)
    except Exception as e:
        logger.error(f"Unexpected error running Docker container: {str(e)}")
        return JsonResponse({'error': f"Unexpected error running Docker container: {str(e)}"}, status=500)

    return JsonResponse({
        'message': 'Docker container is running. Access it at http://localhost:3001',
        'container_id': container_id
    })


@api_view(['GET'])
def check_container_ready(request):
    container_id = request.GET.get('container_id')
    if not container_id:
        return JsonResponse({'error': 'No container ID provided'}, status=400)

    try:
        # Check if the container is running
        result = subprocess.run(
            ['docker', 'inspect', '--format={{.State.Running}}', container_id],
            capture_output=True,
            text=True,
            check=True
        )
        is_running = result.stdout.strip() == 'true'

        if not is_running:
            return JsonResponse({'is_ready': False, 'reason': 'Container not running'})

        # Check if the application is responding
        try:
            response = requests.get('http://localhost:3001', timeout=1)
            is_responding = response.status_code == 200
        except requests.RequestException:
            is_responding = False

        return JsonResponse({'is_ready': is_running and is_responding})
    except subprocess.CalledProcessError:
        return JsonResponse({'error': 'Container not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def process_javascript_code(code):
    logger.info("Starting JavaScript code execution")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        logger.info(f"Running JavaScript code from file: {temp_file_path}")
        result = subprocess.run(['node', temp_file_path],
                                capture_output=True,
                                text=True,
                                timeout=30)  # 30 seconds timeout

        logger.info(f"JavaScript execution result: {result.returncode}")
        logger.info(f"JavaScript stdout: {result.stdout}")
        logger.info(f"JavaScript stderr: {result.stderr}")

        if result.returncode != 0:
            output = f"Error:\n{result.stderr}"
        else:
            output = result.stdout

        logger.info("Returning JavaScript execution result")
        return JsonResponse({'output': output, 'language': 'javascript'})

    except subprocess.TimeoutExpired:
        logger.error("JavaScript execution timed out")
        return JsonResponse({'error': 'Execution timed out'}, status=408)
    except Exception as e:
        logger.error(f"JavaScript Execution Error: {str(e)}")
        return JsonResponse({'error': f'Execution error: {str(e)}'}, status=500)
    finally:
        os.unlink(temp_file_path)

def process_python_code(code):
    logger.info("Starting Python code execution")
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        logger.info(f"Running Python code from file: {temp_file_path}")
        result = subprocess.run(['python', temp_file_path],
                                capture_output=True,
                                text=True,
                                timeout=30)  # 30 seconds timeout

        logger.info(f"Python execution result: {result.returncode}")
        logger.info(f"Python stdout: {result.stdout}")
        logger.info(f"Python stderr: {result.stderr}")

        if result.returncode != 0:
            output = f"Error:\n{result.stderr}"
        else:
            output = result.stdout

        logger.info("Returning Python execution result")
        return JsonResponse({'output': output, 'language': 'python'})

    except subprocess.TimeoutExpired:
        logger.error("Python execution timed out")
        return JsonResponse({'error': 'Execution timed out'}, status=408)
    except Exception as e:
        logger.error(f"Python Execution Error: {str(e)}")
        return JsonResponse({'error': f'Execution error: {str(e)}'}, status=500)
    finally:
        os.unlink(temp_file_path)

@csrf_exempt
@require_http_methods(["POST"])
def deploy_component(request):
    try:
        logger.info("Received deploy_component request")
        data = json.loads(request.body)

        html_content = data.get('html', '')
        logger.debug(f"HTML content length: {len(html_content)}")

        if not html_content:
            logger.warning("No HTML content provided")
            return JsonResponse({'error': 'No HTML content provided'}, status=400)

        filename = f"component_{int(time.time())}.html"
        file_path = os.path.join(settings.DEPLOYED_COMPONENTS_ROOT, filename)
        logger.info(f"Attempting to write file: {file_path}")

        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"File written successfully: {file_path}")

        deployed_url = f"{settings.DEPLOYED_COMPONENTS_URL}{filename}"
        logger.info(f"Component deployed successfully: {deployed_url}")

        return JsonResponse({'url': deployed_url})

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON received: {str(e)}")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected Error in deploy_component: {str(e)}")
        logger.error(traceback.format_exc())
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)