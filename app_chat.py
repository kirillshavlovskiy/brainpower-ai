#!/usr/bin/env python3 -m pytest
import asyncio
import os
import sys
from autogen import ConversableAgent, UserProxyAgent, AssistantAgent, GroupChat, GroupChatManager, Agent, \
    config_list_from_json, config_list_from_dotenv
from autogen.agentchat.contrib.capabilities.teachability import Teachability
from autogen.formatting_utils import colored
from autogen.coding import CodeBlock, LocalCommandLineCodeExecutor
from pathlib import Path

sys.path.append(os.path.join(os.path.dirname(__file__), "../.."))

# Please feel free to change it as you wish
config_list = config_list_from_dotenv(
    dotenv_file_path='.env',
    model_api_key_map={'gpt-4-1106-preview': 'OPENAI_API_KEY'},
    filter_dict={
        "model": {
            "gpt-4-1106-preview"
        }
    }
)

gpt_config = {
    "cache_seed": None,
    "temperature": 0,
    "config_list": config_list,
    "timeout": 100,
}

# Specify the model to use. GPT-3.5 is less reliable than GPT-4 at learning from user input.
# filter_dict = {"model": ["gpt-4-0125-preview"]}
# filter_dict = {"model": ["gpt-3.5-turbo-1106"]}
# filter_dict = {"model": ["gpt-4-0613"]}
# filter_dict = {"model": ["gpt-3.5-turbo"]}
# filter_dict = {"model": ["gpt-4"]}
filter_dict = {"model": ["gpt-35-turbo-16k", "gpt-3.5-turbo-16k"]}

teachability = Teachability(
    verbosity=0,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
    reset_db=False,
    path_to_db_dir="./tmp/interactive/teachability_db",
    recall_threshold=1.5,  # Higher numbers allow more (but less relevant) memos to be recalled.

)
executor = AssistantAgent(
    name="Executor",
    is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("FINISH"),
    llm_config=gpt_config,
    description="""I am **ONLY** allowed to speak **immediately** after `Engineer`.
If the last number mentioned by `Engineer` is a multiple of 3, the next speaker can only be `Executor`.
"""
)

planner = AssistantAgent(
    name="planner",
    llm_config={"config_list": config_list},
    # the default system message of the AssistantAgent is overwritten here
    system_message="You are a helpful AI assistant. You suggest coding and reasoning steps for another AI \
        assistant to accomplish a task. Do not suggest concrete code. For any action beyond writing code or \
        reasoning, convert it to a step that can be implemented by writing code. For example, browsing the web \
        can be implemented by writing code that reads and prints the content of a web page. Finally, inspect the \
        execution result. If the plan is not good, suggest a better plan. If the execution is wrong, analyze the \
        error and suggest a fix.",
)

planner_user = UserProxyAgent(
    name="planner_user",
    max_consecutive_auto_reply=0,  # terminate without auto-reply
    human_input_mode="ALWAYS",
    code_execution_config={
        "use_docker": False
    },
    # Please set use_docker=True if docker is available to run the generated code. Using docker is safer than running the generated code directly.
)


def retrieve_code(path='app_script.py'):
    app_filepath = path

    try:
        # Write the new content to streamlit_app_script.py
        with open(app_filepath, 'r') as file:
            script = file.read()
        return script
    except Exception as e:
        print(f"Error reading file: {e}")
        return None

def create_optimizer_agent(reset_db=False):
    optimizer = ConversableAgent(
        name="planner",
        llm_config={"config_list": config_list},
        # the default system message of the AssistantAgent is overwritten here
        system_message="You are a helpful AI optimizing and criticizing agent. This type of agent never goes first and only after the `Engeneer` agent. This agent analyzes and optimizes\
                       the code provided by the engeneer agent",
        description = """I am **ONLY** allowed to speak **immediately** after `Engineer`."""
    )
    teachability.add_to_agent(optimizer)
    return optimizer


# create an AssistantAgent instance named "teachable_assistant"
def create_teachable_coding_bot(reset_db=False):
    # Load LLM inference endpoints from an env variable or a file
    # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    # Start by instantiating any agent that inherits from AssistantAgent.
    teachable_coding_bot = AssistantAgent(
        name="assistant",
        llm_config={
            "temperature": 0,
            "timeout": 600,
            "cache_seed": 42,
            "config_list": config_list,
            "functions": [
                {
                    "name": "ask_planner",
                    "description": "ask planner to: 1. get a plan for finishing a task, 2. verify the execution result of the plan and potentially suggest new plan.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "question to ask planner. Make sure the question include enough context, such as the code and the execution result. The planner does not know the conversation between you and the user, unless you share the conversation with the planner.",
                            },
                        },
                        "required": ["message"],
                    },
                },
                {
                    "name": "ask_optimizer",
                    "description": "ask optimizer to: 1. verify the code, 2. verify the execution result of the code and potentially suggest improvements to the code. Ask if code restructuring and strategy requires revisit.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message": {
                                "type": "string",
                                "description": "message for optimizer. Make sure the question includes enough context, such as the code and the execution result. The optimizer does not know the conversation between you and the user, unless you share the conversation with the optimizer.",
                            },
                        },
                        "required": ["message"],
                    },
                },
            ],
        },
        description="""I am **ONLY** allowed to speak **immediately** after `Planner`, `Critic` and `Executor`."""
    )
    teachability.add_to_agent(teachable_coding_bot)
    return teachable_coding_bot


def create_executor(reset_db=False):
    code_executor = AssistantAgent(
        name="Executor",
        is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("FINISH"),
        llm_config=gpt_config,
        description="""I am **ONLY** allowed to speak **immediately** after `Engineer`."""
    )
    return code_executor


work_dir = Path(".")
work_dir.mkdir(exist_ok=True)
executor = LocalCommandLineCodeExecutor(work_dir=work_dir)

coding_bot_system_message = """
You are a coding bot. You solve tasks using your coding and language skills. In the following
 cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to
execute. 1. When you need to collect info, use the code to output the info you need, for example, browse or
search the web, download/read a file, print the content of a webpage or a file, get the current date/time,
check the operating system. After sufficient info is printed and the task is ready to be solved based on
your language skill, you can solve the task by yourself. 2. When you need to perform some task with code,
use the code to perform the task and output the result. Finish the task smartly. Solve the task step by
step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code,
and which step uses your language skill. When using code, you must indicate the script type in the 
code block. The user cannot provide any other feedback or perform any other action beyond executing
the code you suggest. The user can't modify your code. So do not suggest incomplete code which 
requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> 
inside the code block as the first line. Don't include multiple code blocks in one response. 
Do not ask users to copy and paste the result. Instead, use 'print' function for the output when
relevant. Check the execution result returned by the user. If the result indicates there is an
error, fix the error and output the code again. Suggest the full code instead of partial code
or code changes. If the error can't be fixed or if the task is not solved even after the code
is executed successfully, analyze the problem, revisit your assumption, collect additional info
you need, and think of a different approach to try. When you find an answer, verify the answer
carefully. Include verifiable evidence in your response if possible. Don't make assumptions 
about what values to plug into functions. Check if code is returning non-None value. Otherwise
add print statement in the end to show calculations results. You never use word 'TERMINATE' in the end
even when everything is done. You save code you create into the streamlit_app.py and run streamlit in command line in sh:
`streamlit run streamlit_app.py`.
"""

def create_teachable_coding_agent(reset_db=False):
    teachability = Teachability(
        verbosity=0,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
        reset_db=False,
        path_to_db_dir="./tmp/interactive/teachability_basic_coding_db",
        recall_threshold=1.5,  # Higher numbers allow more (but less relevant) memos to be recalled.
    )
    """Instantiates a teachable agent using the settings from the top of this file."""
    # Load LLM inference endpoints from an env variable or a file
    # See https://microsoft.github.io/autogen/docs/FAQ#set-your-api-endpoints
    # Start by instantiating any agent that inherits from ConversableAgent.
    teachable_agent = ConversableAgent(
        name="teachable_agent",
        llm_config={"config_list": config_list, "timeout": 120, "cache_seed": None},  # Disable caching.
        code_execution_config={
            "executor": executor,
        },
        system_message=coding_bot_system_message,
    )
    teachability.add_to_agent(teachable_agent)
    return teachable_agent

input_future = None

def print_messages(recipient, messages, sender, config):
    print(f"Messages from: {sender.name} sent to: {recipient.name} | num messages: {len(messages)} | message: {messages[-1]}")
    content = messages[-1]['content']
    return False, None


class MyConversableAgent(ConversableAgent):

    async def a_get_human_input(self, prompt: str) -> str:
        global input_future
        print('AGET!!!!!!')  # or however you wish to display the prompt
        # Create a new Future object for this input operation if none exists
        if input_future is None or input_future.done():
            input_future = asyncio.Future()

        # Wait for the callback to set a result on the future
        await input_future

        # Once the result is set, extract the value and reset the future for the next input operation
        input_value = input_future.result()
        input_future = None
        return input_value


user_proxy = MyConversableAgent(
    name="Admin",
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("exit"),
    system_message="""A human admin. Interact with the planner to discuss the plan. Plan execution needs to be approved by this admin. 

   """,
    # Only say APPROVED in most cases, and say exit when nothing to be done further. Do not say others.
    code_execution_config=False,
    # default_auto_reply="Approved",
    human_input_mode="ALWAYS",
    # llm_config=gpt4_config,
)

engineer = AssistantAgent(
    name="Engineer",
    human_input_mode="NEVER",
    llm_config=gpt_config,
    system_message='''Engineer. You follow an approved plan. You write python/shell code to solve tasks. Wrap the code in a code block that specifies the script type. The user can't modify your code. So do not suggest incomplete code which requires others to modify. Don't use a code block if it's not intended to be executed by the executor.
Don't include multiple code blocks in one response. Do not ask others to copy and paste the result. Check the execution result returned by the executor.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
''',
)
teachability.add_to_agent(engineer)

user_proxy.register_reply(
    [Agent, None],
    reply_func=print_messages,
    config={"callback": None},
)

engineer.register_reply(
    [Agent, None],
    reply_func=print_messages,
    config={"callback": None},
)
initiate_chat_task_created = False


async def delayed_initiate_chat(agent, recipient, message):
    global initiate_chat_task_created
    # Indicate that the task has been created
    initiate_chat_task_created = True

    # Wait for 2 seconds
    await asyncio.sleep(2)

    # Now initiate the chat
    await agent.a_initiate_chat(recipient, message=message)


async def start_chat_with_agent(task):

    global initiate_chat_task_created
    global input_future

    if not initiate_chat_task_created:
        print('autogen chat started')
        asyncio.create_task(delayed_initiate_chat(user_proxy, engineer, 'hello!'))
    else:
        print('autogen chat continued')
        if input_future and not input_future.done():
            input_future.set_result(task)
        else:
            print("There is currently no input being awaited.")

