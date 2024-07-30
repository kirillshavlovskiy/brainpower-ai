import os
import time
import openai
import json
from openai import OpenAI

client = OpenAI(api_key=os.environ.get('OPENAI_API_KEY'))



def check_run(client, thread_id, run_id, max_retries):
    retry_count = 0
    while True:
        # Refresh the run object to get the latest status
        if retry_count > max_retries:
            print('Max retries exceeded. Exiting...')
            return "Error: Operation timed out"
        print('run is not completed :(')
        retry_count += 1
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
        if run.status == "completed":
            return "completed"
            break
        elif run.status == "expired":
            return "expired"
            break
        elif run.status == "requires_action":
            return "requires_action"
            break

        else:
            time.sleep(1)  # Wait for 1 second before checking again


# Waiting in a loop
def wait_on_run(run, thread_id):
    while run.status != "completed":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id,
        )
        print(run.status)
        if run.status == 'requires_action':
            print(run.required_action.submit_tool_outputs.model_dump())

        time.sleep(5)


def get_messages(thread_id):
    message_log = ""
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    i=0
    for each in list(reversed(messages.data)):
        i+=1
        message_log.join(f"===================message #{i}========================\n")
        #message_log.append([each.role, each.content[0].text.value])
        message_log.join(each.role + ": " + each.content[0].text.value + "\n")
        message_log.join("===========================================\n")
    #assistant_message = messages.data[0].content[0].text.value
    print(message_log)
    return message_log


def add_message(run_id, thread_id, message, function_call):
    if function_call:
        additional_promt = "Trigger function calling tool in the end"
    else:
        additional_promt = "Dont trigger function calling tool"
    thread_message = client.beta.threads.messages.create(
        thread_id,
        role="user",
        content=message + additional_promt,
    )
    messages = client.beta.threads.messages.list(thread_id=thread_id)
    assistant_message = messages.data[0].content[0].text.value
    return assistant_message


def retrieve_logs(run_steps):
    runstep_dict = {}
    for i, runstep in enumerate(list(reversed(run_steps.data))):  #step = run_steps
        for key, val in runstep:
            runstep_dict[key] = val
        # print(f"===========================####Run-step {i}####========================================\n", runstep)
        # print(runstep)
        tmp_list = list(runstep_dict["step_details"])
        if runstep_dict["type"] == "tool_calls":
            for detail in tmp_list[0][1]:
                tool_type = detail.type
                if tool_type == "code_interpreter":
                    #print("log:", detail.code_interpreter.outputs[0])
                    return detail.code_interpreter.outputs[0].logs

def run_loop(prompt, assistant_id, thread_id):
    # Convert prompt to string if it's a list
    if isinstance(prompt, list):
        prompt_str = ' '.join(prompt)
    else:
        prompt_str = str(prompt)
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
        instructions="try to keep code with clear remarks and make it as short as possible"
    )
    run_id = run.id
    response = []
    status = check_run(client, thread_id, run_id, 20)
    if status == "requires_action":
        run = client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run_id
        )
        required_actions = run.required_action.submit_tool_outputs.model_dump()
        completion, corrected_code, output, argument_dict = call_required_functions(required_actions, thread_id, run_id)

        response.append(completion)
        response.append(corrected_code)
        response.append(output)
        response.append(argument_dict)
        #message_log = get_messages(thread_id)
        #response.append(message_log)
        return response
    if status == "completed":
        #print('run is completed  :)')
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        assistant_message = messages.data[0].content[0].text.value
        response.append(assistant_message)
        return response


def call_required_functions(required_actions, thread_id, run_id):
    tool_outputs = []
    actions = [] # This initializes an empty dictionary.
    for action in required_actions["tool_calls"]:
        actions.append(action)
        arguments = json.loads(action['function']['arguments'])
        # If arguments is a dictionary:
        print(arguments)
        completion = arguments['completion']
        corrected_code = arguments['code']
        output = arguments['output']
        print(action["id"])
        tool_outputs.append({'tool_call_id': action["id"], 'output': "{success: True}"})
    run = client.beta.threads.runs.submit_tool_outputs(
        thread_id=thread_id,
        run_id=run_id,
        tool_outputs=tool_outputs
    )
    #wait_on_run(run, thread_id)
    run_steps = client.beta.threads.runs.steps.list(
        thread_id=thread_id,
        run_id=run_id
    )
    output = retrieve_logs(run_steps)
    return completion, corrected_code, output, actions



def coding_assisstant_create(instructions):
    model = "gpt-3.5-turbo"
    assistant = client.beta.assistants.create(
        name="Coding_Bot",
        instructions=instructions,
        model=model,
        tools=[{
            "type": "function",
            "function": {
                "name": "analyse_and_correct_the_code",
                "description": "Analyze given code, run it through Code interpreter, correct the code if code \
                execution through interpreter returns error or no output. You should return always all 3 parameters: \
                completion, code and output",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "completion": {
                            "type": "boolean",
                            "description": "completion status, `true` value should be returned here if code \
                            can be executed with some output result, also if input is required from the user, \
                            `false` value should be returned if interpreter raises error in the end of code \
                            completion"
                        },
                        "code": {
                            "type": "string",
                            "description": "suggested corrected code, run through interpreter, which does not \
                            raise any interpreter error. Return result `0` if code cannot be corrected and \
                            additonal guidance is required from the user. check if code contains output \
                            statement.If not then add print or image generation  commang accrodingly"
                        },
                        "output": {
                            "type": "string",
                            "description": "show here provided code execution result (use interpreter if nedeed)"
                        }
                    },
                    "required": ["completion", "code", "output"],
                },

            },
        },
            {
                "type": "function",
                "function": {
                    "name": "write_the_code",
                    "description": "Write a code according to given instructions. Return output result based on the interpreter response. You should always return all 3 parameters: completion, code and output",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "completion": {
                            "type": "boolean",
                            "description": "completion status, `true` value should be returned here successfully generated and checked code"
                        },
                            "code": {
                                "type": "string",
                                "description": "suggested corrected code, run through interpreter, which does not raise any interpreter error. Should return `None`, if completion value is defined as true. Return result `0` if code cannot be corrected and additonal guidance is required from the user"
                            },
                            "output": {
                                "type": "string",
                                "description": "show here provided code execution result (use interpreter if nedeed)"
                            },
                            "graphic_output_code": {
                                "type": "string",
                                "description": "Write a code to convert graphichal output of the program execution. In your function that generates the plot, you should save the figure to a bytes object instead of displaying it (use interpreter if needed): example \
                                                import base64 \
                                                define function to generate chart\n\
                                                Create a BytesIO object and save the plot to it\n\
                                                Get the base64 encoding of the bytes object and decode \
                                                it to string: image_base64 = base64.b64encode(buf.getvalue()).\
                                                decode(`utf-8`), buf.close()\n\
                                                print(image_base64)"
                            }

                        },
                        "required": ["completion", "code", "output", "graphic_output_code"],
                    },

                },
        },
            {"type": "code_interpreter"}]
    )
    return assistant


def testing_bot_calling(prompt):
    messages = [{"role": "user",
                 "content": prompt}]
    assistant_instructions = "You are a Python testing bot interacting through function calling. Use the provided functions to \
        test and correct the code. Don't make assumptions about what values to plug into functions. Check if code is returning \
        non-None value. otherwise add print statement in the end to show calculational results."
    assistant = coding_assisstant_create(assistant_instructions)
    assistant_id = assistant.id
    thread = client.beta.threads.create(
        messages=messages,
    )
    thread_id = thread.id
    ai_response = run_loop(prompt, assistant_id, thread_id)
    print(ai_response)
    return (ai_response)


def coding_bot_calling(prompt):
    messages = [{"role": "user",
                 "content": prompt}]
    assistant_instructions = "You are a Python coding bot interacting through function calling. Use the provided functions to \
    return the correct code. Don't make assumptions about what values to plug into functions. Ask for additional clarification if a \
    user request is ambiguous. If you dont understand what is the purpose of the code run, raise questions about general purpose \
    of th exercise. Always try to run functions first instead of regular message reply! In your last message show result of running \
    the code through interpreter."
    assistant = coding_assisstant_create(assistant_instructions)
    assistant_id = assistant.id
    thread = client.beta.threads.create(
        messages=messages,
    )
    thread_id = thread.id
    ai_response = run_loop(prompt, assistant_id, thread_id)
    print(ai_response)
    return(ai_response)


def assistant_preprocess_task(code, output, thread_id, task_description):
    print('check if assistant started')
    try:
        prompt_1 = 'There is a task: ' + str(task_description)
        prompt_2 = "In following code please check every line and validate execution response. Advise if code does not correspond to the task: \
                         \n" + code + '\nExecution response:\n' + str(output) + '\nShow corrected code in the end, but only if \
                         corrected code really change the result of code execution. Return message <<Code is ok!>> if code correctly address the task.'
        request = f"{prompt_1}{prompt_2}"
        assistant_id = 'asst_Kx2zKp0x0r3fLA6ZFiIGVsPZ'
        ai_response = run_loop(request, assistant_id, thread_id)

        return ai_response, assistant_id, thread_id
    except Exception as e:
        print(f"Error generating content: {e}")
        return None


def assistant_thread_run(code, thread_id, output=None):
    print(code, thread_id)
    try:
        prompt = "In following code please check every line and validate execution response. Advise code corrections if any issue is detected: \
                 \n" + code + '\nExecution response:\n' + str(
            output) + '\nShow improved code even if it shows same result as ' + str(output) + '.'
        assistant_id = 'asst_Kx2zKp0x0r3fLA6ZFiIGVsPZ'
        ai_response = run_loop(prompt, assistant_id, thread_id)

        return ai_response, assistant_id, thread_id
    except Exception as e:
        print(f"Error generating content: {e}")
        return None


def generate_description(prompt):
    generic_prompt_1 = "Please generate learning program description, for the course objective:"
    generic_prompt_2 = ". Limit answer to maximum 500 symbols"
    request = f"{generic_prompt_1} {prompt} {generic_prompt_2} "
    try:
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "user",
                    "content": request,
                },
            ],
        )
        content = completion.choices[0].message.content
        return content
    except Exception as e:
        print(f"Error generating content: {e}")
        return None


def generate_structure(description, i, n):
    generic_prompt_1 = "For the following learning course: "
    generic_prompt_2 = "generate maximum 100 word description of the lesson number"
    generic_prompt_3 = "out of "
    try:
        request = f"{generic_prompt_1} {description} {generic_prompt_2} {i} {generic_prompt_3} {n}"
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "assistant",
                    "content": request,
                },
            ],
        )
        response_text = response.choices[0].message.content.strip()
        return response_text
    except Exception as e:
        print(f"Error generating content for: {e}")
        return None


def generate_lesson_title(lesson):
    generic_prompt = "Please generate lesson title for the following lesson description:"
    request = f"{generic_prompt} {lesson}"
    try:
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "assistant",
                    "content": request,
                },
            ],
        )

        title = response.choices[0].message.content
        print("title:", title)
        return title
    except Exception as e:
        print(f"Error generating content: {e}")
        return None


def generate_project_content(desc):
    generic_prompt_1 = "Please generate Project Task example of correct code snippet with #comments for the topics listed\n"
    generic_prompt_2 = "Please formulate Project assignment based on the solution code for it:\n"
    request_1 = f"{generic_prompt_1} {desc}"

    try:
        response_1 = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "assistant",
                    "content": request_1,
                },
            ],
        )
        request_2 = f"{generic_prompt_2} {response_1}"
        response_2 = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "assistant",
                    "content": request_2,
                },
            ],
        )
        project_solution = response_1.choices[0].message.content
        project_question = response_2.choices[0].message.content
        # Splitting the response into parts based on newline
        # task_lines = response_text.splitlines()

        return project_solution, project_question
    except Exception as e:
        print(f"Error generating content: {e}")
        return None


def generate_lesson_content(title):
    generic_prompt_1 = "Please generate example of correct code snippet with #comments for the topic description below\n"
    generic_prompt_2 = "Please formulate exercise question based on the solution code for it:\n"
    request_1 = f"{generic_prompt_1} {title}"

    try:
        response_1 = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "assistant",
                    "content": request_1,
                },
            ],
        )
        request_2 = f"{generic_prompt_2} {response_1}"
        response_2 = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "assistant",
                    "content": request_2,
                },
            ],
        )
        task_solution = response_1.choices[0].message.content
        task_question = response_2.choices[0].message.content
        # Splitting the response into parts based on newline
        # task_lines = response_text.splitlines()

        return task_question, task_solution
    except Exception as e:
        print(f"Error generating content: {e}")
        return None


def re_generate_content(prompt):
    try:
        completion = openai.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )
        content = completion.choices[0].message.content
        return content
    except Exception as e:
        print(f"Error generating content: {e}")
        return None
