import asyncio
from pprint import pprint

from langchain_community.chat_models import ChatOpenAI

from langchain_community.document_loaders.github import GithubFileLoader

from langchain_core.messages import AIMessage, SystemMessage

from langchain_pinecone import PineconeVectorStore

from typing import Literal, Dict, Any

from langchain_community.document_loaders.parsers import LanguageParser

from langchain_core.messages import HumanMessage
from langchain_core.output_parsers import JsonOutputParser, StrOutputParser

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate

from langchain_text_splitters import Language
from langchain_groq import ChatGroq
from langchain_community.embeddings.openai import OpenAIEmbeddings

from langchain.text_splitter import RecursiveCharacterTextSplitter

import os
from langchain_community.chat_message_histories.upstash_redis import UpstashRedisChatMessageHistory
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.vectorstores import FAISS
from langchain.memory import ConversationBufferMemory


llamaparse_api_key = os.getenv("LLAMA_CLOUD_API_KEY")
qdrant_url = os.getenv("QDRANT_URL")
qdrant_api_key = os.getenv("QDRANT_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")
url_upstash = os.getenv("UPSTASH_REDIS_REST_URL")
token_upstash = os.getenv("UPSTASH_REDIS_REST_TOKEN")
perplexity_api_key = os.getenv("PPLX_API_KEY")
anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
data_file = "./data/repo/langchain/parsed_repo_data.pkl"
model_1 = "mixtral-8x7b-32768"
model_2 = "llama-3.1-8b-instant"
model_3 = "llama-3.1-70b-versatile"
model_4 = "llama-3.1-405b-reasoning"
repo_langchain = "./data/repo/langchain"
repo_llama_index = "./data/repo/llama_index"
repo_autogen = "./data/repo/autogen"
repo_langserve = "./data/web_repo/langserve"
repo_langgraph = "./data/web_repo/langgraph"
repo_code = "/Users/kirillshavlovskiy/mylms/courses/data/repo/langchain/learning"
local_llm = "llama3"

model = ChatGroq()

store = {}

import re


def get_session_history(session_id: str) -> UpstashRedisChatMessageHistory:
    history = UpstashRedisChatMessageHistory(url=url_upstash, token=token_upstash, ttl=0, session_id=session_id)
    return history


def update_session_history(user_id: str, thread_id: str, user_message,
                           ai_message) -> UpstashRedisChatMessageHistory:
    session_id = f"{user_id}_{thread_id}"
    history = UpstashRedisChatMessageHistory(url=url_upstash, token=token_upstash, ttl=0, session_id=session_id)
    # Ensure user_message is a string
    if not isinstance(user_message, str):
        user_message = str(user_message)

    # Ensure ai_message is a string
    if not isinstance(ai_message, str):
        ai_message = str(ai_message)

    history.add_user_message(user_message)
    history.add_ai_message(ai_message)
    return history


urls_ = {
    'langchain': "https://python.langchain.com/docs/get_started/introduction/",
    'lcel': "https://python.langchain.com/v0.1/docs/expression_language/",
    'tool': "https://python.langchain.com/v0.1/docs/use_cases/tool_use/",
    'api': "https://python.langchain.com/v0.1/docs/use_cases/apis/",
    'langserve': "https://python.langchain.com/v0.1/docs/get_started/introduction/#-langserve",
    'stream': "https://python.langchain.com/v0.1/docs/expression_language/streaming/",
    'memory': "https://python.langchain.com/v0.1/docs/use_cases/question_answering/chat_history/",
    'history': "https://python.langchain.com/v0.1/docs/expression_language/how_to/message_history/",
    'langgraph': "https://python.langchain.com/v0.1/docs/get_started/introduction/#%EF%B8%8F-langgraph",
    'chatbot': "https://python.langchain.com/v0.2/docs/tutorials/chatbot/",
    'agents': "https://python.langchain.com/v0.1/docs/use_cases/tool_use/agents/",
    'rag': "https://python.langchain.com/v0.1/docs/use_cases/question_answering/quickstart/",
    "code": "https://python.langchain.com/v0.1/docs/use_cases/code_understanding/",
    'language_model': "https://python.langchain.com/v0.1/docs/modules/model_io/llms/quick_start/",
}

repos_ = {
    "self_reflection": "/Users/kirillshavlovskiy/mylms/courses/code_process_1.py",
    "langchain": "/Users/kirillshavlovskiy/mylms/courses/data/repo/langchain/libs/core/langchain_core",
    "lcel": "/Users/kirillshavlovskiy/mylms/courses/data/repo/langchain",
    "tool": "/Users/kirillshavlovskiy/mylms/courses/data/repo/langgraph/examples/chat_agent_executor_with_function_calling",
    "api": "/Users/kirillshavlovskiy/mylms/courses/data/repo/langserve/examples/api_handler_examples",
    "langserve": "/Users/kirillshavlovskiy/mylms/courses/data/repo/langserve/langserve",
    "stream": "/Users/kirillshavlovskiy/mylms/courses/data/repo/langserve/examples/agent_custom_streaming",
    "memory": "/Users/kirillshavlovskiy/mylms/courses/data/repo/langserve/examples/chat_with_persistence_and_user",
    "history": "/Users/kirillshavlovskiy/mylms/courses/data/repo/langserve/examples/agent_with_history",
    "langgraph": "/Users/kirillshavlovskiy/mylms/courses/data/repo/langgraph/langgraph",
    "chatbot": "/Users/kirillshavlovskiy/mylms/courses/data/repo/langgraph/examples/chatbots",
    "agents": "/Users/kirillshavlovskiy/mylms/courses/data/repo/langgraph/examples/agent_executor",
    "rag": "/Users/kirillshavlovskiy/mylms/courses/data/repo/langgraph/examples/rag",
    "code": "/Users/kirillshavlovskiy/mylms/courses/data/repo/langchain/learning",
}

all_topics = ["langserve", "langgraph", "rag", "api", "code", "memory", "history", "chatbot", "stream", "tool", "lcel",
              "agents", "langchain", "language model"]
topics = []
rag_retriever = None
conversational_rag_chain = None
agent_with_chat_history = None


def sanitize_filename(url):
    """Create a safe filename from a URL by removing unsafe characters."""
    return re.sub(r'[^\w\-_\. ]', '_', url)  # Replace disallowed chars with underscores


fast_llm = ChatOpenAI(model="gpt-3.5-turbo")
open_ai_llm = ChatOpenAI(model="gpt-4o-mini")
model = ChatGroq()

prompt_topic = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a professional classifier assessing the topic of a user question.\n 
        
        Here is the list of available topics to classify user question:\n
        {topics}\n
        \nIf the document contains keywords related to one of the topics in the list, select this topic name or multiple topics.
        \nIf NO relevant topic is found among topics form the list , return "general" value
        \nReturn the a JSON with a single key 'topic' , without other keys. Value to be as selected topic name or a list of topics and no preamble or explanation. 
        \n""",
    ),
    ("human", "{input}"),
])
# Retriever Grader
prompt_retriever = PromptTemplate(
    template="""You are a grader assessing relevance 
    of a retrieved document to a user question. If the document contains keywords related to the user question, 
    grade it as relevant. It does not need to be a stringent test. The goal is to filter out erroneous retrievals. \n
    Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question. \n
    Provide the binary score as a JSON with a single key 'score' and no preamble or explanation.

    Here is the retrieved document: \n\n {document} \n\n
    Here is the user question: {question} \n
    """,
    input_variables=["question", "document"],
)

# Hallucination Prompt
hallucination_prompt = PromptTemplate(
    template=""" You are a grader assessing whether 
    an answer is grounded in / supported by a set of facts. Give a binary 'yes' or 'no' score to indicate 
    whether the answer is grounded in / supported by a set of facts. Provide the binary score as a JSON with a 
    single key 'score' and no preamble or explanation. <|eot_id|><|start_header_id|>user<|end_header_id|>
    Here are the facts:
    \n ------- \n
    {documents} 
    \n ------- \n
    Here is the answer: {generation}""",
    input_variables=["generation", "documents"],
)

# Re-write Prompt
re_write_prompt = PromptTemplate(
    template="""You a question re-writer that converts an input question to a better version that is optimized \n 
     for vectorstore retrieval. Look at the initial and formulate an improved question. \n
     Here is the initial question: \n\n {question}. Improved question with no preamble: \n """,
    input_variables=["generation", "question"],
)
# Router Prompt
prompt_router = PromptTemplate(
    template="""You are designed to be an expert at routing a 
    user question to different nodes.  Give a choice: 'web_search', 'agent_reply', 'self_reflection', or 'vectorstore' based on the question. 
    You do not need to be stringent with the keywords in the question related to these topics. 
    Question to route: {question}.
    Always read latest messages from conversation history to properly address user query. 
    Return the a JSON with a single key 'datasource' and no preamble or explanation. 
    {chat_history}
    \n ------- \n
    Context to consider: 
    {context}
    It should be taking into consideration only if user is asking about this code, this or that program, or similar queries referring to this or that file or files.
    \n ------- \n
   
    Routing rules:
    \n ------- \n
    1. Use the 'vectorstore' for questions specifically on LLM agent, prompt or chatbot engineering only. If user is asking about general langchain related concepts and approaches, select 'vectorstore'.
    2. If user question is asking on how do you work, or how do you operate or what are you or who are you, then return 'self_reflection'. If 'code' answers the question then reply 'self_reflection'.
    3. If you are able to answer yourself  or based on the given 'context' only then answer 'agent_reply'. 
    4. Otherwise if you do not have information to address user query, reply: 'web_search'.
    """,
    input_variables=["question", "context", "chat_history"],
)


class Topic(BaseModel):
    topic: list = Field(description="list of strings representing topics")


# ------Agent Setup-------
agent_scratchpad = []  # Initialize with an empty list
chat_history = []
parser = JsonOutputParser(pydantic_object=Topic)

template = '''
You are a friendly assistant powered by Groq, Langchain and Langgraph frameworks, using llama3 open-source LLM.
You are evaluated based on how much information and how relevant information you provide
in your reply with no or minimal follow-up questions. Answer the following questions as best you
can providing maximum content. Always read the latest messages from conversation history to properly address user query.
You have optional access to the following tools:
{tools}
If the answer can be found in this chat history, reply directly without tool invocation. Always read
the latest messages from conversation history to properly address user query before tool invocation.
After tool invocation, please also rely on the answer based on tool invocation.
{chat_history}
You may be optionally given context documents to base your answer on.
If the answer can be found in this context, reply directly without tool invocation,
ground your answer based on the given context. Use the search tool if there is no context
or the given context is insufficient or incomplete.
If code is to be shared with the user, present it in the form of a snippet starting with """python
Use the following format:
Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question
Begin!
Question: {input}
Context: {context}
Thought:{agent_scratchpad}'''

prompt_react = PromptTemplate.from_template(template)

# Conversational Prompt
system_prompt = """You are a friendly assistant ready to answer question about the logic and your own working algorith"
            This is what you know about yourself:
            I am a React Agent powered by Groq, Langchain and Langgraph frameworks, using llama3 open-source LLM.
            I rely on chat history with you, my own searching tools, RAG interface to langchain knowledgebase, pretrained LLM knowledge 
            I am evaluated based on how much information and how relevant information you provide
            In addition to above knowledge you have access to the python code knowledge base, defining the logic of your work
            You should always access this  knowledge base using 'retriever_tool' from the list of the tools ['retriever_tool'].
            Always read latest messages from conversation history to properly address user query.
            """
self_reflecting_conversational_prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad")
])

# Define the prompt template for the agent
# asd = ChatPromptTemplate.from_messages([
#
#
#
#         (
#             "system",
#             "You are a helpful assistant with advanced long-term memory"
#             " capabilities. Powered by a stateless LLM, you must rely on"
#             " external memory to store information between conversations."
#             " Utilize the available memory tools to store and retrieve"
#             " important details that will help you better attend to the user's"
#             " needs and understand their context.\n\n"
#             "Memory Usage Guidelines:\n"
#             "0. ***IMPORTANT*** !!!Before giving any answer or deciding if/how to use tools, put user question in the ***context***"
#             "of most recent 'chat history' messages!!!"
#
#             "1. ALWAYS after checking user history decide on memory tools usage (store_core_memory, store_recall_memory) if you need more generic information about previous chat history"
#             " to build a comprehensive understanding of the user.\n"
#             "2. Make informed suppositions and extrapolations based on stored"
#             " memories.\n"
#             "3. Regularly reflect on past interactions to identify patterns and"
#             " preferences.\n"
#             "4. Update your mental model of the user with each new piece of"
#             " information.\n"
#             "5. Cross-reference new information with existing memories for"
#             " consistency.\n"
#             "6. Prioritize storing emotional context and personal values"
#             " alongside facts.\n"
#             "7. Use memory to anticipate needs and tailor responses to the"
#             " user's style.\n"
#             "8. Recognize and acknowledge context of the user's query or"
#             "conversation perspectives over time using also following code user providing as a context:\n{context}\n\n"
#             "9. Leverage memories to provide personalized examples and"
#             " analogies.\n"
#             "10. Recall past challenges or successes to inform current"
#             " problem-solving.\n\n"
#             "## Core Memories\n"
#             "Core memories are fundamental to understanding the user and are"
#             " always available:\n{core_memories}\n\n"
#             "## Recall Memories\n"
#             "Recall memories are contextually retrieved based on the current"
#             " conversation:\n{recall_memories}\n\n"
#             "## Instructions\n"
#             "Engage with the user naturally, as a trusted colleague or friend."
#             " There's no need to explicitly mention your memory capabilities."
#             " Instead, seamlessly incorporate your understanding of the user"
#             " into your responses. Be attentive to subtle cues and underlying"
#             " emotions. Adapt your communication style to match the user's"
#             " preferences and current emotional state. Use tools to persist"
#             " information you want to retain in the next conversation. If you"
#             " do call tools, all text preceding the tool call is an internal"
#             " message. Respond AFTER calling the tool, once you have"
#             " confirmation that the tool completed successfully.\n\n"
#             " before ending conversation always check if you need to store_recall_memory or store_core_memory"
#             "Current system time: {current_time}\n\n",
#         ),
#
#         (
#             "user",
#             [
#                 {
#                     "type": "image",
#                     "source": {
#                         "type": "base64",
#                         "media_type": "image/png",
#                         "data": "{image_data}",
#                     },
#                 },
#                 {
#                     "type": "text",
#                     "text": "This image supplements previous user message with code UI image context to make responses of the model more accurate and detailed",
#                 },
#             ],
#         ),
#     MessagesPlaceholder(variable_name="chat_history"),
#
#
#     ]
# )

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage

prompt_main = ChatPromptTemplate.from_messages([
    ("system",
     "You are a helpful assistant with advanced long-term memory"
     " capabilities. You are working over the user project. Powered by a stateless LLM, you must rely on"
     " external memory to store information between conversations."
     " Utilize the available memory tools to store and retrieve"
     " important details that will help you better attend to the user's"
     " needs and understand their context.\n\n"
     "Memory Usage Guidelines:\n"
     "0. ***IMPORTANT*** !!!Before giving any answer or deciding if/how to use tools, put user question in the ***context***"
     "of most recent 'chat history' messages!!!"
     "1. ALWAYS after checking user history provided before decide on memory tools usage (store_core_memory, store_recall_memory) if you need more generic historical information about previous chatting sessions"
     " to build a comprehensive understanding of the user work.\n"
     "2. Make informed suppositions and extrapolations based on stored"
     " memories.\n"
     "3. Regularly reflect on past interactions to identify patterns and"
     " preferences.\n"
     "4. Update your mental model of the user with each new piece of"
     " information.\n"
     "5. Cross-reference new information with existing memories for"
     " consistency.\n"
     "6. Prioritize storing emotional context and personal values"
     " alongside facts.\n"
     "7. Use memory to anticipate needs and tailor responses to the"
     " user's style.\n"
     "8. Recognize and acknowledge context of the user's query or"
     "conversation perspectives over time using also following code user providing as a context:\n{context}\n\n"
     "9. Leverage memories to provide personalized examples and"
     " analogies.\n"
     "10. Recall past challenges or successes to inform current"
     " problem-solving.\n\n"
     "## Core Memories\n"
     "Core memories are fundamental to understanding the user and are"
     " always available:\n{core_memories}\n\n"
     "## Recall Memories\n"
     "Recall memories are contextually retrieved based on the current"
     " conversation:\n{recall_memories}\n\n"
     "## Instructions\n"
     "Engage with the user naturally, as a trusted colleague or friend."
     " There's no need to explicitly mention your memory capabilities."
     " Instead, seamlessly incorporate your understanding of the user"
     " into your responses. Be attentive to subtle cues and underlying"
     " emotions. Adapt your communication style to match the user's"
     " preferences and current emotional state. Use tools to persist"
     " information you want to retain in the next conversation. If you"
     " do call tools, all text preceding the tool call is an internal"
     " message. Respond AFTER calling the tool, once you have"
     " confirmation that the tool completed successfully.\n\n"
     " before ending conversation always check if you need to store_recall_memory or store_core_memory"
     "Current system time: {current_time}\n\n"),

    ("user",
     [
         {
             "type": "image_url",
             "image_url": {"url": "{image_data}"},
         }
     ]),
    MessagesPlaceholder("chat_history"),
    ("user",
     [
         {
             "type": "text",
             "text": "{question}",
         }
     ]),

])

# -----------------------------------------Chain Section--------------------------------------------------


llm = ChatGroq(temperature=0, groq_api_key=groq_api_key, model_name=model_3)
structured_llm = llm.with_structured_output(method="json_mode")
retrieval_topic_chain = prompt_topic | structured_llm
gemma_llm = ChatGroq(temperature=0, groq_api_key=groq_api_key, model_name=model_1)
structured_gemma = gemma_llm.with_structured_output(method="json_mode")
retrieval_grader = prompt_retriever | llm | JsonOutputParser()
hallucination_grader = hallucination_prompt | gemma_llm | JsonOutputParser()
question_rewriter = re_write_prompt | llm | StrOutputParser()
# question_router = prompt_router | fast_llm | JsonOutputParser()

# ----------------------------------------- Agent Setup Section (Reply Chain) --------------------------------------------------

from langchain_core.tools import tool
from langchain_community.tools.tavily_search import TavilySearchResults
import tiktoken
import requests
import json
import logging
import uuid
from datetime import datetime, timezone, time
import langsmith
from langchain_core.runnables.config import (
    RunnableConfig,
    ensure_config,
    get_executor_for_config,
)
from langchain_core.messages.utils import get_buffer_string
from . import _utils as utils
from . import _constants as constants
from . import _settings as settings

from ._schemas import GraphState, GraphConfig
from typing import Optional, Tuple
from langgraph.prebuilt import ToolNode
from langchain_core.tools import Tool, StructuredTool

logger = logging.getLogger("memory")

_EMPTY_VEC = [0.0] * 768

# Initialize the search tool
search_tool = TavilySearchResults(max_results=1)
tools = [search_tool]


class InputSchema(BaseModel):
    query: str


import base64
import os

def perplexity_search(query: str) -> str:
    """Retrieve perplexity response on a query.

        Args:
            query (str): The query to be processed by perplexity.

        Returns:
            str: The Perplexity response.
    """
    API_KEY = perplexity_api_key
    URL = "https://api.perplexity.ai/chat/completions"
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama-3-70b-instruct",
        "messages": [
            {"role": "user", "content": query}
        ]
    }
    response = requests.post(URL, headers=headers, data=json.dumps(data))
    if response.status_code == 200:
        result = response.json()
        try:
            answer = result['choices'][0]['message']['content']
        except (KeyError, IndexError) as e:
            answer = f"Error accessing the reply message: {e}"
    else:
        answer = f"Error: {response.status_code}, {response.text}"
    return answer


def langchain_rag_retriever(query: str) -> str:
    """Retrieve relevant documents using rag-retriever funciton to address query on modern AI frameworks solutions and interfaces.
       Args:
           query (str): The query to be processed by perplexity.

       Returns:
           str: The Agent response.
       """
    global topics

    documents = []
    print(topics)
    if topics[0] != 'general':
        for topic in topics:
            print(topic)
            url = urls_[topic]
            print(url)
            # Define the file filter function to include only files in the "tests" folder that contain "test" in their names
            # file_filter = lambda file_path: topic in file_path
            file_filter = lambda file_path: "cookbook" in file_path and topic in file_path and file_path.endswith(
                ".ipynb")
            loader_langchain = GithubFileLoader(
                repo="langchain-ai/langchain",
                branch="master",
                access_token=os.environ["GITHUB_ACCESS_TOKEN"],
                file_filter=file_filter
            )
            repo_doc = loader_langchain.load()
            documents.extend(repo_doc)
            file_filter = lambda file_path: "examples" in file_path and topic in file_path and file_path.endswith(
                ".ipynb")
            loader_langgraph = GithubFileLoader(
                repo="langchain-ai/langgraph",
                branch="main",
                access_token=os.environ["GITHUB_ACCESS_TOKEN"],
                file_filter=file_filter
            )
            repo_doc = loader_langgraph.load()
            documents.extend(repo_doc)
        for doc in documents:
            print(f"Path: {doc.metadata['path']}")
            print(f"Content: {doc.page_content[:200]}...")  # Print the first 200 characters
            print("-" * 50)

        python_splitter = RecursiveCharacterTextSplitter.from_language(language=Language.PYTHON,
                                                                       chunk_size=1000,
                                                                       chunk_overlap=200)
        code_splits = None
        if documents:
            code_splits = python_splitter.split_documents(documents)

        # Index
        # embeddings = FireworksEmbeddings(model="nomic-ai/nomic-embed-text-v1.5")
        # Initialize embeddings
        embeddings = OpenAIEmbeddings(model="text-embedding-ada-002")

        index_name = "python-code-search"
        vectorstore = PineconeVectorStore.from_documents(code_splits, embeddings, index_name=index_name)

        docs = vectorstore.max_marginal_relevance_search(
            query,
            k=len(topics),
            fetch_k=len(topics) * 3,
            lambda_mult=0.5  # Adjust this value between 0 and 1
        )
        for doc in docs:
            print(f"Path: {doc.metadata['path']}")
            print(f"Content: {doc.page_content[:200]}...")  # Print the first 200 characters
            print("-" * 50)
        filtered_docs, agent_search = grade_docs(query, docs)
        if agent_search == "no":
            # generation = conversational_rag_chain.invoke({"input": query, "context": filtered_docs})
            return filtered_docs
        else:
            return 'There is no relevan document found, I will use perplexity search instead'
    else:
        return 'reply directly as there is no specific document which could be used to answer this question'


def self_retriever_host_or_ai(query: str) -> list:
    """Retrieve self-retriever response on a query. Suitable to answer user question on host processing logic AI
    framework or api implementation logic
            Args:
                query (str): The query to be processed by perplexity.

            Returns:
                str: The Agent response.
            """
    # Create Retriever Tool
    loader_server_app = GenericLoader.from_filesystem(
        "./courses/query_process.py",
        glob="**/*",
        suffixes=[".py"],
        exclude=["**/non-utf8-encoding.py"],
        show_progress=True,
        parser=LanguageParser(language=Language.PYTHON, parser_threshold=500),
    )

    docs = loader_server_app.load()
    print(docs)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=200,
        chunk_overlap=20
    )
    docsplits = splitter.split_documents(docs)
    embedding = OpenAIEmbeddings()
    index_name = "python-code-search"
    vectorstore = PineconeVectorStore.from_documents(docsplits, embedding, index_name=index_name)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
    generation = retriever.invoke(query)
    print(generation)
    return docs


def self_retriever_frontend(query: str) -> list:
    """Retrieve self-retriever response on a query. Suitable to answer user question on frontend/web or React/JS
    implementation logic of this react based platform

    Args:
        query (str): The query to be processed by perplexity.

    Returns:
        str: The Agent response.
    """
    # Create Retriever Tool
    filtered_docs = []
    file_filter = lambda file_path: file_path.endswith(".js")
    loader_client_app = GithubFileLoader(
        repo="kirillshavlovskiy/monaco-react",
        branch="master",
        access_token=os.environ["GITHUB_ACCESS_TOKEN"],
        file_filter=file_filter
    )

    docs = loader_client_app.load()
    print(docs)
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=2000,
        chunk_overlap=200
    )
    codesplits = splitter.split_documents(docs)
    embedding = OpenAIEmbeddings(model="text-embedding-ada-002")
    index_name = "js-code-search"
    vectorstore = PineconeVectorStore.from_documents(codesplits, embedding, index_name=index_name)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})
    generation = retriever.invoke(query)
    return generation


perplexity_tool = StructuredTool.from_function(
    name="perplexity_tool",
    func=perplexity_search,
    description="Useful for when you need to find an answer about any subject you don't know.",
    args_schema=InputSchema
)

langchain_retriever_tool = StructuredTool.from_function(
    name="langchain_retriever_tool",
    func=langchain_rag_retriever,
    description="Use this tool when searching for information about AI frameworks, inference models and other solutions.",
    args_schema=InputSchema
)

self_retriever_tool = StructuredTool.from_function(
    name="self_retriever_tool",
    func=self_retriever_host_or_ai,
    description="Retrieve self-retriever response on a query about host processing logic AI framework or API implementation logic",
    args_schema=InputSchema
)
frontend_retriever_tool = StructuredTool.from_function(
    name="frontend_retriever_tool",
    func=self_retriever_frontend,
    description="Use this tool when searching for information about yourself, your algorithm of processing user queries, approach of using memory and RAG tools.",
    args_schema=InputSchema
)

# Create Internal Buffer Knowledge Retriever Tool
loader_repo = GenericLoader.from_filesystem(
    "/Users/kirillshavlovskiy/mylms/courses/knowledge.py",
    glob="**/*",
    suffixes=[".py"],
    exclude=["**/non-utf8-encoding.py"],
    show_progress=True,
    parser=LanguageParser(language=Language.PYTHON, parser_threshold=500),
)

docs = loader_repo.load()
splitter = RecursiveCharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=20
)
splitDocs = splitter.split_documents(docs)
# embedding = OpenAIEmbeddings()
# vectorStore = FAISS.from_documents(splitDocs, embedding=embedding)
# knowledge_retriever = vectorStore.as_retriever(search_kwargs={"k": 1})

# knowledgeretrievertool = create_retriever_tool(
#     knowledge_retriever,
#     "Knowledge Retriever",
#     """Use this tool to understand on how to resolve user issue or query, based on your accumulated knowledge derived form the previous conversations with the user."""
# )

from langchain_anthropic import ChatAnthropic

chat_history = []

llm_llama = ChatGroq(temperature=0, groq_api_key=groq_api_key, model_name=model_4)
llm_claud = ChatAnthropic(
    model="claude-3-5-sonnet-20240620",  # or another available model
    temperature=0.1,
    max_tokens=8192,
    timeout=None,
    max_retries=2,
    streaming=True
)


# tools = [self_retriever_tool, ragretriever_tool, perplexity_tool]
# base_prompt = hub.pull("langchain-ai/react-agent-template")

# # Create Retriever Tool
# loader_repo = GenericLoader.from_filesystem(
#     "/Users/kirillshavlovskiy/mylms/courses/query_process.py",
#     glob="**/*",
#     suffixes=[".py"],
#     exclude=["**/non-utf8-encoding.py"],
#     show_progress=True,
#     parser=LanguageParser(language=Language.PYTHON, parser_threshold=500),
# )
#
# docs = loader_repo.load()
# splitter = RecursiveCharacterTextSplitter(
#     chunk_size=200,
#     chunk_overlap=20
# )
# docsplits = splitter.split_documents(docs)
#
# embedding = OpenAIEmbeddings()
# vectorStore = FAISS.from_documents(docsplits, embedding=embedding)
# retriever = vectorStore.as_retriever(search_kwargs={"k": 1})
#
# selfretriever_tool = create_retriever_tool(
#     retriever,
#     "Self_Reflection_Retriever",
#     "Use this tool when searching for information about yourself, your algorithm of processing user request, approach of using."
# )


# tools = [knowledgeretrievertool, selfretriever_tool, perplexity_tool]


# -----------------------------------------Helper Functions--------------------------------------------------


# def retrieve_topic(question):
#     global all_topics
#
#     retrieval_topic_chain = prompt_topic | structured_gemma
#     print(f"---> **Question**: {question}\n")
#     sys_msg = retrieval_topic_chain.invoke({"input": question,
#                                             "topics": all_topics,
#                                             })
#     print(sys_msg)
#     print(f"---> **Topic**: {sys_msg['topic']} \n")
#     if type(sys_msg["topic"]) == list:
#         sys_ref = sys_msg["topic"]
#     else:
#         sys_ref = [sys_msg["topic"]]
#     return sys_ref


def hallucination_status(docs, generation):
    # Prompt
    prompt = PromptTemplate(
        template="""You are a grader assessing whether 
        an answer is grounded in / supported by a set of facts. Give a binary 'yes' or 'no' score to indicate 
        whether the answer is grounded in / supported by a set of facts. Provide the binary score as a JSON with a 
        single key 'score' and no preamble or explanation.
        Here are the facts:
        \n ------- \n
        {documents} 
        \n ------- \n
        Here is the answer: 
        \n ------- \n
        {generation}""",
        input_variables=["generation", "documents"],
    )

    hallucination_grader = prompt | llm | JsonOutputParser()
    response = hallucination_grader.invoke({"documents": docs, "generation": generation})
    return response


def answer_grader(question, generation):
    prompt = PromptTemplate(
        template="""You are a grader assessing whether an answer is useful to resolve a question. 
        Give a binary score 'yes' or 'no' to indicate whether the answer is useful to resolve a question. 
        Provide the binary score as a JSON with a single key 'score' and no preamble or explanation.
        Here is the answer:
        \n ------- \n
        {generation} 
        \n ------- \n
        Here is the question: 
        \n ------- \n
        {question}""",
        input_variables=["generation", "question"],
    )

    answer_grader = prompt | llm | JsonOutputParser()
    answer_relevance = answer_grader.invoke({"question": question, "generation": generation})["score"]
    return answer_relevance


def grade_docs(question, docs):
    """
    Determines whether the retrieved documents are relevant to the question
    If any document is not relevant, we will set a flag to run web search

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Filtered out irrelevant documents and updated web_search state
    """

    print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    print(docs)
    # Score each doc
    filtered_docs = []
    agent_search = "yes"
    for d in docs:

        score = retrieval_grader.invoke(
            {"question": question, "document": d.page_content}
        )
        grade = score["score"]
        # Document relevant
        if grade.lower() == "yes":
            print("---GRADE: DOCUMENT RELEVANT---")
            filtered_docs.append(d)
            agent_search = "no"
            print(agent_search)
        # Document not relevant
        else:
            print("---GRADE: DOCUMENT NOT RELEVANT---")
            # We do not include the document in filtered_docs
            # We set a flag to indicate that we want to run web search
            print(agent_search)
            continue

    return filtered_docs, agent_search


@langsmith.traceable
def fetch_core_memories(user_id: str) -> Tuple[str, list[str]]:
    """Fetch core memories for a specific user.

    Args:
            user_id (str): The ID of the user.

    Returns:
        Tuple[str, list[str]]: The path and list of core memories.
    """
    path = constants.PATCH_PATH.format(user_id=user_id)
    response = utils.get_index().fetch(
        ids=[path], namespace=settings.SETTINGS.pinecone_namespace
    )
    memories = []
    if vectors := response.get("vectors"):
        document = vectors[path]
        payload = document["metadata"][constants.PAYLOAD_KEY]
        memories = json.loads(payload)["memories"]
    return path, memories


@tool
def search_memory(query: str, top_k: int = 5) -> list[str]:
    """Search for memories in the database based on semantic similarity.

    Args:
        query (str): The search query.
        top_k (int): The number of results to return.

    Returns:
        list[str]: A list of relevant recall memories.
    """
    config = ensure_config()
    configurable = utils.ensure_configurable(config)
    embeddings = utils.get_embeddings()
    vector = embeddings.embed_query(query)
    with langsmith.trace("query", inputs={"query": query, "top_k": top_k}) as rt:
        response = utils.get_index().query(
            vector=vector,
            filter={
                "user_id": {"$eq": configurable["user_id"]},
                constants.TYPE_KEY: {"$eq": "recall"},
            },
            namespace=settings.SETTINGS.pinecone_namespace,
            include_metadata=True,
            top_k=top_k,
        )
        rt.end(outputs={"response": response})
    memories = []
    if matches := response.get("matches"):
        memories = [m["metadata"][constants.PAYLOAD_KEY] for m in matches]
    return memories


@tool
def search_core_memory(query: str, top_k: int = 5) -> list[str]:
    """Search for memories in the database based on semantic similarity.

    Args:
        query (str): The search query.
        top_k (int): The number of results to return.

    Returns:
        list[str]: A list of relevant core memories.
    """
    config = ensure_config()
    configurable = utils.ensure_configurable(config)
    embeddings = utils.get_embeddings()
    vector = embeddings.embed_query(query)
    with langsmith.trace("query", inputs={"query": query, "top_k": top_k}) as rt:
        response = utils.get_index().query(
            vector=vector,
            filter={
                "user_id": {"$eq": configurable["user_id"]},
                constants.TYPE_KEY: {"$eq": "core"},
            },
            namespace=settings.SETTINGS.pinecone_namespace,
            include_metadata=True,
            top_k=top_k,
        )
        rt.end(outputs={"response": response})
    memories = []
    if matches := response.get("matches"):
        memories = [m["metadata"][constants.PAYLOAD_KEY] for m in matches]
    return memories


@tool
async def store_recall_memory(memory: str) -> str:
    """Save a memory to the database for later semantic retrieval.

    Args:
        memory (str): The memory to be saved.

    Returns:
        str: The saved memory.
    """
    config = ensure_config()
    configurable = utils.ensure_configurable(config)
    embeddings = utils.get_embeddings()
    vector = await embeddings.aembed_query(memory)
    current_time = datetime.now(tz=timezone.utc)
    path = constants.INSERT_PATH.format(
        user_id=configurable["user_id"],
        event_id=str(uuid.uuid4()),
    )
    documents = [
        {
            "id": path,
            "values": vector,
            "metadata": {
                constants.PAYLOAD_KEY: memory,
                constants.PATH_KEY: path,
                constants.TIMESTAMP_KEY: current_time,
                constants.TYPE_KEY: "recall",
                "user_id": configurable["user_id"],
            },
        }
    ]
    utils.get_index().upsert(
        vectors=documents,
        namespace=settings.SETTINGS.pinecone_namespace,
    )
    return memory


@tool
async def store_core_memory(memory: str, index: Optional[int] = None) -> str:
    """Store a core memory in the database. Whatever is important for as core knowledge about user and dialog with user
    Args:
        memory (str): The memory to store.
        index (Optional[int]): The index at which to store the memory.

    Returns:
        str: A confirmation message.
    """
    config = ensure_config()
    configurable = utils.ensure_configurable(config)
    embeddings = utils.get_embeddings()
    vector = await embeddings.aembed_query(memory)
    path, memories = fetch_core_memories(configurable["user_id"])
    if index is not None:
        if index < 0 or index >= len(memories):
            return "Error: Index out of bounds."
        memories[index] = memory
    else:
        memories.insert(0, memory)
    documents = [
        {
            "id": path,
            "values": vector,
            "metadata": {
                constants.PAYLOAD_KEY: json.dumps({"memories": memories}),
                constants.PATH_KEY: path,
                constants.TIMESTAMP_KEY: datetime.now(tz=timezone.utc),
                constants.TYPE_KEY: "core",
                "user_id": configurable["user_id"],
            },
        }
    ]
    utils.get_index().upsert(
        vectors=documents,
        namespace=settings.SETTINGS.pinecone_namespace,
    )
    return "Memory stored."


all_tools = [langchain_retriever_tool, self_retriever_tool, frontend_retriever_tool, perplexity_tool,
             store_recall_memory, search_memory, search_core_memory,
             store_core_memory]


# -----------------------------------------Nodes--------------------------------------------------


def load_memories(state: GraphState, config: RunnableConfig):
    """Load core and recall memories for the current conversation."""
    configurable = utils.ensure_configurable(config)
    user_id = configurable["user_id"]

    tokenizer = tiktoken.encoding_for_model("gpt-3.5-turbo")


    def convert_messages(messages):
        converted = []
        for message in messages:
            if isinstance(message, HumanMessage):
                converted.append(HumanMessage(content=message.content))
            elif isinstance(message, AIMessage):
                converted.append(AIMessage(content=message.content))
            elif isinstance(message, SystemMessage):
                converted.append(SystemMessage(content=message.content))
            else:
                # For any other type, we can use ChatMessage
                from langchain_core.messages import ChatMessage
                converted.append(ChatMessage(role=message.type, content=message.content))
        return converted

    converted_messages = convert_messages(state["messages"])
    convo_str = get_buffer_string(converted_messages)
    convo_str = tokenizer.decode(tokenizer.encode(convo_str)[:2048])
    with get_executor_for_config(config) as executor:
        futures = [
            executor.submit(fetch_core_memories, user_id),
            executor.submit(search_memory.invoke, convo_str),
        ]
        _, core_memories = futures[0].result()
        recall_memories = futures[1].result()
    return {
        "core_memories": core_memories,
        "recall_memories": recall_memories,
    }


def rag_call(state):
    question = state["messages"][0]['content']
    print(question)
    agent_search = "Yes"
    topics = retrieve_topic(question)

    if topics[0] != 'general':
        conversational_rag_chain, rag_retriever = code_search_process(topics)
        docs = rag_retriever.invoke(question)
        filtered_docs, agent_search = grade_docs(question, docs)

        if agent_search == "no":
            state['context'] = filtered_docs
            return 'agent_reply'
        else:
            return 'agent_search'


def generate(state):
    global tools
    global conversational_rag_chain
    """
    Generate answer using RAG on retrieved documents
    Args:
        state (dict): The current graph state
    Returns:
        state (dict): New key added to state, generation, that contains LLM generation
    """
    print("---GENERATE---")
    question = state["question"]
    documents = state["documents"]
    context = state["context"]
    agent_search = state["agent_search"]
    generation = state["generation"]
    # RAG/Other LLM generation

    return {"documents": documents, "question": question, "generation": generation['answer']}


def agent_search(state):
    """
    Web search based on the question
    Args:
        state (dict): The current graph state
    Returns:
        state (dict): Appended web results to generation
    """
    print("---AGENT SEARCH---")
    question = state["question"]
    documents = state["documents"]
    context = state["context"]
    # Web search

    import requests
    import json

    # Your Perplexity API key
    API_KEY = perplexity_api_key

    # API endpoint
    URL = "https://api.perplexity.ai/chat/completions"

    # Headers for the request
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }

    # The message you want to send
    message = question

    # The data payload for the request
    data = {
        "model": "llama-3-70b-instruct",  # or another model of your choice
        "messages": [
            {"role": "user", "content": message}
        ]
    }

    # Make the POST request to the API
    response = requests.post(URL, headers=headers, data=json.dumps(data))
    reply = {'answer': ''}
    # Check if the request was successful
    if response.status_code == 200:
        # Parse the JSON response
        result = response.json()

        # Access the reply message
        try:
            answer = result['choices'][0]['message']['content']
            reply['answer'] = answer
            print("Reply:", reply)
        except (KeyError, IndexError) as e:
            answer = f"Error accessing the reply message: {e}"
            reply['answer'] = answer
    else:
        print("Error:", response.status_code, response.text)
        reply['answer'] = response.text

    update_session_history('12345', '123454', question, reply)

    return {"documents": documents, "question": question, "generation": reply}


# def self_reflection(state):
#     """
#     Web search based based on the question
#     Args:
#         state (dict): The current graph state
#     Returns:
#         state (dict): Appended self reflection results to generation
#     """
#     print("---AGENT SELF REFLECTION---")
#     question = state["question"]
#
#     generation = self_reflecting_agent_with_chat_history.invoke({"input": question},
#                                                                 config={
#                                                                     "configurable": {"conversation_id": "12345",
#                                                                                      'user_id': '123454'}})
#     intermediate_steps = generation["intermediate_steps"]
#     for step in intermediate_steps:
#         action = step[0]  # AgentAction object
#         result = step[1]  # Result of the action
#         response = generation[
#                        "output"] + f"Action: {action.tool}" + f"Action Input: {action.tool_input}" + f"Result: {result}"
#
#     return {"question": question, "generation": generation}
from langchain_core.runnables.history import RunnableWithMessageHistory

async def agent(state: GraphState, config: RunnableConfig):
    # global all_tools
    """Process the current state and generate a response using the LLM.

    Args:
        state (schemas.State): The current state of the conversation.
        config (RunnableConfig): The runtime configuration for the agent.

    Returns:
        schemas.State: The updated state with the agent's response.
    """
    configurable = utils.ensure_configurable(config)
    user_id = configurable["user_id"]

    llm = llm_claud
    # llm = llm_llama
    # llm = open_ai_llm
    question = ""
    query = state["messages"][0]
    if isinstance(query, HumanMessage):
        question = query.content

    bound = prompt_main | llm

    agent_with_history = RunnableWithMessageHistory(
        bound,
        get_session_history,
        input_messages_key="question",
        history_messages_key="chat_history",
    )


    core_str = (
            "<core_memory>\n" + "\n".join(state["core_memories"]) + "\n</core_memory>"
    )
    recall_str = (
            "<recall_memory>\n" + "\n".join(state["recall_memories"]) + "\n</recall_memory>"
    )
    if state['user_id'] and state['thread_id']:
        session_id = state['user_id'] + '_' + state['thread_id']
    else:
        session_id = "0"

    prediction = await agent_with_history.ainvoke(
        {
            "question": question,
            "context": state['context'],
            "core_memories": core_str,
            "recall_memories": recall_str,
            "image_data": state['image_data'],
            "current_time": datetime.now(tz=timezone.utc).isoformat(),
        },
        config={"configurable": {"session_id": session_id}}
    )

    update_session_history(state['user_id'], state['thread_id'], question, prediction)
    logger.info("\nprediction\n",prediction)

    return {
        "messages": prediction,
    }


def agent_reply(state):
    """
    Agent REPLY
    Args:
        state (dict): The current graph state
    Returns:
        state (dict): Appended web results to documents
    """
    print("---AGENT REPLY---")
    question = state["question"]
    context = state["context"]
    documents = state["documents"]
    response = "---"
    # Agent Reply
    generation = conversational_agent_with_chat_history.invoke({"input": question, "context": context},
                                                               config={
                                                                   "configurable": {"conversation_id": "12345",
                                                                                    'user_id': '123454'}})

    print(generation['output'])
    intermediate_steps = generation["intermediate_steps"]
    print("-------------------------------")

    for step in intermediate_steps:
        action = step[0]  # AgentAction object
        result = step[1]  # Result of the action
        output = generation["output"]
        if output != "":
            generation = {"output": output}
        else:
            generation = {
                "output": f"Action: {action.tool}" + f"Action Input: {action.tool_input}" + f"Result: {result}"}
    return {"documents": documents, "question": question, "generation": generation}


# -----------------------------------------Conditional edge--------------------------------------------------


def route_tools(state: GraphState) -> Literal["tools", "__end__"]:
    """Determine whether to use tools or end the conversation based on the last message.

    Args:
        state (schemas.State): The current state of the conversation.

    Returns:
        Literal["tools", "__end__"]: The next step in the graph.
    """
    msg = state["messages"][-1]
    print(state["messages"][-1])
    if msg.tool_calls:
        return "tools"
    return END


# def route_question(state):
#     """
#     Route question to agent search or RAG.
#     Args:
#         state (dict): The current graph state
#     Returns:
#         str: Next node to call
#     """
#     print("---ROUTE QUESTION---")
#     question = state["messages"][0]["content"]
#     context = state["context"]
#     thread_id = state["thread_id"]
#     user_id = state["user_id"]
#     chat_history = get_session_history(user_id, thread_id)
#     source = question_router.invoke({"question": question, "context": context, "chat_history": chat_history})
#
#     if source["datasource"] == "web_search":
#         print("---ROUTE QUESTION TO WEB SEARCH---")
#         return "agent_reply"
#     elif source["datasource"] == "vectorstore":
#         print("---ROUTE QUESTION TO RAG---")
#         return "agent_reply"
#     elif source["datasource"] == "self_reflection":
#         print("---ROUTE QUESTION TO SELF REFLECTION---")
#         return "agent_reply"
#     else:
#         print("---ROUTE QUESTION TO AGENT REPLY---")
#         return "agent_reply"


def decide_to_generate(state):
    """
    Determines whether to generate an answer, or add web search
    Args:
        state (dict): The current graph state
    Returns:
        str: Binary decision for next node to call
    """
    print("---ASSESS GRADED DOCUMENTS---")
    agent_search = state["agent_search"]
    if agent_search == "yes":
        # All documents have been filtered check_relevance
        # We will re-generate a new query
        print(
            "---DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, INCLUDE AGENT SEARCH---"
        )
        return "agent_search"
    else:
        # We have relevant documents, so generate answer
        print("---DECISION: GENERATE---")

        return "generate"


def grade_generation_v_documents_and_question(state):
    """
    Determines whether the generation is grounded in the document and answers question.

    Args:
        state (dict): The current graph state

    Returns:
        str: Decision for next node to call
    """
    print("---CHECK HALLUCINATIONS---")
    question = state["question"]
    documents = state["documents"]
    generation = state["generation"]
    print("generation", generation)
    score = hallucination_grader.invoke(
        {"documents": documents, "generation": generation}
    )
    print(score)
    grade = score["score"]

    # Check hallucination
    if grade == "yes":
        print("---DECISION: GENERATION IS GROUNDED IN DOCUMENTS---")
        # Check question-answering
        print("---GRADE GENERATION vs QUESTION---")
        grade = answer_grader(question, generation)
        if grade == "yes":
            print("---DECISION: GENERATION ADDRESSES QUESTION---")
            answer = generation
            # update_session_history("123", "123", question, answer)
            return "useful"
        else:
            print("---DECISION: GENERATION DOES NOT ADDRESS QUESTION---")
            return "not useful"
    else:
        pprint("---DECISION: GENERATION IS NOT GROUNDED IN DOCUMENTS, RE-TRY---")
        return "not supported"


from langgraph.graph import END, StateGraph

workflow = StateGraph(GraphState, GraphConfig)

# Define the nodes
workflow.add_node("load_memories", load_memories)
# workflow.add_node("web_search", agent_search)  # web search
workflow.add_node("agent", agent)  # agent reply
# workflow.add_node("self_reflection", self_reflection)  # self reflection type search
# workflow.add_node("retrieve", rag_call)  # RAG
# workflow.add_node("generate", generate)  # generate RAG based response
workflow.add_node("tools", ToolNode(all_tools))
# -----------------------------------------Build graph--------------------------------------------------

workflow.set_entry_point("load_memories")

# workflow.add_conditional_edges(
#     "load_memories",
#     route_question,
#     {
#         "web_search": "web_search",
#         "agent_reply": "agent",
#         "self_reflection": "self_reflection",
#         "vectorstore": "retrieve",
#     },
# )
#

workflow.add_edge("load_memories", 'agent')
# workflow.add_edge("web_search", END)
workflow.add_conditional_edges("agent", route_tools)
# workflow.add_conditional_edges(
#     'agent',
#     route_tools,
#     {
#         "tools": "tools",
#     },
# )
workflow.add_edge("tools", "agent")
# workflow.add_edge("self_reflection", END)
# workflow.add_conditional_edges(
#     "generate",
#     grade_generation_v_documents_and_question,
#     {
#         "not supported": "web_search",
#         "useful": "agent",
#         "not useful": "web_search",
#     },
# )

# Compile

message_queue = asyncio.Queue()
import pprint

# -------------------------------------CHAT BOT------------------------------------------

import asyncio
from typing import Dict, Any
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging
from langchain.callbacks.base import BaseCallbackHandler

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()

class StreamingCallback(BaseCallbackHandler):
    def __init__(self, channel_name):
        self.channel_name = channel_name
        self.buffer = ""
        self.lock = asyncio.Lock()

    async def on_llm_new_token(self, token: str, **kwargs):
        async with self.lock:
            self.buffer += token
            if len(self.buffer) >= 10 or '\n' in self.buffer:  # Adjust buffer size as needed
                await self.flush()

    async def flush(self):
        if self.buffer:
            await channel_layer.send(
                self.channel_name,
                {
                    'type': 'chat_message',
                    'text': self.buffer,
                    'sender': "Coding Agent",
                }
            )
            logger.info(f"Sent buffer: {self.buffer}")
            self.buffer = ""

async def react_agent_queue(contents: Dict[str, Any], channel_name: str):
    global topics
    app = workflow.compile()
    thread_id = contents['thread_id']
    user_id = contents['user_id']
    logger.info(f"Starting streaming process for user: {user_id}, thread: {thread_id}")

    streaming_callback = StreamingCallback(channel_name)

    try:
        async for event in app.astream_events(
                input={
                    "messages": contents['messages'],
                    "context": contents['context'],
                    "image_data": contents['image_data'],
                    "user_id": user_id,
                    "session_ID": contents['session_id'],
                    "thread_id": thread_id,
                    "topics": topics
                },
                config={
                    "configurable": {
                        "user_id": user_id,
                        "thread_id": thread_id,
                        "lang_memgpt_url": "",
                        "delay": 4,
                    },
                    "callbacks": [streaming_callback],
                },
                version="v2"
        ):

            pass

    finally:
        # Ensure any remaining content in the buffer is sent
        await streaming_callback.flush()

    logger.info(f"Streaming process completed for user: {user_id}, thread: {thread_id}")

async def query(query_data, channel_name):
    thread_id = query_data['thread_id']
    try:
        await react_agent_queue(query_data, channel_name)
    except Exception as e:
        logger.error(f"Error in query processing: {str(e)}", exc_info=True)
        await channel_layer.send(
            channel_name,
            {
                'type': 'chat_message',
                'text': f"An error occurred while processing your request: {str(e)}",
                'sender': "System",
                'thread_id': thread_id
            }
        )
