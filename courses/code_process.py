import chromadb
from git import Repo, GitCommandError
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain.memory import ConversationSummaryMemory
from langchain.text_splitter import Language
from langchain_community.chat_message_histories import ChatMessageHistory, UpstashRedisChatMessageHistory
from langchain_community.document_loaders import RecursiveUrlLoader
from langchain_core.chat_history import BaseChatMessageHistory
from langchain.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage
from langchain_core.runnables import ConfigurableFieldSpec
from langchain_core.runnables.history import RunnableWithMessageHistory
from llama_index.core.embeddings import resolve_embed_model
from langchain_core.prompts import ChatPromptTemplate
from langchain_community import chat_models
from langchain_text_splitters import Language
# from llama_index.llms.groq import Groq
from langchain_groq import ChatGroq
from langchain_community.chat_models import ChatOpenAI
from langchain_community.vectorstores import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from bs4 import BeautifulSoup as Soup
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
import os
import pickle


llamaparse_api_key = os.getenv("LLAMA_CLOUD_API_KEY")
qdrant_url = os.getenv("QDRANT_URL")
qdrant_api_key = os.getenv("QDRANT_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")
data_file = "./data/repo/langchain/parsed_repo_data.pkl"
model_1 = "mixtral-8x7b-32768"
model_2 = "llama3-70b-8192"
model_3 = "llama3-8b-8192"
llm = ChatGroq(temperature=0, groq_api_key=groq_api_key, model_name=model_3)
url_upstash = os.getenv("UPSTASH_URL")
token_upstash = os.getenv("UPSTASH_TOKEN")
repo_langchain = "./data/repo/langchain"


store = {}
def get_session_history(user_id: str, conversation_id: str) -> UpstashRedisChatMessageHistory:
    if (user_id, conversation_id) not in store:
        store[(user_id, conversation_id)] = ChatMessageHistory()
    return store[(user_id, conversation_id)]

def code_search_process():
    # 1. LCEL docs
    url = "https://python.langchain.com/docs/expression_language/"
    loader_html = RecursiveUrlLoader(
        url=url, max_depth=20, extractor=lambda x: Soup(x, "html.parser").text,
    )
    docs = loader_html.load()

    # Sort the list based on the URLs and get the text
    d_sorted = sorted(docs, key=lambda x: x.metadata["source"])
    d_reversed = list(reversed(d_sorted))
    concatenated_content = "\n\n\n --- \n\n\n".join(
    [doc.page_content for doc in d_reversed])
    print(concatenated_content)
    # 2 Repo files
    if os.path.exists(data_file):
        print(" ----> opening code repo...")
        # Load the parsed data from the file
        with open(data_file, "rb") as f:
            documents = pickle.load(f)
    else:
        # Perform chain of the parsing steps and store the result in llama_parse_documents
        try:

            loader_repo = GenericLoader.from_filesystem(
                "./data/repo/langchain",
                glob="**/*",
                suffixes=[".py", "ipynb"],
                exclude=["**/non-utf8-encoding.py"],
                show_progress=True,
                parser=LanguageParser(language=Language.PYTHON, parser_threshold=500),
            )
            documents = loader_repo.load()

            with open(data_file, "wb") as f:
                pickle.dump(documents, f)
        except Exception as e:
            print("Unable to process load request...")
            documents = [""]
    context_data = concatenated_content + "\n\n\n --- \n\n\n".join(
    [doc.page_content for doc in documents])
    print(context_data)
    print("end of context")
    python_splitter = RecursiveCharacterTextSplitter.from_language(language=Language.PYTHON,
                                                                   chunk_size=2000,
                                                                   chunk_overlap=200)
    texts = python_splitter.split_documents(documents)
    ABS_PATH = os.path.dirname(os.path.abspath(__file__))
    # DB_DIR = os.path.join(ABS_PATH, "db/code")
    db_code = Chroma.from_documents(texts, OpenAIEmbeddings(disallowed_special=()))
    code_retriever = db_code.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 1},
    )

    print("check")
    prompt = ChatPromptTemplate.from_messages(
        [
            ("placeholder", "{chat_history}"),
            ("user", "{input}"),
            (
                "user",
                "Given the above conversation, generate a search query to look up to get information relevant to the conversation",
            ),
        ]
    )

    retriever_chain = create_history_aware_retriever(llm, code_retriever, prompt)
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Answer the user's questions based on the below context:\n\n{context}",
            ),
            ("placeholder", "{chat_history}"),
            ("user", "{input}"),
        ]
    )
    document_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever_chain, document_chain)
    conversational_rag_chain = RunnableWithMessageHistory(
        rag_chain,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
        history_factory_config=[
            ConfigurableFieldSpec(
                id="user_id",
                annotation=str,
                name="User ID",
                description="Unique identifier for the user.",
                default="",
                is_shared=True,
            ),
            ConfigurableFieldSpec(
                id="conversation_id",
                annotation=str,
                name="Conversation ID",
                description="Unique identifier for the conversation.",
                default="",
                is_shared=True,
            ),
        ],
    )

    return conversational_rag_chain, context_data


questions = [
    "how to add tool calling into langchain?",
    "Can you provide an example of how to add teachability to autogen agent",
    "Show me how to generate ReAct agent using llama_index library?",
    "Show me how to generate Group Chat with langchain based agents?",
]

chat_history = []
conversational_rag_chain, context_data = code_search_process()

while True:
    question = input("input your question: ")
    ai_msg = conversational_rag_chain.invoke(
        {"input": question},
        config={"configurable": {"conversation_id": "123", 'user_id': '123'}}
    )

    print(f"-> **Question**: {question} \n")
    print(f"**Answer**: {ai_msg['answer']} \n")
