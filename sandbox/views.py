import re
import subprocess
import tempfile
import json
import os
import traceback
import time
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import logging

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def execute_code(request):
    logger.info("execute_code function called")
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        language = data.get('language', '').lower()

        logger.info(f"Received {language} code: {code[:100]}...")  # Log first 100 chars of code

        # Simply return the code and language without any processing
        return JsonResponse({
            'code': code,
            'language': language
        })

    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error: {str(e)}")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Unexpected Error: {str(e)}", exc_info=True)
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


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


def process_react_code(code):
    logger.info("React code processing started")

    try:
        # Simple processing for React JSX
        def process_jsx(jsx_code):
            # Convert JSX to React.createElement calls
            def replace_jsx(match):
                tag = match.group(1)
                attrs = match.group(2)
                children = match.group(3)

                attr_str = ''
                if attrs:
                    attr_pairs = re.findall(r'(\w+)=\{([^}]+)\}', attrs)
                    attr_str = ', {' + ', '.join(f"'{k}': {v}" for k, v in attr_pairs) + '}'

                if children:
                    return f"React.createElement('{tag}'{attr_str}, {children})"
                else:
                    return f"React.createElement('{tag}'{attr_str})"

            processed = re.sub(r'<(\w+)([^>]*)>([^<]*)<\/\1>', replace_jsx, jsx_code)
            return processed

        # Remove import statements
        code_without_imports = re.sub(r'import.*?;', '', code)

        # Process JSX
        processed_code = process_jsx(code_without_imports)

        logger.info("Processing completed successfully")
        logger.info(f"Processed code preview: {processed_code[:100]}...")  # Log first 100 chars

        return JsonResponse({
            'processedCode': processed_code,
            'language': 'javascript'
        })

    except Exception as e:
        logger.error(f"Processing Error: {str(e)}")
        return JsonResponse({'error': f'Processing error: {str(e)}'}, status=500)


logger = logging.getLogger(__name__)


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
