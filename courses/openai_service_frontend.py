import os
import time
import openai
import json
from openai import OpenAI
from . import openai_service
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


def retrieve_logs(run_steps):
    runstep_dict = {}
    for i, runstep in enumerate(list(reversed(run_steps.data))):  #step = run_steps
        for key, val in runstep:
            runstep_dict[key] = val
        print(f"===========================####Run-step {i}####========================================\n", runstep)
        print(runstep)
        tmp_list = list(runstep_dict["step_details"])
        if runstep_dict["type"] == "tool_calls":
            for detail in tmp_list[0][1]:
                tool_type = detail.type
                if tool_type == "code_interpreter":
                    #print("log:", detail.code_interpreter.outputs[0])
                    return detail.code_interpreter.outputs[0].logs


def testing_assisstant_create(instructions):
    model = "gpt-4-turbo-preview"
    assistant = client.beta.assistants.create(
        name="Testing_Bot",
        instructions=instructions,
        model=model,
        tools=[{
            "type": "function",
            "function": {
                "name": "test and correct_the_code",
                "description": "Analyze given code, run it through Code interpreter, correct the code if code \
                    execution through interpreter returns error or no output. You should return always all 3 parameters: \
                    completion, code and output!!! This is important!!! make sure code is following below pattern fpr streamlit:\n\
                               >>> fig, ax = plt.subplots()\n\
                                            >>> ax.scatter([1, 2, 3], [1, 2, 3])\n\
                                            >>>    ... other plotting actions ...\n\
                                            >>> st.pyplot(fig))",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "completion": {
                            "type": "boolean",
                            "description": "test completion status, `true` value should be returned here if code \
                                is tested with positive output, not raising any error and correspond to the initial requirements\
                                `false` value should be returned if interpreter raises error during testing"
                        },
                        "code": {
                            "type": "string",
                            "description": "check if code requires corrections, if so make code fixes and run it through\
                             interpreter, which does not raise any interpreter error. Return here fixed code or result `0` \
                             if code cannot be corrected and additional guidance is required from the user. Check if code contains \
                             output statement. If not then add print or image generation  command accordingly."
                        },
                        "output": {
                            "type": "string",
                            "description": "show here provided code execution result (use interpreter if needed)"
                        }
                    },
                    "required": ["completion", "code", "output"],
                },

            },
        },

            {"type": "code_interpreter"}]
    )
    return assistant


def interface_assisstant_create(instructions):
    model = "gpt-3.5-turbo"
    assistant = client.beta.assistants.create(
        name="Coding_Bot",
        instructions=instructions,
        model=model,
        tools=[{
                "type": "function",
                "function": {
                    "name": "write_and_check_the_streamlit_code",
                    "description": "Write a Streamlit code  according to given instructions without usage of base64 image and with no saving it in the buffer. \
                    Return output result based on the interpreter response. You should always return all 3 parameters: completion, code and output",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "completion": {
                            "type": "boolean",
                            "description": "completion status, `true` value should be returned here successfully generated and checked code, which does not raise any error in interpreter and does not return None",
                        },
                            "code": {
                                "type": "string",
                                "description": "Write a Steamlit code without(!) image_base64 saving and retrieval. Suggested code in a streamlit framework should follow this core logic if required:\n\
                                            >>> fig, ax = plt.subplots()\n\
                                            >>> ax.scatter([1, 2, 3], [1, 2, 3])\n\
                                            >>>    ... other plotting actions ...\n\
                                            >>> st.pyplot(fig))\n\
                                            Then run the code through interpreter - it should not raise any interpreter error. Return result `0` if code cannot be written and \
                                            additonal guidance is required from the user"
                            },
                            "output": {
                                "type": "string",
                                "description": "show here provided code execution result (use interpreter if needed)"
                            },
                        },
                        "required": ["completion", "code", "output"],
                    },

                },
        },
            {"type": "code_interpreter"}]
    )
    return assistant


def testing_agent_calling(request, response):
    messages = [{"role": "user",
                 "content": f"originally interface coding bot got a request to build Streamlit interface based on a given prompt request {request} and returned following response code:{response}\
    Response contains following arguments: completion status, script code for Streamlit app, output from the openAI interpreter (if any). Correct the code if:\n\
    1. you find code problems\n\
    2. code inconsistent with initial request\n\
    3. no output or output is not consistent with front end visual communication requirements (no output text or controls shown)\n\
    4. there is vulnerability oin the code if input parameters will change from given examples"}]
    print(messages)
    assistant_instructions = "You are a Python testing assistant. You are critical for any given code and responsible for quality of \
             released front-end functionality. You need to test interface built on Streamlit framework based on a given back-end code execution \
             requirements and already prepared code which defines and executes Streamlit functions. Carefully make every unit test\
             of the code and return corrected code which does not raise any error in interpreter"
    assistant = testing_assisstant_create(assistant_instructions)
    assistant_id = assistant.id
    thread = client.beta.threads.create(
        messages=messages,
    )
    thread_id = thread.id
    ai_response = run_loop(request, assistant_id, thread_id)
    print(ai_response)
    return (ai_response)


def interface_bot_calling(prompt):
    messages = [{"role": "user",
                 "content": prompt}]
    assistant_instructions = "You are a Python coding bot responsible for interface building based on the already prepared\
    backend code which executes function or functions based on input parameters. Your code should strictly stick to these parameters and each parameter should \
    be connected to the frontend field, while function execution should be connected to controls and buttons in the fron-end. When you create interface\
    you interacting through function calling.  Use the provided functions to return the correct interface streamlit code. Always try to run functions first\
    instead of regular message reply!"
    assistant = interface_assisstant_create(assistant_instructions)
    assistant_id = assistant.id
    thread = client.beta.threads.create(
        messages=messages,
    )
    thread_id = thread.id
    ai_response = run_loop(prompt, assistant_id, thread_id)
    return(ai_response)


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
        print("responses from interface bot", completion, corrected_code, output)
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
        print("interface bot message upon completion", assistant_message)
        return response


def call_required_functions(required_actions, thread_id, run_id):
    tool_outputs = []
    argument_dict = {} # This initializes an empty dictionary.

    for action in required_actions["tool_calls"]:
        print("interface action", action)
        arguments = json.loads(action['function']['arguments'])
        print("interface action", arguments)
        # If arguments is a dictionary:
        for key, val in arguments.items():
            argument_dict[key] = val
            print("---------------------")
            print(f'{key}:\n{val}')
            print("---------------------")
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
    return completion, corrected_code, output, argument_dict

