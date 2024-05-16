import os
import boto3
from llama_index.llms.bedrock import Bedrock


class Connections:
    region_name = os.environ["AWS_REGION"]
    athena_bucket_name = os.environ["ATHENA_BUCKET_NAME"]
    agent_bucket_name = os.environ["AGENT_BUCKET_NAME"]
    text2sql_database = os.environ["TEXT2SQL_DATABASE"]
    log_level = os.environ["LOG_LEVEL"]
    fewshot_examples_path = os.environ["FEWSHOT_EXAMPLES_PATH"]
    s3_resource = boto3.resource("s3", region_name=region_name)
    s3_client = boto3.client("s3", region_name=region_name)
    bedrock_client = boto3.client("bedrock-runtime", region_name=region_name)

    @staticmethod
    def get_bedrock_llm(model_name="ClaudeInstant", max_tokens=256):
        MODELID_MAPPING = {
            "Titan": "amazon.titan-tg1-large",
            "Jurassic": "ai21.j2-ultra-v1",
            "Claude2": "anthropic.claude-v2",
            "ClaudeInstant": "anthropic.claude-instant-v1",
        }

        MODEL_KWARGS_MAPPING = {
            "Titan": {
                "max_tokens": max_tokens,
                "temperature": 0,
            },
            "Jurassic": {
                "max_tokens": max_tokens,
                "temperature": 0,
            },
            "Claude2": {
                "max_tokens": max_tokens,
                "temperature": 0,
            },
            "ClaudeInstant": {
                "max_tokens": max_tokens,
                "temperature": 0,
            },
        }
        model_kwargs = MODEL_KWARGS_MAPPING[model_name].copy()
        model_kwargs = MODEL_KWARGS_MAPPING[model_name].copy()

        model_kwargs.update(
            {
                "model": MODELID_MAPPING[model_name],
                "aws_region_name": Connections.region_name,
            }
        )

        llm = Bedrock(**model_kwargs)

        return llm
