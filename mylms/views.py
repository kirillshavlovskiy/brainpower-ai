import subprocess
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import tempfile
import os

def run_python_code(code):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        # Run the code in a separate process with resource limits
        result = subprocess.run(['python', temp_file_path],
                                capture_output=True,
                                text=True,
                                timeout=5,  # 5 seconds timeout
                                check=True)
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out"
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

def run_javascript_code(code):
    with tempfile.NamedTemporaryFile(mode='w', suffix='.js', delete=False) as temp_file:
        temp_file.write(code)
        temp_file_path = temp_file.name

    try:
        # Run the code using Node.js in a separate process with resource limits
        result = subprocess.run(['node', temp_file_path],
                                capture_output=True,
                                text=True,
                                timeout=5,  # 5 seconds timeout
                                check=True)
        return result.stdout
    except subprocess.TimeoutExpired:
        return "Error: Code execution timed out"
    except subprocess.CalledProcessError as e:
        return f"Error: {e.stderr}"
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

@csrf_exempt
@require_http_methods(["POST"])
def execute_code(request):
    try:
        data = json.loads(request.body)
        code = data.get('code', '')
        language = data.get('language', '').lower()

        if language == 'python':
            output = run_python_code(code)
        elif language == 'javascript':
            output = run_javascript_code(code)
        else:
            return JsonResponse({'error': 'Unsupported language'}, status=400)

        return JsonResponse({'output': output})
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# Create your views here.
