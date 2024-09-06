import time
import traceback
import json
import requests
from django.views.decorators.http import require_http_methods
import os
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view
import docker
import logging

logger = logging.getLogger(__name__)
client = docker.from_env()

from mylms import settings
from docker.errors import NotFound, APIError


@csrf_exempt
@api_view(['POST'])
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

@csrf_exempt
@api_view(['POST'])
def check_or_create_container(request):
    logger.info(f"Received request data: {request.data}")
    code = request.data.get('code')
    language = request.data.get('language')
    user_id = request.data.get('user_id', '0')
    file_name = request.data.get('file_name', 'component.js')

    if not all([code, language, file_name]):
        logger.warning(f"Missing required fields. code: {bool(code)}, language: {bool(language)}, file_name: {bool(file_name)}")
        return JsonResponse({'error': 'Missing required fields'}, status=400)


    if language != 'react':
        return JsonResponse({'error': 'Unsupported language'}, status=400)

    react_renderer_path = '/Users/kirillshavlovskiy/mylms/react_renderer'
    container_name = f'react_renderer_{user_id}_{file_name}'

    try:
        with open(os.path.join(react_renderer_path, 'src', 'component.js'), 'w') as f:
            f.write(code)
        logger.info("Code written to component.js")

        try:
            container = client.containers.get(container_name)
            if container.status != 'running':
                container.start()
            logger.info(f"Container {container_name} is running")
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

        # Wait for port mapping to be available
        max_retries = 10
        for _ in range(max_retries):
            container.reload()
            port_mapping = container.ports.get('3001/tcp')
            if port_mapping:
                host_port = port_mapping[0]['HostPort']
                break
            time.sleep(1)
        else:
            raise Exception("Timeout waiting for port mapping")

        # Construct the dynamic URL
        dynamic_url = f"http://localhost:{host_port}/{user_id}/{file_name}"
        logger.info(f"Dynamic URL: {dynamic_url}")

        return JsonResponse({
            'status': 'success',
            'message': 'Container is running',
            'container_id': container.id,
            'url': dynamic_url,
        })

    except Exception as e:
        logger.error(f"Error in check_or_create_container: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)



def update_code_in_container(container, code, file_name):
    try:
        exec_result = container.exec_run(
            f"sh -c 'echo \"{code}\" > /app/src/{file_name}'"
        )
        if exec_result.exit_code != 0:
            raise Exception(f"Failed to update code: {exec_result.output.decode()}")
        logger.info(f"Code updated in container: {container.id}")
    except Exception as e:
        logger.error(f"Error updating code in container: {str(e)}", exc_info=True)
        raise


def wait_for_container_ready(container, user_id, file_name):
    max_retries = 30
    for _ in range(max_retries):
        container.reload()
        port_mapping = container.ports.get('3001/tcp')
        if port_mapping:
            host_port = port_mapping[0]['HostPort']
            dynamic_url = f"http://localhost:{host_port}/{user_id}/{file_name}"
            try:
                response = requests.get(dynamic_url, timeout=2)
                if response.status_code == 200 and 'root' in response.text and 'react' in response.text.lower():
                    logger.info(f"Container ready: {dynamic_url}")
                    return dynamic_url
            except requests.RequestException:
                pass
        time.sleep(1)
    raise Exception("Timeout waiting for container to be ready")

def container_exists(container_id):
    try:
        client.containers.get(container_id)
        return True
    except docker.errors.NotFound:
        return False

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
    code = request.data.get('code')
    file_name = 'component.js'  # Hardcoded for now, but consider making this dynamic in the future
    logger.info(f"Received update request for container: {container_id}, file: {file_name}")

    if not container_id or not code:
        logger.warning("Missing container_id or code in update request")
        return JsonResponse({'error': 'Missing container_id or code'}, status=400)

    try:
        # Path to the source directory in your Django project
        source_dir = os.path.join(settings.BASE_DIR, 'react_renderer', 'src')
        file_path = os.path.join(source_dir, file_name)

        logger.info(f"Attempting to write to file: {file_path}")

        # Ensure the directory exists
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write the code to the file
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(code)

        logger.info(f"Successfully wrote to file: {file_path}")

        # Get the container
        container = client.containers.get(container_id)

        # Touch the file in the container to trigger file change detection
        exec_result = container.exec_run(["touch", f"/app/src/{file_name}"])
        if exec_result.exit_code != 0:
            raise Exception(f"Failed to touch file in container: {exec_result.output.decode()}")

        logger.info(f"Touched file in container: /app/src/{file_name}")
        return JsonResponse({'status': 'Code updated successfully'})

    except docker.errors.NotFound:
        logger.error(f"Container not found: {container_id}")
        return JsonResponse({'error': 'Container not found'}, status=404)
    except Exception as e:
        logger.error(f"Error updating code: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
@api_view(['GET'])
def check_container_ready(request):
    container_id = request.GET.get('container_id')
    user_id = request.GET.get('user_id', 'default')
    file_name = request.GET.get('file_name')
    logger.info(
        f"Checking container readiness for container_id: {container_id}, user_id: {user_id}, file_name: {file_name}")

    if not container_id:
        logger.warning("No container ID provided")
        return JsonResponse({'error': 'No container ID provided'}, status=400)

    try:
        container = client.containers.get(container_id)
        container.reload()
        container_status = container.status
        logger.info(f"Container status: {container_status}")

        if container_status != 'running':
            return JsonResponse({'status': 'container_starting'})

        # Get the assigned port
        port_mapping = container.ports.get('3001/tcp')
        if not port_mapping:
            return JsonResponse({'status': 'waiting_for_port'})

        host_port = port_mapping[0]['HostPort']
        dynamic_url = f"http://localhost:{host_port}/{user_id}/rendered-component"

        # Check if the dev server is responding and the content is available
        try:
            response = requests.get(dynamic_url, timeout=2)
            if response.status_code == 200:
                # Check if the response contains expected React content
                if 'root' in response.text and 'react' in response.text.lower():
                    return JsonResponse({
                        'status': 'ready',
                        'url': dynamic_url
                    })
                else:
                    return JsonResponse({'status': 'content_loading'})
            else:
                return JsonResponse({'status': 'server_starting'})
        except requests.RequestException:
            return JsonResponse({'status': 'server_starting'})

    except docker.errors.NotFound:
        logger.error(f"Container with ID {container_id} not found", exc_info=True)
        return JsonResponse(
            {'error': 'Container not found', 'details': 'The container may have stopped or been removed'}, status=404)
    except Exception as e:
        logger.error(f"Error checking container status: {str(e)}", exc_info=True)
        return JsonResponse({'error': 'Error checking container status', 'details': str(e)}, status=500)

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


from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
import base64
import os

def ui_analyzer(url: str, viewport_width: int = 1920, viewport_height: int = 1080) -> dict:
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument(f"--window-size={viewport_width},{viewport_height}")

    try:
        with webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options) as driver:
            driver.get(url)

            # Get page title and HTML
            page_title = driver.title
            page_html = driver.page_source

            # Take screenshot
            screenshot_path = "screenshot.png"
            driver.save_screenshot(screenshot_path)

            # Encode screenshot to base64
            with open(screenshot_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode('utf-8')

            # Clean up the screenshot file
            os.remove(screenshot_path)

        return {
            "title": page_title,
            "html": page_html,
            "screenshot": encoded_image
        }

    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}
