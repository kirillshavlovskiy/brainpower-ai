import logging
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from .models import Thread, UserProfile
from .serializers import ThreadSerializer
import uuid
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from asgiref.sync import sync_to_async, async_to_sync
import json
import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import asyncio
from django.contrib.auth import get_user_model
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse, HttpResponse
from openai import OpenAI
from .forms import ContentForm, CodeForm
from django.shortcuts import get_object_or_404, redirect
from .models import Course, Module, Lesson, Task, Task_thread
from .openai_service import generate_lesson_content, generate_project_content, assistant_thread_run, \
    assistant_preprocess_task, coding_bot_calling, run_loop
from django.shortcuts import render
from .openai_service_frontend import interface_bot_calling
from .python_execution import run_streamlit_app, read_streamlit_code, read_code,  execute_python_code
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods

client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))


# Enable logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
User = get_user_model()
from django.contrib.auth.models import User
from courses.models import UserProfile

@csrf_exempt
@require_http_methods(["POST"])
def user_login(request):
    for user in User.objects.all():
        UserProfile.objects.get_or_create(user=user)
    data = json.loads(request.body)
    username = data.get('username')
    password = data.get('password')

    if username is None or password is None:
        return JsonResponse({'message': 'Please provide both username and password'}, status=400)

    user = authenticate(username=username, password=password)

    if user is not None:
        login(request, user)
        return JsonResponse({
            'message': 'Login successful',
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            }
        }, status=200)
    else:
        return JsonResponse({'message': 'Invalid credentials'}, status=401)


@csrf_exempt
@require_http_methods(["POST"])
def signup(request):
    data = json.loads(request.body)
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')

    if not all([username, email, password]):
        return JsonResponse({'message': 'Please provide all required fields'}, status=400)

    try:
        user = User.objects.create_user(username=username, email=email, password=password)
        return JsonResponse({'message': 'User created successfully', 'id': user.id}, status=201)
    except Exception as e:
        return JsonResponse({'message': str(e)}, status=400)

@csrf_exempt
@login_required
@require_http_methods(["POST"])
def update_deployment_info(request):
    data = json.loads(request.body)
    file_name = data.get('file_name')
    deployment_info = data.get('deployment_info')

    if not all([file_name, deployment_info]):
        return JsonResponse({'message': 'Please provide both file_name and deployment_info'}, status=400)

    try:
        user_profile, created = UserProfile.objects.get_or_create(user=request.user)
        user_profile.deployed_apps[file_name] = deployment_info
        user_profile.save()
        return JsonResponse({'status': 'success', 'message': 'Deployment info updated'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)


class ThreadViewSet(viewsets.ModelViewSet):
    serializer_class = ThreadSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Thread.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=False, methods=['get'])
    def get_or_create_default(self, request):
        default_thread, created = Thread.objects.get_or_create(
            user=request.user,
            name="Default Thread",
        )
        serializer = self.get_serializer(default_thread)
        return Response(serializer.data)

    def get_queryset(self):
        return Thread.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        name = request.data.get('name', 'Default Thread')
        thread, created = Thread.objects.get_or_create(
            user=request.user,
            name=name
        )
        serializer = self.get_serializer(thread)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class ExecuteView(APIView):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(ExecuteView, self).dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):
        print("post request received")
        message = request.data.get('message')
        code = message.get('code')  # Assuming the code is submitted in the request
        input_values = message.get('input_values')  # Assuming input values are provided
        try:
            response = execute_python_code(code, input_values)
            if len(response) > 4:
                output, complete, prompt_line_n, message, image = response
                print("response", response)
                return Response(
                    {'output': output,
                     'completion': complete,
                     'prompt_line_n': prompt_line_n,
                     'message': message,
                     'image': image,
                     }, status=status.HTTP_200_OK)
            else:
                output, complete, prompt_line_n, message = response
                print("response", response)
                return Response(
                    {'output': output,
                     'completion': complete,
                     'prompt_line_n': prompt_line_n,
                     'message': message,
                     }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f"Error during code execution: {str(e)}", exc_info=True)
            return Response({'error': 'An error occurred during code execution'},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


async def start_group_chat(request):
    print("check if coding_chat started")
    if request.method == 'POST':
        # Extract message from request asynchronously
        message = await sync_to_async(request.POST.get)('input_message')

        # Assuming `app_1.callback` can be awaited, otherwise you need to adapt it

        print("response", response)

        # Reading code can be done asynchronously if I/O bound
        streamlit_code = await sync_to_async(read_streamlit_code)()
        code = await sync_to_async(read_code)()

        # Run the async code execution, adjust `run_streamlit_app` to be async
        process = await run_streamlit_app(streamlit_code)

        # Using subprocess properly in AsyncIO, depending on your implementation
        completion = process.poll()
        output, error = await process.communicate()

        return JsonResponse({
            'completion': completion,
            'response': response,
            'code': code,
            'streamlit_code': streamlit_code,
            'output': output.decode() if output else "",
            'error': error.decode() if error else ""
        })


def start_code_verify(request):
    print("check if coding started")
    if request.method == 'POST':
        message = request.POST.get('input_message')
        code = ""
        language = "Python"
        # message = "Define a function censor_python that takes one parameter:   \
        #        Name: input_strs, Type: list of str, Example Input: [“python“, “hello“, “HELLO“]\
        #     When called, the function should return a new list of strings with the letters “P”,\
        #      “Y”, “T”, “H”, “O”, “N” replaced with “X”, the solution should be case insensitive."
        result = ""
        criteria = ""
        action = ""
        interface_code = ""
        streamlit_code = """
import streamlit as st
import subprocess
import threading
import queue
import time
output_queue = queue.Queue()
class ProcessHandler(threading.Thread):
    def __init__(self, filepath):
        super().__init__()
        self.filepath = filepath
    def run(self):
        with subprocess.Popen(["python3", self.filepath], stdout=subprocess.PIPE) as p:
            for line in p.stdout:
                output_queue.put(line.decode())
user_input = st.sidebar.text_input("Enter some input")
if st.sidebar.button('Start Python Script'):
    script_path = 'streamlit_app_script.py'  # Put the correct path to your python script here
    proc_handler = ProcessHandler(filepath=script_path)
    proc_handler.start()
st.sidebar.write('Output:')
output_textarea = st.sidebar.empty()
while True:
    time.sleep(1)
    while not output_queue.empty():
        output_textarea.code(output_queue.get(), 'python')"""


        def get_prompt_1(language, message):
            return f"Return the code following defined logic. Code should be in {language} language and return result \
                       as per the logic:\n{message}. Return completion status is you completed exercise\
                       check and return interpreter output result if you completed the assignment."
        prompt_1 = get_prompt_1(language, message)
        print("prompt_1: ", prompt_1)
        def get_prompt_2(prompt_1, code, output):
            return f"Check and if needed correct the code. Initial request was: {prompt_1}. Given code is: {code}. \
                        Output is {output}. Check if:\n1. Image encoding code is doing: transformation and saving of the\
                        image into 64base format object\n2. All classes and modules are imported correctly in the beginning\
                        of the code\n3. Returns correct output from interpreter as a. text and/or as image object, also as converted \
                        64base image code."
        def get_prompt_3(prompt_1, code):
            return f"You failed to execute code with valid output corresponding to request: {prompt_1}. Given code is: {code}. \
                        Return corrected code with output statement so achieve valid non zero non Null output from interpreter \
                        and  return it in `output`. Make sure that if code defines function it is called in same code"

        def get_prompt_4(language, code, prompt):
            return f"Change a streamlit app code {streamlit_code} in {language} language to be able to handle following logic:\n\
                    It finally should builds the interface in Streamlit which shows the necessary controls, input fields to accept user\
                    input values and output value/image based on the logic defined by the code: \n{code} been prepared based on given task {prompt}.\n\
                    Avoid using st.pyplot() without any arguments.\n Check yourself using interpreter. Make sure you input all libraries and classes on top of the the code!"

        def get_prompt_5(prompt, interface_code, code, output):
            return f"Check and if needed correct the Streamlit code. Initial request was: {prompt}. Given code is: {interface_code}. \
                        Check if:\n1. All classes and modules are imported correctly in the beginning\
                        of the code\n2. Streamlit Code returns correct output from an interpreter as a. plot object or image \
                        object or message"
        response_log = []
        print("first coding bot call")
        bot_response = coding_bot_calling(prompt_1)
        response_log.append(bot_response[3])
        code = bot_response[1]
        output = bot_response[2]
        interface_prompt = get_prompt_4(language, code, prompt_1)
        print("first interface coding bot call")
        interface_bot_response = interface_bot_calling(interface_prompt)
        print(interface_bot_response)
        interface_code = interface_bot_response[1]
        interface_output = interface_bot_response[2]
        if output:
            print("check previous run")
            bot_response = coding_bot_calling(get_prompt_2(prompt_1, code, output))
        else:
            print("check previous run")
            output = "to be added. Temporary add input \
            values to the code. Run this through interpreter to get valid output. Check that code triggers print \
            function of generate image  or text to reflect the output"
            bot_response = coding_bot_calling(get_prompt_2(prompt_1, code, output))
        response_log.append(bot_response[3])
        status = bot_response[0]
        code = bot_response[1]
        output = bot_response[2]
        response_log.append(bot_response[3])
        #interface_prompt = get_prompt_5(interface_prompt, interface_code, code, interface_output)
        #interface_bot_response = interface_bot_calling(interface_prompt)
        #testing_agent_response = testing_agent_calling(prompt_1, interface_bot_response)
        #interface_code = testing_agent_response[1]
        #interface_output = testing_agent_response[2]
        # if not output:
        #     bot_response = coding_bot_calling(get_prompt_3(prompt_1, code))
        # code = bot_response[1]
        # output = bot_response[2]
        # interface_prompt = get_prompt_5(interface_prompt, interface_code, code, interface_output)
        # interface_bot_response = interface_bot_calling(interface_prompt)
        # testing_agent_response = testing_agent_calling(prompt_1, interface_bot_response)
        #interface_prompt = get_prompt_4(language, code, prompt_1)
        # print("first interface coding bot call")
        #interface_bot_response = interface_bot_calling(interface_prompt)
        #testing_agent_response = testing_agent_calling(interface_prompt, interface_bot_response[1])
        #interface_code = testing_agent_response[1]
        #status = testing_agent_response[0]

        streamlit_code = read_streamlit_code()
        # response = testing_agent_calling(get_prompt(code), streamlit_code)
        run_streamlit_app(streamlit_code)
        update_app_script(code)
        #update_streamlit_script(interface_code)
        #run_streamlit_app(interface_code)


        return JsonResponse({'status': status,
                             'code': code,
                             'streamlit_code': interface_code,
                             'output': output,
                             'log': response_log}
                            )


def update_streamlit_script(code):
    app_filepath = './streamlit_script.py'
    try:
        # Write the new content to streamlit_app_script.py
        with open(app_filepath, 'w') as file:
            file.write(code)

        print("streamlit_app_script.py has been updated successfully with the new content.")

        print("streamlit_app_script.py is launched on local server.")
    except Exception as e:
        print(f"Error updating app.py: {e}")

def update_app_script(code):
    app_filepath = './streamlit_app.py'
    try:
        # Write the new content to streamlit_app_script.py
        with open(app_filepath, 'w') as file:
            file.write(code)

        print("streamlit_app_script.py has been updated successfully with the new content.")

        print("streamlit_app_script.py is launched on local server.")
    except Exception as e:
        print(f"Error updating app.py: {e}")

def extract_input_prompt(code, line):
    return code.split('\n')[line].split("input(", 1)[1].split(")", 1)[0].strip().strip('"').strip("'")


@csrf_exempt
def lesson_process_code(request, lesson_id):
    print('check if code run started on the server and chat initiated')
    #interact_and_code_with_user()


    lesson = get_object_or_404(Lesson, pk=lesson_id)
    tasks = Task.objects.filter(lesson_id=lesson.id)
    image = None
    if request.method == 'POST':
        try:
            form = CodeForm(request.POST)
            if form.is_valid():
                code = form.cleaned_data['code']
                input_values = request.POST.getlist('input_value')
                symbols_processed = str(request.POST.get('symbols_processed', ''))

                response = execute_python_code(code, input_values)

                print(response)
                # handle additional image output if exists
                if len(response) > 4:
                    output, complete, prompt_line_n, message, image = response

                else:
                    output, complete, prompt_line_n, message = response

                output_clean: str = output[
                                    len(symbols_processed):]  # Truncate the output based on symbol processed length

                completion_status = complete == 0

                if complete is None:
                    print("complete is none")
                    return JsonResponse(
                        {'input_requested': True,
                         'prompt_message': prompt_line_n,
                         'output': output_clean,
                         'image': image,
                         })
                elif complete > 0:
                    print("complete >0")
                    return JsonResponse(
                        {'prompt_message': prompt_line_n,
                         'output': output_clean,
                         'completed': completion_status,
                         'message': message,
                         'image': image,
                         })
                else:

                    print("complete = 0")
                    return JsonResponse(
                        {'output': output_clean,
                         'completed': completion_status,
                         'image': image,
                         })

        except Exception as e:
            error_msg = "An error occurred during code execution: {}".format(str(e))
            logging.error(error_msg)
            return JsonResponse({'error': error_msg})
    else:
        form = CodeForm()

    return render(request, "courses/Show_lesson_process_page.html", {
        'form': form,
        'tasks': tasks,
        'lesson': lesson
    })

def retrieve_thread(request):
    try:
        print('Log: start_thread retrieve:')
        if request.method == 'POST':
            task_id = request.POST.get('task_id')
            print(task_id)
            task_thread = Task_thread.objects.filter(task_id=task_id).last()
            messages = client.beta.threads.messages.list(thread_id=task_thread.thread_id)
            print("messages: ", messages)
            return JsonResponse(
                {'messages': messages})
        else:
            # Handle the case when the form is not valid
            print("Form is not valid")
            return JsonResponse({'error': 'Form is not valid'})
    except Exception as e:
        # Handle any exception that occurred

        print('error', str(e))
        return JsonResponse({'error:': str(e)})


def save_thread(request):
    if request.method == 'POST':
        task_id = request.POST.get('task_id')
        print(task_id)
        thread = request.POST.get('thread')
        code = request.POST.get('code_example')
        print(code)
        task_thread = Task_thread.objects.filter(task_id=task_id).last()
        task_thread.learning_thread += [thread]
        print('what is saved: ', task_thread.learning_thread)
        task_thread.code = code
        task_thread.save()
        return JsonResponse({'system_message': 'saved'})
    else:
        # Handle the case when the form is not valid
        print("Form is not valid")
        return JsonResponse({'error': 'Form is not valid'})


def start_thread(request):
    try:
        if request.method == 'POST':
            task_id = request.POST.get('task_id')
            code = request.POST.get('code')
            print(task_id)
            task = get_object_or_404(Task, id=task_id)
            assistant_id = 'asst_Kx2zKp0x0r3fLA6ZFiIGVsPZ'
            print(code)
            if not Task_thread.objects.filter(task=task).exists():
                print('start_thread:')
                print("check if Task_thread object does not exist: passed")
                thread = client.beta.threads.create()
                task_thread = Task_thread.objects.create(thread_id=thread.id,
                                                         assistant_id=assistant_id,
                                                         task=task)
                task_thread.save()
                thread_id = task_thread.thread_id
                prompt_1 = 'There is a task: ' + str(task.description)
                prompt_2 = '\nFor the following code, please provide a detailed explanation starting from topic basics on how we should approach coding task completion:\n' + str(
                    code)
                message = f"{prompt_1} {prompt_2} "
                print(task_thread)
                AI_response = run_loop(message, assistant_id, thread_id)

                print("AI_response: ", AI_response)
                return JsonResponse(
                    {'ai_response': AI_response, 'thread_id': thread_id, 'task_description': task.description,
                     'assistant_id': assistant_id})
            else:
                task_thread = Task_thread.objects.filter(task_id=task_id).last()
                length = len(task_thread.learning_thread)
                messages = task_thread.learning_thread[length - 1]
                print("messages: ", messages)
                return JsonResponse(
                    {'messages': messages, 'thread_id': task_thread.thread_id, 'assistant_id': assistant_id})
        else:
            # Handle the case when the form is not valid
            print("Form is not valid")
            return JsonResponse({'error': 'Form is not valid'})
    except Exception as e:
        # Handle any exception that occurred

        print('error_start thread', str(e))
        return JsonResponse({'error': str(e)})


def chat(request):
    try:
        if request.method == 'POST':
            message = request.POST.get('input_message')
            thread_id = request.POST.get('thread_id')
            if not thread_id:
                thread = client.beta.threads.create()
                thread_id = thread.id
            assistant_id = 'asst_Kx2zKp0x0r3fLA6ZFiIGVsPZ'
            AI_response = run_loop(message, assistant_id, thread_id)
            print("AI_response: ", AI_response)
            return JsonResponse({'ai_response': AI_response, 'thread_id': thread_id, 'assistant_id': assistant_id})
        else:
            # Handle the case when the form is not valid
            print("Form is not valid")
            return JsonResponse({'error': 'Form is not valid'})

    except Exception as e:
        # Handle any exception that occurred
        print('error', str(e))
        return JsonResponse({'error': str(e)})


def code_process_ai(request):
    try:
        if request.method == 'POST':
            print('code_process:')
            code = request.POST.get('code')
            print(code)
            output = request.POST.get('output')
            print(output)
            thread_id = request.POST.get('thread_id')
            print(output)
            task_id = request.POST.get('task_id')
            print(task_id)
            assistant_id = 'asst_Kx2zKp0x0r3fLA6ZFiIGVsPZ'
            if thread_id is None:
                thread = client.beta.threads.create()
                thread_id = thread.id
            if task_id:
                task = get_object_or_404(Task, id=task_id)
                print('task id found: ', task_id)
                result = assistant_preprocess_task(code, output, thread_id, task.description)
                if result is not None and len(result) == 3:
                    ai_response, assistant_id, thread_id = result
                    return JsonResponse(
                        {'ai_response': ai_response, 'thread_id': thread_id, 'assistant_id': assistant_id,
                         'task_description': task.description})
                else:
                    # Handle the case when the result does not contain the expected values
                    print("Error_0: Incorrect number of values returned from assistant_thread_run")
                    return JsonResponse({'error': 'Incorrect number of values returned'})
            else:

                result = assistant_thread_run(code, thread_id, output)
                print('proceed without task:', result)
                if result is not None and len(result) == 3:
                    ai_response, assistant_id, thread_id = result
                    return JsonResponse(
                        {'ai_response': ai_response, 'thread_id': thread_id, 'assistant_id': assistant_id})
                else:
                    # Handle the case when the result does not contain the expected values
                    print("Error_1: Incorrect number of values returned from assistant_thread_run")
                    return JsonResponse({'error': 'Incorrect number of values returned'})
        return JsonResponse({'error': 'Form is not valid'})
    except Exception as e:
        # Handle any exception that occurred
        print('error_0', str(e))
        return JsonResponse({'error_0': str(e)})


def content_process_form(request, content_id):
    course = get_object_or_404(Course, pk=content_id)
    modules = Module.objects.filter(course_id=content_id)
    return render(request, 'courses/Course_module_list.html', {'course': course,
                                                               'modules': modules})


def display_content(request):
    # Fetch all the saved content from the database
    courses = Course.objects.all().order_by('-id')  # Newest first

    return render(request, 'courses/Show_courses_list.html', {'courses': courses})


def create_course_structure(request, course):
    file_path = os.path.join(settings.BASE_DIR, 'static/data/Basics.json')
    created_modules = []

    with open(file_path, 'r') as file:
        json_data = json.load(file)
    m = 0
    for module_data in json_data:
        module = Module.objects.create(number=module_data['number'], title=module_data['title'], course=course)
        # Collect the created module
        i = 0
        m += 1
        print('module: ', m)
        created_lessons = []
        for lesson_data in module_data['lessons']:
            if i != len(module_data['lessons']):

                i += 1
                print('lesson: ', i)
                lesson = Lesson.objects.create(module=module, number=lesson_data['number'], title=lesson_data['title'])
                created_tasks = []
                for task in lesson_data['tasks']:
                    task_description = task['description'] + task['example_code']
                    task_question, task_code = generate_lesson_content(task_description)
                    task = Task.objects.create(lesson=lesson, task_name=task['task_title'],
                                               description=task['description'], correct_code=task_code)
                    created_tasks.append([task.description, task.correct_code])
                    created_lessons.append([lesson_data['title'], [created_tasks]])
                    task.save()
                created_modules.append(created_lessons)
                lesson.save()
            else:

                module_descr = ''
                for item in created_modules[-1]:
                    module_descr.join(item[0])

                project_title = module.title + ' Module Project Assignment'
                lesson = Lesson.objects.create(module=module, number=lesson_data['number'], title=project_title)
                project_code, project_description = generate_project_content(module_descr)

                task = Task.objects.create(lesson=lesson, task_name=task['task_title'],
                                           description=project_description, correct_code=project_code)
                created_tasks.append([task.description, task.code, ])
                created_lessons.append(created_tasks)
                task.save()
                lesson.save()
                print(task)
                print(lesson)
        created_modules.append(created_lessons)
        module.save()
        return created_modules


def create_content(request):
    if request.method == 'POST':
        form = ContentForm(request.POST)
        if form.is_valid():
            new_course_name = form.cleaned_data['title']
            objective = form.cleaned_data['objective']
            description = form.cleaned_data['description']

            if not new_course_name:
                form.add_error(None, 'Failed to generate content.')
            else:
                new_course = Course.objects.create(title=new_course_name,
                                                   description=description,
                                                   objective=objective,
                                                   structure=[])

                new_course.structure = create_course_structure(request, new_course)
                new_course.save()
                return redirect('display_content')  # Redirect to a new URL
    else:
        form = ContentForm()
    return render(request, 'courses/Show_content_generation_form.html', {'form': form})
