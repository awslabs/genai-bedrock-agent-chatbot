import os
import boto3
import json
from botocore.config import Config

session = boto3.Session()

if os.environ.get("ACCOUNT_ID") is None:
    ACCOUNT_ID = session.client("sts").get_caller_identity().get("Account")
    AWS_REGION = session.region_name
else:
    ACCOUNT_ID = os.environ["ACCOUNT_ID"]
    AWS_REGION = os.environ["AWS_REGION"]

if os.environ.get("LAMBDA_FUNCTION_NAME") is None:
    try:
        # read in json file cdk.json
        with open("../../cdk.json", encoding="utf-8") as f:
            data = json.load(f)
        config = data["context"]["config"]
        STACK_NAME = config["names"]["stack_name"]
        STREAMLIT_INVOKE_LAMBDA_FUNCTION_NAME = config["names"][
            "streamlit_lambda_function_name"
        ]
        lambda_function_name = f"{STACK_NAME}-{STREAMLIT_INVOKE_LAMBDA_FUNCTION_NAME}-{ACCOUNT_ID}-{AWS_REGION}"
    except Exception:
        raise ValueError(
            "LAMBDA_FUNCTION_NAME not found in environment or cdk.json.")
else:
    lambda_function_name = os.environ["LAMBDA_FUNCTION_NAME"]


class Connections:
    lambda_function_name = lambda_function_name
    lambda_client = boto3.client(
        "lambda",
        region_name=AWS_REGION,
        config=Config(read_timeout=300, connect_timeout=300),
    )
