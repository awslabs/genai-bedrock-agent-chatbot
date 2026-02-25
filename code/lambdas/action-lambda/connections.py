import os
import boto3
from llama_index.llms.bedrock import Bedrock


class Connections:
    region_name = os.environ["AWS_REGION"]
    athena_bucket_name = os.environ["ATHENA_BUCKET_NAME"]
    text2sql_database = os.environ["TEXT2SQL_DATABASE"]
    log_level = os.environ["LOG_LEVEL"]
    fewshot_examples_path = os.environ["FEWSHOT_EXAMPLES_PATH"]
    s3_resource = boto3.resource("s3", region_name=region_name)
    bedrock_client = boto3.client("bedrock-runtime", region_name=region_name)

    # Cross-region inference profile IDs required for Claude 4.x models (no on-demand single-region support)
    MODELID_MAPPING = {
        "Sonnet46": ("us.anthropic.claude-sonnet-4-6", 200000),
        "Sonnet45": ("us.anthropic.claude-sonnet-4-5-20250929-v1:0", 200000),
        "Haiku45": ("us.anthropic.claude-haiku-4-5-20251001-v1:0", 200000),
        "Titan": ("amazon.titan-tg1-large", 8000),
    }

    @staticmethod
    def get_bedrock_llm(model_name="Sonnet46", max_tokens=256):
        entry = Connections.MODELID_MAPPING.get(model_name)
        if not entry:
            raise ValueError(f"Unknown model: {model_name}. Available: {list(Connections.MODELID_MAPPING.keys())}")

        model_id, context_size = entry
        llm = Bedrock(
            model=model_id,
            aws_region_name=Connections.region_name,
            max_tokens=max_tokens,
            temperature=0,
            context_size=context_size,
        )
        return llm
