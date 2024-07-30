# To install required packages:
# pip install pyautogen==0.2.9 panel==1.3.8
import autogen
import logging
import json

logger = logging.getLogger(__name__)
from queue import Queue
import aioconsole
import panel as pn
import openai
import os
import time
import asyncio
from pathlib import Path
import asyncio
from autogen import config_list_from_dotenv
from autogen.coding import LocalCommandLineCodeExecutor
from autogen.agentchat.contrib.capabilities.teachability import Teachability
from channels.layers import get_channel_layer
import asyncio

import os
model = "microsoft/wizardlm-2-8x22b"
#model = "meta-llama/llama-3-8b-instruct"
#model = "meta-llama/llama-3-70b-instruct"
#model = "meta-llama/codellama-34b-instruct"
#model = "mistralai/mixtral-8x7b-instruct"
#model = "mistralai/mixtral-8x22b-instruct"
#model = "mistralai/mistral-7b-instruct:free"
#model = "gryphe/mythomax-l2-13b"
#model = "nousresearch/nous-hermes-llama2-13b"


os.environ['OAI_CONFIG_LIST'] = """[
{"model": "microsoft/wizardlm-2-8x22b",
"api_key": "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",
"base_url": "https://openrouter.ai/api/v1","max_tokens":10000000},
{"model": "meta-llama/llama-3-8b-instruct",
"api_key": "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",
"base_url": "https://openrouter.ai/api/v1","max_tokens":10000000},
{"model": "meta-llama/llama-3-70b-instruct",
"api_key": "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",
"base_url": "https://openrouter.ai/api/v1","max_tokens":10000000},
{"model": "meta-llama/codellama-34b-instruct",
"api_key": "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",
"base_url": "https://openrouter.ai/api/v1","max_tokens":10000000},
{"model": "mistralai/mistral-7b-instruct:free",
"api_key": "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",
"base_url": "https://openrouter.ai/api/v1","max_tokens":10000000},
{"model": "mistralai/mixtral-8x7b-instruct",
"api_key": "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",
"base_url": "https://openrouter.ai/api/v1","max_tokens":10000000},
{"model": "mistralai/mixtral-8x22b-instruct",
"api_key": "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",
"base_url": "https://openrouter.ai/api/v1","max_tokens":10000000},
{"model": "gryphe/mythomax-l2-13b",
"api_key": "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",
"base_url": "https://openrouter.ai/api/v1","max_tokens":10000000},
{"model": "nousresearch/nous-hermes-llama2-13b",
"api_key": "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",
"base_url": "https://openrouter.ai/api/v1","max_tokens":10000000}
]"""


work_dir = Path("./coding")
work_dir.mkdir(exist_ok=True)
executor = LocalCommandLineCodeExecutor(work_dir=work_dir)

manager_system_message = """As a manger you do not execute or write a code, you steer the development process and 
    conversation with Admin. Before proceeding with development loop, which starts from the planner, make sure that
    you got a definite completion coding task, which can be resolved during application or code development process 
    or research process.
    ***IMPORTANT*** If message dedicated to Admin you send this message immediately to Admin for answering! dont 
    resend this message to any other agent in the group!
    ***IMPORTANT*** If reply from any agent is dedicated to Admin then you send queue to admin to answer 
    *** IMPORTANT*** If you did not get any development or completion task which requires involvement of other agents, *** ALWAYS*** 
    return queue to Admin always!.
    *** IMPORTANT*** If you did receive definite clear development task then you manage speaker transition and also manage response to/from 
    Admin to confirm continuation. If task is unclear dont proceed with development process, dont pass message to Planner. Respond to Admin, 
    and request additional information of the development process. 
    If engineer prepared the code, please instruct Executor to run it using one of the tools: 
    local interpreter or shell. Make sure changes are saved in the streamlit_app.py file before calling Executor. 
    ***YOU NEVER CALL MEMORIES***
    ***IMPORTANT*** If reply form any agent is dedicated to Admin then you send queue to admin to answer this question.
    """
code_writer_system_message = """
You are a coding bot. You solve tasks using your coding and language skills. You are able to work with files and directories.
You can retrieve existing code to continue work on it from following location: .coding/streamlit_app.py and in case of a non 
streamlit app from ./app_script.py. Additional files may be retrieved based on the imported modules and their paths. Save your work 
into same files. You can create additional files which may be executed by Executor if they are properly imported into main files 
Streamlit_app.py and app_script.py. If you create additional python files, make sure to create folder called "coding" and place 
files into this folder. You never never never delete files.
***ONLY*** if you are given a specific request to retrieve external documents or papers, write code to retrieve related papers from the arXiv API, 
print their title, authors, abstract, and link.
You write python/shell code to solve tasks. Wrap the code in a code block that specifies the script type. fir exmample:
```python
print("hello world!")
```
Always wrap single code block based on this example. better send separate code blocks in separate messages if possible.
The user can't modify 
your code. So do not suggest incomplete code which requires others to modify. Don't use a code block if it's not intended to be 
executed by the executor.
Don't include multiple code blocks in one response. Do not ask others to copy and paste the result. Check the execution result 
returned by the executor.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code 
or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze 
the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) 
for the user to execute. 
1. When you need to collect info, use the code to output the info you need, for example, browse or
search the web, download/read a file, print the content of a webpage or a file, get the current date/time,
check the operating system. After sufficient info is printed and the task is ready to be solved based on
your language skill, you can solve the task by yourself. 
2. When you need to perform some task with code,
use the code to perform the task and output the result. Finish the task smartly. Solve the task step by
step if you need to. Be clear which step uses code, and which step uses your language skill. When using 
code, you must indicate the script type in the code block. 
The user cannot provide any other feedback or perform any other action beyond executing
the code you suggest. The user can't modify your code. So do not suggest incomplete code which 
requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> 
    inside the code block as the first line. Don't include multiple code blocks in one response. 
    Do not ask users to copy and paste the result. Instead, use 'print' function for the output when
    relevant. Check the execution result returned by the executor or Admin. If the result indicates there is an
error, fix the error and output the code again. Suggest the full code instead of partial code
or code changes. If the error can't be fixed or if the task is not solved even after the code
is executed successfully, analyze the problem, revisit your assumption, collect additional info
you need, and think of a different approach to try. When you find an answer, verify the answer
carefully. Include verifiable evidence in your response if possible. Don't make assumptions 
about what values to plug into functions. Check if code is returning non-None value. Otherwise
add print statement in the end to show calculations results. You never use word 'TERMINATE' in the end
even when everything is done. You save code you create into the ./coding/streamlit_app.py and run streamlit in 
command line in sh: `streamlit run ./coding/streamlit_app.py`. Send code
"""
planner_system_message = """You are a helpful AI assistant. You create tasks for programmer assistants using your 
language skills. Your role is to create step-by-step plans for programmer agents and to verify if the plan 
is followed by the agents. Do not write the code yourself
Take the input from the user and create 3 different plans.
Choose the best plan and only send that one to the programmer agent
You have to be crystal clear when explaining which plan is the best.
Solve the task step-by-step if you need to
If a plan is not provided, explain your plan first
Be clear about which step uses code, and which step uses your language skill. 
When you find an answer, verify the answer carefully
Always follow this process and only this process:
Step 1. Take the input from 'user_proxy' and use 3 different plans to solve the main task
Step 2. Analyze each plan in terms of its complexity and suitability.
Step 3. Choose the optimal variant: the most suitable but not the most complex scenario for realization. 
Only this scenario you send to the programmer agent makes it clear which plan we use to follow.
Never use the word  'TERMINATE' in any of your replies.
"""
critic_system_message = """Critic. You are a helpful assistant highly skilled in evaluating the quality of a given visualization code by providing a score from 1 (bad) - 10 (good) while providing clear rationale. YOU MUST CONSIDER VISUALIZATION BEST PRACTICES for each evaluation. Specifically, you can carefully evaluate the code across the following dimensions
- bugs (bugs):  are there bugs, logic errors, syntax error or typos? Are there any reasons why the code may fail to compile? How should it be fixed? If ANY bug exists, the bug score MUST be less than 5.
- Data transformation (transformation): Is the data transformed appropriately for the visualization type? E.g., is the dataset appropriated filtered, aggregated, or grouped  if needed? If a date field is used, is the date field first converted to a date object etc?
- Goal compliance (compliance): how well the code meets the specified visualization goals?
- Visualization type (type): CONSIDERING BEST PRACTICES, is the visualization type appropriate for the data and intent? Is there a visualization type that would be more effective in conveying insights? If a different visualization type is more appropriate, the score MUST BE LESS THAN 5.
- Data encoding (encoding): Is the data encoded appropriately for the visualization type?
- aesthetics (aesthetics): Are the aesthetics of the visualization appropriate for the visualization type and the data?

YOU MUST PROVIDE A SCORE for each of the above dimensions.
{bugs: 0, transformation: 0, compliance: 0, type: 0, encoding: 0, aesthetics: 0}
Do not suggest code.
Finally, based on the critique above, suggest a concrete list of actions that the coder should take to improve the code.
"""
code_writer_system_message_short = """
You have been given coding capability to solve tasks using Python code.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
"""


config_list = config_list_from_dotenv(
    dotenv_file_path='./.env',
    model_api_key_map={'gpt-3.5-turbo': 'OPENAI_API_KEY'},
    filter_dict={
        "model": {
            "gpt-3.5-turbo"
        }
    }
)

gpt_config = {
    "timeout": 600,
    "cache_seed": None,  # change the seed for different trials
    "config_list": autogen.config_list_from_json(
        "OAI_CONFIG_LIST",
        filter_dict={"model": [model]},
    ),
    "temperature": 0.01,
}

llm_config = {
    "cache_seed": 48,
    "config_list": [{
        "model": os.environ.get("OPENAI_MODEL_NAME", "llama3-70b-8192"),
        "api_key": os.environ["GROQ_API_KEY"],
        "base_url": os.environ.get("OPENAI_API_BASE", "https://api.groq.com/openai/v1")}
    ],
}

print(gpt_config)
# gpt_config = {
#     "cache_seed": None,
#     "temperature": 0,
#     "config_list": config_list,
#     "timeout": 100,
# }

reset = False
teachability_planner = Teachability(
    verbosity=0,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
    reset_db=reset,
    path_to_db_dir="../tmp/interactive/teachability_p_db",
    recall_threshold=1,  # Higher numbers allow more (but less relevant) memos to be recalled.
)
teachability_engineer = Teachability(
    verbosity=0,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
    reset_db=reset,
    path_to_db_dir="../tmp/interactive/teachability_e_db",
    recall_threshold=1,  # Higher numbers allow more (but less relevant) memos to be recalled.
)
teachability_critic = Teachability(
    verbosity=0,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
    reset_db=reset,
    path_to_db_dir="../tmp/interactive/teachability_c_db",
    recall_threshold=1,  # Higher numbers allow more (but less relevant) memos to be recalled.
)

input_future = None
done = [False]


class MyConversableAgent(autogen.ConversableAgent):
    async def a_get_human_input(self, prompt: str) -> str:
        global input_future, done
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
    system_message="""A human admin""",
    max_consecutive_auto_reply=10,
    # Only say APPROVED in most cases, and say exit when nothing to be done further. Do not say others.
    code_execution_config=False,
    default_auto_reply="",

    human_input_mode="ALWAYS",
)

group_manager = autogen.AssistantAgent(
    name="Manager",
    human_input_mode="ALWAYS",
    llm_config=gpt_config,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    system_message="""You are an agent administrating the group chat and you always run first after the Admin message input. 
    Be polite and responsive to Admin, if general conversation is ongoing.
    Interact with the planner to discuss the plan or with Admin, if any input is requested from the Admin by other agents. 
    Also can support general conversation with Admin, if no explicit task is communicated to this Manager. Dont forward message
    to any other agent if Admin does not request to develop or create. Answer TERMINATE if:
    1. tasks are executed
    2. queries are completed
    3. Result is delivered to the Admin and it confirms it is satisfactory.
    """,
    description="""I am **ONLY** allowed to speak **immediately** after `Admin`, `Planner`, `Engineer`, `Executor` or `Critic`. 
    I always go first after Admin first request, or later if communication with Agent is requested.
    Call me to request information form the Admin or send the reply to Admin if needed.
    """
)

engineer = autogen.ConversableAgent(
    name="Coder",
    human_input_mode="NEVER",
    llm_config=llm_config,
    system_message=code_writer_system_message,
    # description="""This agent always goes either after Admin or after Critic agent. Call this agent
    # to write a code or run the shell command. Engineer agent is able to retrieve external data through APIs. All the
    # materials and papers can be retrieved by Engineer form the internet, For example you can call for arxiv documents papers
    # retrieval.
    # """
)
scientist = autogen.AssistantAgent(
    name="Scientist",
    human_input_mode="NEVER",
    llm_config=gpt_config,
    system_message="""Scientist. You follow an approved plan. You are able to categorize papers after seeing their abstracts printed. You don't write code."""
)
planner = autogen.ConversableAgent(
    name="Planner",
    human_input_mode="ALWAYS",
    llm_config=gpt_config,
    system_message=planner_system_message,
    description="""This is a planner agent that always runs second after the Manager. Second time this agent may be called only by Admin.
     This agent writes clear step-by-step plans for programmer agents to use. If there is no need to create new app or program, then 
     you call for plan retrieval from the .coding/plan.txt file. And planning step may be skipped. It is **ONLY** allowed to speak **immediately** after `Admin`.
     """

)
executor = autogen.UserProxyAgent(
    name="Executor",
    system_message="""Executor. Execute the code written by the engineer and report the result. You always try to execute code using 2 methods:
   1. available Python interpreter interface
   2. available shell or command line interface
   report result of both running exercises.
    """,
    code_execution_config={
        "executor": executor,
    },
)
critic = autogen.ConversableAgent(
    name="Critic",
    system_message=critic_system_message,
    llm_config=llm_config,
)

teachability_engineer.add_to_agent(engineer)
teachability_critic.add_to_agent(critic)
teachability_planner.add_to_agent(planner)

graph_dict = {
    user_proxy: [engineer],
    #group_manager: [user_proxy],
    #planner: [engineer, group_manager],
    engineer: [critic],
    #executor: [user_proxy],
    critic: [engineer, user_proxy],
}

agents = [engineer, critic, user_proxy]

group_chat = autogen.GroupChat(agents=agents,
                               messages=[],
                               max_round=100,
                               speaker_selection_method="auto",
                               allowed_or_disallowed_speaker_transitions=graph_dict,
                               allow_repeat_speaker=None,
                               speaker_transitions_type="allowed",
                               send_introductions=True,
                               enable_clear_history=True,
                               )

manager = autogen.GroupChatManager(
    groupchat=group_chat,
    llm_config=llm_config,
    is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
    #system_message=manager_system_message
)

avatar = {user_proxy.name: "👨‍💼", engineer.name: "👩‍💻", scientist.name: "👩‍🔬", planner.name: "🗓",
          executor.name: "🛠", critic.name: '📝'}

# Existing imports...

ready_flag = False
content_holder = ''
update_event = asyncio.Event()  # Global event
# Globally accessible queue
message_queue = asyncio.Queue()


async def print_messages(recipient, messages, sender, config):
    global ready_flag
    global update_event
    global content_holder
    global message_queue
    message_content = {"sender": sender.name, "content": messages[-1]['content']}
    chat_content = {}
    logger.info(f"Queue size before adding a message: {message_queue.qsize()}")
    await message_queue.put(message_content)  # Enqueue the message
    logger.info(f"Queue size after adding a message: {message_queue.qsize()}")

    # Check if the current message is from the engineer assistant
    if recipient.name == 'Admin':
        # Trigger the reload of input prompt after the engineer's reply is printed
        await asyncio.sleep(1)
        ready_flag = True
    return False, None

user_proxy.register_reply(
    [autogen.Agent, None],
    reply_func=print_messages,
    config={"callback": None},
)

group_manager.register_reply(
    [autogen.Agent, None],
    reply_func=print_messages,
    config={"callback": None},
)

engineer.register_reply(
    [autogen.Agent, None],
    reply_func=print_messages,
    config={"callback": None},
)
scientist.register_reply(
    [autogen.Agent, None],
    reply_func=print_messages,
    config={"callback": None},
)
planner.register_reply(
    [autogen.Agent, None],
    reply_func=print_messages,
    config={"callback": None},
)

executor.register_reply(
    [autogen.Agent, None],
    reply_func=print_messages,
    config={"callback": None},
)
critic.register_reply(
    [autogen.Agent, None],
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


async def callback(contents: str):
    global initiate_chat_task_created
    global input_future
    if not initiate_chat_task_created:
        asyncio.create_task(delayed_initiate_chat(user_proxy, engineer, contents))
    else:
        if input_future and not input_future.done():
            input_future.set_result(contents)

        else:
            print("There is currently no input being awaited.")


async def get_summary():
    summary = await user_proxy.chat_messages[manager]
    return summary




# Run the main coroutine
#print(gpt_config)
#asyncio.run(callback('lets continue development of our battleship game'))

