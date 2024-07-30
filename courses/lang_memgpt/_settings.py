from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    pinecone_api_key: str = ""
    pinecone_index_name: str = ""
    pinecone_namespace: str = "us-east-1"
    model: str = "claude-3-5-sonnet-20240620"


SETTINGS = Settings()
