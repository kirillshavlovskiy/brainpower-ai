# To install required packages:
# pip install pyautogen==0.2.9 panel==1.3.8
import autogen
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

import os

# model = "microsoft/wizardlm-2-8x22b"
# model = "meta-llama/llama-3-8b-instruct"
# model = "mistralai/mixtral-8x7b-instruct"
# model = "mistralai/mixtral-8x22b-instruct"
# model = "gryphe/mythomax-l2-13b"
model = "nousresearch/nous-hermes-llama2-13b"

os.environ['OAI_CONFIG_LIST'] = """[{"model": "microsoft/wizardlm-2-8x22b",
"api_key": "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",
"base_url": "https://openrouter.ai/api/v1",
"max_tokens":100000},{"model": "meta-llama/llama-3-8b-instruct",
"api_key": "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",
"base_url": "https://openrouter.ai/api/v1",
"max_tokens":100000},{"model": "mistralai/mixtral-8x7b-instruct",
"api_key": "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",
"base_url": "https://openrouter.ai/api/v1",
"max_tokens":100000},{"model": "mmistralai/mixtral-8x22b-instruct",
"api_key": "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",
"base_url": "https://openrouter.ai/api/v1",
"max_tokens":100000},{"model": "nousresearch/nous-hermes-llama2-13b",
"api_key": "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",
"base_url": "https://openrouter.ai/api/v1",
"max_tokens":100000}]"""

work_dir = Path("./coding")
work_dir.mkdir(exist_ok=True)
executor = LocalCommandLineCodeExecutor(work_dir=work_dir)

code_writer_system_message = """
You are a coding bot. You solve tasks using your coding and language skills. You are able to work with files and directories.
You can retrieve existing code to continue work on it from following location: .coding/streamlit_app.py and in case of a non 
streamlit app from ./app_script.py. Additional files may be retrieved based on the imported modules and their paths. Save your work 
into same files. You can create additional files which may be executed by Executor if they are properly imported into main files 
Streamlit_app.py and app_script.py. If you create additional python files, make sure to create folder called "coding" and place 
files into this folder. You never never never delete files.
***ONLY*** if you are given a specific request to retrieve external documents or papers, write code to retrieve related papers from the arXiv API, 
print their title, authors, abstract, and link.
You write python/shell code to solve tasks. Wrap the code in a code block that specifies the script type. The user can't modify 
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
step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code,
and which step uses your language skill. When using code, you must indicate the script type in the 
code block. The user cannot provide any other feedback or perform any other action beyond executing
the code you suggest. The user can't modify your code. So do not suggest incomplete code which 
requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> 
inside the code block as the first line. Don't include multiple code blocks in one response. 
Do not ask users to copy and paste the result. Instead, use 'print' function for the output when
relevant. Check the execution result returned by the executor. If the result indicates there is an
error, fix the error and output the code again. Suggest the full code instead of partial code
or code changes. If the error can't be fixed or if the task is not solved even after the code
is executed successfully, analyze the problem, revisit your assumption, collect additional info
you need, and think of a different approach to try. When you find an answer, verify the answer
carefully. Include verifiable evidence in your response if possible. Don't make assumptions 
about what values to plug into functions. Check if code is returning non-None value. Otherwise
add print statement in the end to show calculations results. You never use word 'TERMINATE' in the end
even when everything is done. You save code you create into the ./coding/streamlit_app.py and run streamlit in 
command line in sh: `streamlit run ./coding/streamlit_app.py`. Before finishing your task make sure you saved 
code changes to ./coding/streamlit_app.py file. Report file update completion to the chat manager! 
Always save your changes to ./coding/app_script.py (if a non-streamlit app) or to ./coding/streamlit_app.py!
***example of the streamlit application or satisfactory level of elaboration:
# filename: streamlit_script.py
import streamlit as st
import matplotlib.pyplot as plt
import numpy as np
from sympy import symbols, lambdify
from sympy.parsing.sympy_parser import parse_expr
from mpl_toolkits.mplot3d import Axes3D

# Define the symbols used in the formula
x, y, z = symbols('x y z')

# Sidebar for input
st.sidebar.header("Input your formula and parameters")
formula_str = st.sidebar.text_area("Enter the formula (in terms of x, y, z):", value='x**2 + y**2')
min_range = st.sidebar.number_input("Enter the minimum value for x and y:", value=-10.0)
max_range = st.sidebar.number_input("Enter the maximum value for x and y:", value=10.0)
scale = st.sidebar.number_input("Enter the number of points to plot:", value=100, step=1, format='%d')

# Hints and examples
st.sidebar.info("Valid functions include operations and functions like +, -, *, /, sin, cos, exp, etc.")
st.sidebar.info("Example for 2D plot: x**2")
st.sidebar.info("Example for 3D plot: x**2 + y**2")

# Main area for plot and button
if st.button("Plot"):
    expr = parse_expr(formula_str)
    message = ""

    if expr.has(x, y, z):
        fig = plt.figure()
        ax = fig.add_subplot(111, projection='3d')
        x_vals = np.linspace(min_range, max_range, scale)
        y_vals = np.linspace(min_range, max_range, scale)
        x_vals, y_vals = np.meshgrid(x_vals, y_vals)
        z_vals = lambdify((x, y), expr, "numpy")
        ax.plot_surface(x_vals, y_vals, z_vals(x_vals, y_vals))
        ax.set_xlabel('x')
        ax.set_ylabel('y')
        ax.set_zlabel('z')
    elif expr.has(x, y):
        x_vals = np.linspace(min_range, max_range, scale)
        y_vals = lambdify(x, expr, "numpy")
        plt.plot(x_vals, y_vals(x_vals))
        plt.xlabel('x')
        plt.ylabel('y')
    elif expr.has(x):
        x_vals = np.linspace(min_range, max_range, scale)
        y_vals = lambdify(x, expr, "numpy")
        plt.plot(x_vals, y_vals(x_vals))
        plt.xlabel('x')
        plt.ylabel('y')
    else:
        message = "Invalid formula"
        st.error(message)

    if message == "":
        st.pyplot(fig)
***Other example***
import streamlit as st
from sympy import symbols, lambdify, sin, cos, sqrt, pi
from sympy.parsing.sympy_parser import parse_expr
import plotly.graph_objects as go
import numpy as np

# Sidebar for user inputs
st.sidebar.header("Chart Parameters")
formula = st.sidebar.text_input('Enter Formula:', 'sin(sqrt(x**2 + y**2))')
min_range = st.sidebar.number_input('Minimum Range:', value=-10.0)
max_range = st.sidebar.number_input('Maximum Range:', value=10.0)
points = st.sidebar.number_input('Number of Points:', value=100, min_value=10)
height = st.sidebar.number_input('Height:', value=600, min_value=100)
width = st.sidebar.number_input('Width:', value=600, min_value=100)

# Parse formula
x, y = symbols('x y')
expr = parse_expr(formula)
lambdified_expr = lambdify((x, y), expr, modules=['numpy'])

# Define x, y values
x_vals = np.linspace(min_range, max_range, points)
y_vals = np.linspace(min_range, max_range, points)
x_vals, y_vals = np.meshgrid(x_vals, y_vals)

# Evaluate z
z_vals = lambdified_expr(x_vals, y_vals)

# Create figure
fig = go.Figure(data=[go.Surface(z=z_vals, x=x_vals, y=y_vals)])

# Update layout
fig.update_layout(
    autosize=False,
    width=width,
    height=height,
    scene=dict(
        xaxis_title='X',
        yaxis_title='Y',
        zaxis_title='Z',
        aspectratio=dict(x=1, y=1, z=1),  #adjust aspect ratio if you want to "zoom"
    )
)

# Show figure
st.write(fig)
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

# gpt_config = {
#     "timeout": 600,
#     "cache_seed": 22,  # change the seed for different trials
#     "config_list": autogen.config_list_from_json(
#         "OAI_CONFIG_LIST",
#         filter_dict={"model": [model]},
#     ),
#     "temperature": 0.7,
# }


gpt_config = {
    "cache_seed": None,
    "temperature": 0,
    "config_list": config_list,
    "timeout": 100,
}

reset = False
teachability_planner = Teachability(
    verbosity=0,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
    reset_db=reset,
    path_to_db_dir="../tmp/interactive/teachability_p_db",
    recall_threshold=1.5,  # Higher numbers allow more (but less relevant) memos to be recalled.
)
teachability_engineer = Teachability(
    verbosity=0,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
    reset_db=reset,
    path_to_db_dir="../tmp/interactive/teachability_e_db",
    recall_threshold=0.5,  # Higher numbers allow more (but less relevant) memos to be recalled.
)
teachability_critic = Teachability(
    verbosity=0,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
    reset_db=reset,
    path_to_db_dir="../tmp/interactive/teachability_c_db",
    recall_threshold=0.25,  # Higher numbers allow more (but less relevant) memos to be recalled.
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
    system_message="""A human admin. Interact with the planner to discuss the plan. Plan execution needs to be approved by this admin. 

   """,
    # Only say APPROVED in most cases, and say exit when nothing to be done further. Do not say others.
    code_execution_config=False,
    # default_auto_reply="Approved",
    human_input_mode="ALWAYS",
    # llm_config=gpt4_config,
)

engineer = autogen.AssistantAgent(
    name="Engineer",
    human_input_mode="NEVER",
    llm_config=gpt_config,
    system_message='''Engineer. You follow an approved plan. You write python/shell code to solve tasks. Wrap the code in a code block that specifies the script type. The user can't modify your code. So do not suggest incomplete code which requires others to modify. Don't use a code block if it's not intended to be executed by the executor.
Don't include multiple code blocks in one response. Do not ask others to copy and paste the result. Check the execution result returned by the executor.
If the result indicates there is an error, fix the error and output the code again. Suggest the full code instead of partial code or code changes. If the error can't be fixed or if the task is not solved even after the code is executed successfully, analyze the problem, revisit your assumption, collect additional info you need, and think of a different approach to try.
''',
)
scientist = autogen.AssistantAgent(
    name="Scientist",
    human_input_mode="NEVER",
    llm_config=gpt_config,
    system_message="""Scientist. You follow an approved plan. You are able to categorize papers after seeing their abstracts printed. You don't write code."""
)
planner = autogen.AssistantAgent(
    name="Planner",
    human_input_mode="NEVER",
    system_message='''Planner. Suggest a plan. Revise the plan based on feedback from admin and critic, until admin approval.
The plan may involve an engineer who can write code and a scientist who doesn't write code.
Explain the plan first. Be clear which step is performed by an engineer, and which step is performed by a scientist.
''',
    llm_config=gpt_config,
)
executor = autogen.UserProxyAgent(
    name="Executor",
    system_message="Executor. Execute the code written by the engineer and report the result.",
    human_input_mode="NEVER",
    code_execution_config={"last_n_messages": 3, "work_dir": "paper", "use_docker": False},
)
critic = autogen.AssistantAgent(
    name="Critic",
    system_message="""Critic. Double check plan, claims, code from other agents and provide feedback. 
    Check whether the plan includes adding verifiable info such as source URL. 
    """,
    llm_config=gpt_config,
    human_input_mode="NEVER",
)

teachability_engineer.add_to_agent(planner)
teachability_critic.add_to_agent(engineer)
teachability_planner.add_to_agent(critic)

groupchat = autogen.GroupChat(agents=[user_proxy, engineer, scientist, planner, executor, critic], messages=[],
                              max_round=20)
manager = autogen.GroupChatManager(groupchat=groupchat, llm_config=gpt_config)

avatar = {user_proxy.name: "👨‍💼", engineer.name: "👩‍💻", scientist.name: "👩‍🔬", planner.name: "🗓",
          executor.name: "🛠", critic.name: '📝'}

# Existing imports...

ready_flag = False
content_holder = ''
update_event = asyncio.Event()  # Global event


def print_messages(recipient, messages, sender, config):
    global ready_flag
    global update_event
    global content_holder
    content = messages[-1]['content']
    print(f"Messages from: {sender.name} sent to: {recipient.name} | message: {content}")
    content_holder = content
    # Check if the current message is from the engineer assistant
    if sender.name != 'Admin':
        # Trigger the reload of input prompt after the engineer's reply is printed
        time.sleep(1)
        content_holder = content
        ready_flag = True
        update_event.set()
    return False, None

user_proxy.register_reply(
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
        asyncio.create_task(delayed_initiate_chat(user_proxy, manager, contents))

    else:
        if input_future and not input_future.done():
            input_future.set_result(contents)
        else:
            print("There is currently no input being awaited.")


# Run the main coroutine
print(gpt_config)
asyncio.run(callback('lets continue development of our battleship game'))

