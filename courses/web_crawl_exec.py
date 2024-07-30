import requests
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from collections import deque
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import GPT4AllEmbeddings
from langchain.indexes import VectorstoreIndexCreator
from langchain_community.utilities import ApifyWrapper
from langchain_core.documents import Document
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.document_transformers import Html2TextTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.output_parsers import StrOutputParser
from langchain_groq import ChatGroq
from langchain import hub
import os
import pickle
import re

model = "llama3-70b-8192"
groq_api_key = os.getenv("GROQ_API_KEY")
llm = ChatGroq(temperature=0, groq_api_key=groq_api_key, model_name=model)
embedding = GPT4AllEmbeddings()


def sanitize_filename(url):
    """Create a safe filename from a URL by removing unsafe characters."""
    return re.sub(r'[^\w\-_\. ]', '_', url)  # Replace disallowed chars with underscores


# def apify_loader(url):
#     loader = apify.call_actor(
#                 actor_id="apify/website-content-crawler",
#                 run_input={"startUrls": [
#                                          {"url": url},
#
#                                          ]},
#                 dataset_mapping_function=lambda item: Document(
#                     page_content=item["text"] or "", metadata={"source": item["url"]}
#                 ),
#
#             )


def simple_loader(url):
    loader = WebBaseLoader(url)
    document = loader.load()
    html2text = Html2TextTransformer()
    transformed_doc = html2text.transform_documents(document)
    text_splitter = RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        chunk_size=500, chunk_overlap=100, disallowed_special=()
    )
    splits = text_splitter.split_documents(transformed_doc)
    return splits


def is_valid(url, base_url):
    parsed = urlparse(url)
    return bool(parsed.netloc) and parsed.netloc == urlparse(base_url).netloc


def crawl(start_url, max_depth=10, k=25):
    visited = set()
    sanitized_url = sanitize_filename(start_url)
    data_file = f"./data/web/parsed_html/parsed_data {sanitized_url}.pkl"

    dir_path = os.path.join("./data/web/parsed_html/")
    queue = deque([(start_url, 0)])
    parsed_links_count = 0  # Initialize a counter for parsed links

    if os.path.exists(data_file):
        print("file already exists")
        return data_file
    else:
        document_parsed = []
        i = 1
        while queue and parsed_links_count < k:

            current_url, depth = queue.popleft()

            if depth > max_depth:
                continue

            try:
                response = requests.get(current_url)
                soup = BeautifulSoup(response.text, 'html.parser')

                for link in soup.find_all('a', href=True):
                    full_url = urljoin(current_url, link['href'])
                    if full_url not in visited and is_valid(full_url, start_url):
                        visited.add(full_url)
                        print(f"url {i} is processed:", full_url)
                        document_parsed.append(simple_loader(full_url)[0])
                        i += 1
                        parsed_links_count += 1
                        if parsed_links_count < k:
                            queue.append((full_url, depth + 1))
                        else:
                            break  # Break out of the loop if the limit is reached
            except requests.exceptions.RequestException as e:
                print(f"An error occurred: {e}")

        if not os.path.exists(dir_path):
            os.makedirs(dir_path, exist_ok=True)

        # Open the file in binary write mode
        with open(data_file, "wb") as f:
            pickle.dump(document_parsed, f)

            print(f"text is saved to file{data_file}:\n", document_parsed)

    return data_file



def main():
    all_links = []
    urls = [
        "https://python.langchain.com/docs/get_started/introduction/#-langserve",
        "https://python.langchain.com/docs/get_started/introduction/#%EF%B8%8F-langgraph",
        "https://python.langchain.com/docs/use_cases/question_answering/quickstart/",
        "https://python.langchain.com/docs/use_cases/question_answering/chat_history/",
        "https://python.langchain.com/docs/use_cases/chatbots/",
        "https://python.langchain.com/docs/use_cases/tool_use/",
        "https://python.langchain.com/docs/expression_language/",
        "https://python.langchain.com/docs/use_cases/tool_use/agents/",
        "https://python.langchain.com/docs/modules/model_io/llms/quick_start/",
    ]
    for url in urls:
        print(url)
        file_path = crawl(url)



        with open(file_path, "rb") as f:
            parse_documents = pickle.load(f)
            print(parse_documents)
        vectorstore_1 = Chroma.from_documents(
            documents=parse_documents,
            collection_name="rag-chroma-1",
            embedding=embedding,
        )
        retriever = vectorstore_1.as_retriever(
            search_type="mmr",  # Also test "similarity"
            search_kwargs={"k": 8},
        )
        # Prompt
        prompt = hub.pull("rlm/rag-prompt")
        rag_chain = prompt | llm | StrOutputParser()
        question = 'show what is this site about'
        context = retriever.get_relevant_documents(question)
        response = rag_chain.invoke({"context": context, "question": question})
        print(response)

    print(all_links)


if __name__ == "__main__":
    main()