import os
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    gcp_project: str = os.getenv("GCP_PROJECT")
    bq_dataset: str = os.getenv("BQ_DATASET")
    bq_lounges_table: str = os.getenv("BQ_LOUNGES_TABLE")
    vertex_model: str =os.getenv("VERTEX_MODEL")
    gemini_api_key: str=os.getenv("GEMINI_API_KEY")
    ocr_confidence_threshold: float = 0.7

settings = Settings()









