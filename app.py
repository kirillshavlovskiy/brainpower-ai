from autogen.agentchat import GroupChat, AssistantAgent, UserProxyAgent, GroupChatManager, \
    ConversableAgent
from autogen.coding import CodeBlock, LocalCommandLineCodeExecutor
from autogen.oai.openai_utils import config_list_from_dotenv
from autogen.agentchat.contrib.capabilities.teachability import Teachability
from pathlib import Path
from dotenv import load_dotenv
import os
import ast

load_dotenv()
llm_config = {
    "cache_seed": 48,
    "config_list": [{
        "model": os.environ.get("OPENAI_MODEL_NAME", "llama3-70b-8192"),
        "api_key": os.environ["GROQ_API_KEY"],
        "base_url": os.environ.get("OPENAI_API_BASE", "https://api.groq.com/openai/v1")}
    ],
}


print(result)

work_dir = Path(".")
work_dir.mkdir(exist_ok=True)

executor = LocalCommandLineCodeExecutor(work_dir=work_dir)


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


# Please feel free to change it as you wish
config_list = config_list_from_dotenv(
    dotenv_file_path='.env',
    model_api_key_map={'gpt-3.5-turbo-16k': 'OPENAI_API_KEY'},
    filter_dict={
        "model": {
            "gpt-3.5-turbo-16k"
        }
    }
)

local_llm_config = {
    "cache_seed": 41,
    "temperature": 0.25,
    "config_list": config_list,
    "timeout": 100,
}

# local_llm_config = {
#     "config_list": [
#         {
#             "model": "NotRequired", # Loaded with LiteLLM command
#             "api_key": "NotRequired", # Not needed
#             "base_url": "http://0.0.0.0:4000"  # Your LiteLLM URL
#         }
#     ],
#     "cache_seed": None # Turns off caching, useful for testing different models
# }

teachability_planner = Teachability(
    verbosity=0,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
    reset_db=False,
    path_to_db_dir="./tmp/interactive/teachability_p_db",
    recall_threshold=1.5,  # Higher numbers allow more (but less relevant) memos to be recalled.
)
teachability_engineer = Teachability(
    verbosity=0,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
    reset_db=False,
    path_to_db_dir="./tmp/interactive/teachability_e_db",
    recall_threshold=1.5,  # Higher numbers allow more (but less relevant) memos to be recalled.
)
teachability_critic = Teachability(
    verbosity=0,  # 0 for basic info, 1 to add memory operations, 2 for analyzer messages, 3 for memo lists.
    reset_db=False,
    path_to_db_dir="./tmp/interactive/teachability_c_db",
    recall_threshold=1.5,  # Higher numbers allow more (but less relevant) memos to be recalled.
)

code_writer_system_message = """
You have been given coding capability to solve tasks using Python code.
In the following cases, suggest python code (in a python coding block) or shell script (in a sh coding block) for the user to execute.
    1. When you need to collect info, use the code to output the info you need, for example, browse or search the web, download/read a file, print the content of a webpage or a file, get the current date/time, check the operating system. After sufficient info is printed and the task is ready to be solved based on your language skill, you can solve the task by yourself.
    2. When you need to perform some task with code, use the code to perform the task and output the result. Finish the task smartly.
Solve the task step by step if you need to. If a plan is not provided, explain your plan first. Be clear which step uses code, and which step uses your language skill.
When using code, you must indicate the script type in the code block. The user cannot provide any other feedback or perform any other action beyond executing the code you suggest. The user can't modify your code. So do not suggest incomplete code which requires users to modify. Don't use a code block if it's not intended to be executed by the user.
If you want the user to save the code in a file before executing it, put # filename: <filename> inside the code block as the first line. Don't include multiple code blocks in one response. Do not ask users to copy and paste the result. Instead, use 'print' function for the output when relevant. Check the execution result returned by the user.
"""

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
even when everything is done. You save code you write into the streamlit_app.py and run streamlit in command line
"""

# agents configuration
engineer = ConversableAgent(
    name="Engineer",
    llm_config=local_llm_config,
    code_execution_config=False,  # Turn off code execution for this agent.
    max_consecutive_auto_reply=25,
    human_input_mode="NEVER",
    system_message=coding_bot_system_message,
    description="""I am **ONLY** allowed to speak **immediately** after `Planner` and `user_proxy`.
"""
)

planner = ConversableAgent(
    name="Planner",
    llm_config=local_llm_config,
    system_message="""You are a helpful AI assistant. You create tasks for programmer assistants using your 
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
    Never use the word  'TERMINATE' in any of your replies.""",

    description="""This is a planner agent that always runs first. This agent writes clear step-by-step plans 
    for programmer agents to use. it is **ONLY** allowed to speak **immediately** after `User` or `Critic` 
    or speak first."""
)

code_executor_agent = AssistantAgent(
    name="Executor",
    is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("FINISH"),
    system_message="""You **ONLY** allowed to:
    1. execute `streamlit run streamlit_script.py` command in `sh` once you execute code first time.
    2. make changes to the streamlit_script.py file's content. Its forbidden to create other files in root folder.
    3. Speak **immediately** after `Planner`, `Engineer` or `Executor`.
    You are a helpful AI agent setup to execute shell commands in command line (like streamlit run) or if code does not 
    contain streamlit components, to execute regular python code. 
    This type of agent never goes first and only after the `Engineer` agent. This agent only executes the code provided by the Engineer agent. 
    Save code into "streamlit_script.py". If code is for streamlit, after saving the code to streamlit_app.py 
    run it on local server using sh command. Never use the word  'TERMINATE' in any of your replies.""",
    llm_config=False,
    code_execution_config={
        "executor": executor,
    },
    human_input_mode="NEVER",
    description="""I am **ONLY** allowed to speak **immediately** after `Engineer` and `User`.
"""
)

critic = ConversableAgent(
    name="Critic",
    human_input_mode="NEVER",
    llm_config=local_llm_config,
    system_message="""You are a helpful AI optimizing and criticizing agent. This type of agent never goes first 
        and only first appears after the `Engineer` agent. This agent analyzes and optimizes the code provided by the Engineer
        agent. You are not allowed to use word TERMINATE""",
    description="""I am **ONLY** allowed to speak **immediately** after `Planner`, `Engineer` or `Executor`.
"""
)

user_proxy = UserProxyAgent(
    name="User",
    human_input_mode="ALWAYS",
    max_consecutive_auto_reply=100,
    is_termination_msg=lambda x: x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config={"work_dir": "../mylms", "use_docker": False},
    llm_config=local_llm_config,
    system_message='''Reply TERMINATE if the task has been solved at full satisfaction. Otherwise reply continue,\
    or the reason why the task is not solved yet. Save files as streamlit_script.py file always.'''
)

graph_dict = {}
graph_dict[user_proxy] = [engineer, planner]
graph_dict[planner] = [engineer]
graph_dict[engineer] = [code_executor_agent]
graph_dict[code_executor_agent] = [critic]
graph_dict[critic] = [planner, engineer, user_proxy]

agents = [user_proxy, engineer, planner, code_executor_agent, critic]

# create the groupchat
group_chat = GroupChat(agents=agents, messages=[], max_round=100, allowed_or_disallowed_speaker_transitions=graph_dict,
                       allow_repeat_speaker=None, speaker_transitions_type="allowed")

# create the manager
manager = GroupChatManager(
    groupchat=group_chat,
    llm_config=local_llm_config,
    is_termination_msg=lambda x: x.get("content", "") and x.get("content", "").rstrip().endswith("TERMINATE"),
    code_execution_config=False,
)

teachability_engineer.add_to_agent(engineer)
teachability_critic.add_to_agent(engineer)
teachability_planner.add_to_agent(engineer)

task = f"""
Create an app in Streamlit, which creates front-end based on this code: {retrieve_code()} Add interface to input 
formulas of 2d and 3d format, charting, scale and calculation parameters in toolbar (left side). Please make sure
interface supports whole diversity of all kinds of inputs of formula. Add hints on correct function format in the frontend. Save file to 
streamlit_script.py file always and run it using command streamlit run streamlit_script.py Add feature to rotate 3D  
object built in plotting area."""
termination_notice = (
    '\n\nDo not show appreciation in your responses, say only what is necessary. '
    'if "Thank you" or "You\'re welcome" are said in the conversation, then say TERMINATE '
    'to indicate the conversation is finished and this is your last message.'
)
task += termination_notice
# initiate the task
user_proxy.initiate_chat(
    manager,
    message=task,
    clear_history=True
)



