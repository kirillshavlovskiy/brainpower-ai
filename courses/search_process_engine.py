import chromadb
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains.conversational_retrieval.base import ConversationalRetrievalChain
from langchain.memory import ConversationSummaryMemory
from langchain.retrievers import MultiQueryRetriever, MergerRetriever
from langchain.retrievers.document_compressors import DocumentCompressorPipeline
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from code_process import code_search_process
run_local = "Yes"
local_llm = "mistral:latest"
from langchain_community.document_transformers import Html2TextTransformer, EmbeddingsClusteringFilter, \
    EmbeddingsRedundantFilter
from sentence_transformers import SentenceTransformer
import faiss
from sentence_transformers import SentenceTransformer
import numpy as np
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain.chains import LLMChain, StuffDocumentsChain
from langchain_chroma import Chroma
from langchain_community.document_transformers import (
    LongContextReorder,
)
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_openai import OpenAI, ChatOpenAI, OpenAIEmbeddings
from langchain import hub
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
import os
import pickle
from langchain_groq import ChatGroq
from langchain_community.document_loaders.parsers import GrobidParser
from langchain.document_loaders.generic import GenericLoader
import glob
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import Chroma

groq_api_key = os.getenv("GROQ_API_KEY")
apyfy_api_key = os.getenv("APIFY_API_TOKEN")
azure_api_key = os.getenv("AZURE_API_KEY")

import os
import glob
import pickle
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from urllib.parse import urlparse


def indexed_metadata_retrieval(indexed_data):
    relevant_docs = {}
    for desc in indexed_data:
        url = desc.page_content.split(',', 1)[0]
        if url in url_to_doc:
            relevant_docs[url] = url_to_doc[url]
            # Process the relevant document object as needed
            print(f"URL: {url}")
            print(f"Title: {url_to_doc[url].metadata.get('title', '')}")
            print(f"Content: {url_to_doc[url].metadata.get('description', '')}")
            relevant_docs[url] = url_to_doc[url].page_content
    # Index
    vectorstore = Chroma.from_texts(
        texts=list(relevant_docs.values()),
        collection_name="rag-chroma",
        embedding=embedding,
    )
    retriever = vectorstore.as_retriever()
    return retriever

def load_metadata():
    document_dict = {}  # Dictionary to store document objects
    url_to_doc = {} # Dictionary to map urls
    metadata_dict = {}  # Dictionary to store metadata
    # Load all documents and build metadata_dict for embeddings
    index=0
    for idx, path in enumerate(glob.glob(os.path.join('./data/web/parsed_html', '**', '*.pkl'), recursive=True)):
        with open(path, 'rb') as file:
            documents = pickle.load(file)
            for doc in documents:
                source = doc.metadata.get('source', '')
                title = doc.metadata.get('title', '')
                description = doc.metadata.get('description', '')
                if source:

                    metadata_text = f"{source.strip()}, {title.strip()}, {description.strip()}"

                    metadata_dict[index] = metadata_text  # Store metadata in the dictionary

                    document_dict[index] = doc  # Map the index to the document for retrieval
                    url_to_doc[source] = doc
                    index += 1

    # Check if there are documents to process
    if not metadata_dict:
        print("No document metadata available for processing.")
        return {}, {}, {}
    else:

        return metadata_dict, document_dict, url_to_doc

def is_valid_url(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False



# Example call to the function

metadata_dict, document_dict, url_to_doc = load_metadata()
print(metadata_dict)
# query = "What can you tell me about the Autogen agents teachability?"
# query = "How to add memory to chatbot in langchain?"
# query = "what is the difference between llamaindex and langchain?"

# Embed and index

embedding = GPT4AllEmbeddings()
all_mini = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
multi_qa_mini = HuggingFaceEmbeddings(model_name="multi-qa-MiniLM-L6-dot-v1")
#embedding = OpenAIEmbeddings()

# Index
ABS_PATH = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(ABS_PATH, "db")

# Instantiate 2 diff chromadb indexes, each one with a diff embedding.
client_settings = chromadb.config.Settings(
    is_persistent=False,
    persist_directory=DB_DIR,
    anonymized_telemetry=False,
)
vectorstore_meta = Chroma.from_documents(
    documents=list(metadata_dict.values()),
    collection_name="project_store_all",

    client_settings=client_settings,
    embedding=all_mini,
)
vectorstore_docs = Chroma.from_documents(
    documents=list(metadata_dict.values()),
    collection_name="project_store_multi_qa",
    client_settings=client_settings,
    embedding=multi_qa_mini,
)

# LLM
model = "llama3-8b-8192"
llm = ChatGroq(temperature=0, groq_api_key=groq_api_key, model_name=model)
filter_embeddings = GPT4AllEmbeddings()
retriever_all = MultiQueryRetriever.from_llm(
    retriever=vectorstore_meta.as_retriever(search_type="similarity", search_kwargs={"k": 10}), llm=llm
)
retriever_multi_qa = MultiQueryRetriever.from_llm(
    retriever=vectorstore_docs.as_retriever(search_type="mmr", search_kwargs={"k": 10}), llm=llm
)


# The Lord of the Retrievers will hold the output of both retrievers and can be used as any other
# retriever on different types of chains.
lotr = MergerRetriever(retrievers=[retriever_all, retriever_multi_qa])

# We can remove redundant results from both retrievers using yet another embedding.
# Using multiples embeddings in diff steps could help reduce biases.
# This filter will divide the documents vectors into clusters or "centers" of meaning.
# Then it will pick the closest document to that center for the final results.
# By default the result document will be ordered/grouped by clusters.
filter = EmbeddingsRedundantFilter(embeddings=filter_embeddings)
filter_ordered_cluster = EmbeddingsClusteringFilter(
    embeddings=filter_embeddings,
    num_clusters=10,
    num_closest=1,
    sorted=True,
)
#
reordering = LongContextReorder()
pipeline = DocumentCompressorPipeline(transformers=[reordering])
compression_retriever_enhanced = ContextualCompressionRetriever(
    base_compressor=pipeline, base_retriever=lotr
)
prompt = PromptTemplate(
    template="""You are a grader assessing relevance of a retrieved document to a user question. \n 
    Here is the retrieved document: \n\n {document} \n\n
    Here is the user question: {question} \n
    If the document contains keywords related to the user question, grade it as relevant. \n
    It does not need to be a stringent test. The goal is to filter out erroneous retrievals. \n
    Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question. \n
    Provide the binary score as a JSON with a single key 'score' and no premable or explanation.""",
    input_variables=["question", "document"],
)

retrieval_grader = prompt | llm | JsonOutputParser()
prompt = hub.pull("rlm/rag-prompt")

# Post-processing
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

# Chains
rag_chain = prompt | llm | StrOutputParser()


### Query Re-writer

# Prompt
re_write_prompt = PromptTemplate(
    template="""You a question re-writer that converts an input question to a better version that is optimized \n 
     for vectorstore retrieval. Look at the initial and formulate an improved question. \n
     Here is the initial question: \n\n {question}. Improved question with no preamble: \n """,
    input_variables=["generation", "question"],
)

question_rewriter = re_write_prompt | llm | StrOutputParser()

# #Memory:
# memory = ConversationSummaryMemory(llm=llm, memory_key="chat_history", return_messages=True)
# qa = ConversationalRetrievalChain.from_llm(llm, retriever=retriever, memory=memory)

# Run
chat_history = []
while True:
    query = input("input your question: ")
    new_query = question_rewriter.invoke({"question": query})
    data = compression_retriever_enhanced.get_relevant_documents(new_query)
    print(data)
    #   retriever = indexed_metadata_retrieval(data)
    #docs = retriever.invoke(new_query)
    doc_txt = data[1].page_content
    print(retrieval_grader.invoke({"question": new_query, "document": doc_txt}))
    text_generation = rag_chain.invoke({"context": data, "question": new_query})
    print(text_generation)
    #
    # code_chain, code_retriever = code_search_process(new_query)
    # code_data = code_retriever.get_relevant_documents(new_query)
    # code_generation = code_chain.invoke({"context": code_data, "question": new_query, "chat_history": chat_history})

    print(retrieval_grader.invoke({"question": new_query, "document": code_data}))
    print(f"-> **Question**: {new_query} \n")
    print(

            f"**Answer from code sources**: {text_generation} \n",
          )






# Override prompts
# document_prompt = PromptTemplate(
#     input_variables=["page_content"], template="{page_content}"
# )
# document_variable_name = "context"
# llm = OpenAI()
#
#
# stuff_prompt_override = """Given this text extracts:
# -----
# {context}
# -----
# Please answer the following question:
# {query}"""
# prompt = PromptTemplate(
#     template=stuff_prompt_override, input_variables=["context", "query"]
# )
#
# # Instantiate the chain
# llm_chain = LLMChain(llm=llm, prompt=prompt)
# chain = StuffDocumentsChain(
#     llm_chain=llm_chain,
#     document_prompt=document_prompt,
#     document_variable_name=document_variable_name,
# )
# chain.run(input_documents=reordered_docs, query=query)

# ### Retrieval Grader
# from langchain.prompts import PromptTemplate
# from langchain_core.output_parsers import JsonOutputParser
#
# # LLM
# model = "llama3-70b-8192"
# llm = ChatGroq(temperature=0, groq_api_key=groq_api_key, model_name=model)
#
# prompt = PromptTemplate(
#     template="""You are a grader assessing relevance of a retrieved document to a user question. \n
#     Here is the retrieved document: \n\n {document} \n\n
#     Here is the user question: {question} \n
#     If the document contains keywords related to the user question, grade it as relevant. \n
#     It does not need to be a stringent test. The goal is to filter out erroneous retrievals. \n
#     Give a binary score 'yes' or 'no' score to indicate whether the document is relevant to the question. \n
#     Provide the binary score as a JSON with a single key 'score' and no premable or explaination.""",
#     input_variables=["question", "document"],
# )
#
# # retrieval_grader = prompt | llm | JsonOutputParser()
#
#
#
# # Prompt
# prompt = hub.pull("rlm/rag-prompt")
#
# ### Question Re-writer
#
#
# # Prompt
# re_write_prompt = PromptTemplate(
#     template="""You a question re-writer that converts an input question to a better version that is optimized \n
#      for vectorstore retrieval. Look at the initial and formulate an improved question. \n
#      Here is the initial question: \n\n {question}. Improved question with no preamble: \n """,
#     input_variables=["generation", "question"],
# )
#
# question_rewriter = re_write_prompt | llm | StrOutputParser()
#
#
#
# # Post-processing
# def format_docs(docs):
#     return "\n\n".join(doc.page_content for doc in docs)
#
#
# Chain
#rag_chain = prompt | llm | StrOutputParser()
#
# from langchain_community.tools.tavily_search import TavilySearchResults
#
# web_search_tool = TavilySearchResults(k=3)

# Run

# while True:
#     question = input("-> **Question**:")
#     # Get relevant documents ordered by relevance score
#     docs = retriever.invoke(question)
#
#
#     doc_txt_2 = doc[1].page_content
#     grade_2 = retrieval_grader.invoke({"question": question, "document": doc_txt_2})
#     generation_2 = rag_chain.invoke({"context": doc, "question": question})
#     question_rewriter.invoke({"question": question})
#     print("generation 2: ", generation_2)
#     print(grade_2)