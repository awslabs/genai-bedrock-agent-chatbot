import os
import boto3


class Connections:
    region_name = os.environ["AWS_REGION"]

    crawler_name = os.environ["GLUE_CRAWLER_NAME"]
    knowledgebase_id = os.environ["KNOWLEDGEBASE_ID"]
    data_source_id = os.environ["KNOWLEDGEBASE_DATASOURCE_ID"]
    agent_id = os.environ["BEDROCK_AGENT_ID"]
    agent_name = os.environ["BEDROCK_AGENT_NAME"]
    agent_alias_name = os.environ["BEDROCK_AGENT_ALIAS"]
    agent_resource_role_arn = os.environ["BEDROCK_AGENT_RESOURCE_ROLE_ARN"]

    log_level = os.environ["LOG_LEVEL"]

    update_agent = False

    glue_client = boto3.client("glue", region_name=region_name)
    bedrock_agent = boto3.client("bedrock-agent", region_name=region_name)
