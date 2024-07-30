from langchain_community.document_loaders import UnstructuredFileLoader
from langchain_community.document_loaders import DirectoryLoader
from langchain.document_loaders.generic import GenericLoader
from llama_parse import LlamaParse
from PyPDF2 import PdfReader
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.embeddings.fastembed import FastEmbedEmbeddings
from llama_index.core.embeddings import resolve_embed_model
from langchain_community.document_loaders.parsers import GrobidParser
from langchain_groq import ChatGroq
import os

llamaparse_api_key = os.getenv("LLAMA_CLOUD_API_KEY")
qdrant_url = os.getenv("QDRANT_URL")
qdrant_api_key = os.getenv("QDRANT_API_KEY")
groq_api_key = os.getenv("GROQ_API_KEY")

#embed_model = FastEmbedEmbeddings(model_name="BAAI/bge-base-en-v1.5")
#embed_model_2 = resolve_embed_model("local:BAAI/bge-m3")
llm_lamma3_70b = ChatGroq(temperature=0, groq_api_key=groq_api_key, model_name="llama3-70b-8192")
from langchain_community.document_loaders import WebBaseLoader

loader = GenericLoader.from_filesystem(
    "./data/docs/",
    glob="*",
    suffixes=[".pdf"],
    parser=GrobidParser(segment_sentences=False),
)
docs = loader.load()


# We need to split the text using Character Text Split such that it sshould not increse token size
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

text_splitter = RecursiveCharacterTextSplitter()
texts = text_splitter.split_documents(docs)

from langchain_community.vectorstores import Qdrant

from langchain_openai import OpenAIEmbeddings
url = "https://f336255f-9d81-439a-9d27-f09e84b17423.us-east4-0.gcp.cloud.qdrant.io:6333"
api_key = "S3wizW2QJ8IfFZxSA5lr31cAbuukpJWXbAa47_axx5f2KN9SmUmLkQ"
qdrant = Qdrant.from_documents(
    texts,
    OpenAIEmbeddings(),
    url=url,
    prefer_grpc=True,
    api_key=api_key,
    collection_name="my_documents",
    force_recreate=True,
)
retriever = qdrant.as_retriever(
    search_type="mmr",  # Also test "similarity"
    search_kwargs={"k": 8},
)


from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
# First we need a prompt that we can pass into an LLM to generate this search query

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

retriever_chain = create_history_aware_retriever(llm_lamma3_70b, retriever, prompt)

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
document_chain = create_stuff_documents_chain(llm_lamma3_70b, prompt)

qa = create_retrieval_chain(retriever_chain, document_chain)
questions = [
    "What is the name of the book?",
    "Show table of the contents of the book",
    "Show exampl eof exercise to learn python",
]

for question in questions:
    result = qa.invoke({"input": question})
    print(f"-> **Question**: {question} \n")
    print(f"**Answer**: {result['answer']} \n")