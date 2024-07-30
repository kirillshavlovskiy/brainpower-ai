from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    pinecone_api_key: str = "3384fd7c-8f10-4cb7-a06b-a79afe4a6da1"
    pinecone_index_name: str = "mem"
    pinecone_namespace: str = "us-east-1"
    model: str = "claude-3-5-sonnet-20240620"


SETTINGS = Settings()
