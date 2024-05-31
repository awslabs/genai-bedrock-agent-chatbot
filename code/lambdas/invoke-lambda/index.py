import boto3
import json
import logging
import os
from collections import OrderedDict
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def log(message):
    logger.info(message)


AGENT_ID = os.environ["AGENT_ID"]
REGION_NAME = os.environ["REGION_NAME"]

log(f"Agent id: {AGENT_ID}")

agent_client = boto3.client("bedrock-agent", region_name=REGION_NAME)
agent_runtime_client = boto3.client(
    "bedrock-agent-runtime", region_name=REGION_NAME)
s3_resource = boto3.resource("s3", region_name=REGION_NAME)


def get_highest_agent_version_alias_id(response):
    """
    Find newest agent alias id.

    Args:
        response (dict): Response from list_agent_aliases().

    Returns:
        str: Agent alias ID of the newest agent version.
    """
    # Initialize highest version info
    highest_version = None
    highest_version_alias_id = None

    # Iterate through the agentAliasSummaries
    for alias_summary in response.get("agentAliasSummaries", []):
        # Assuming each alias has one routingConfiguration
        if alias_summary["routingConfiguration"]:
            agent_version = alias_summary["routingConfiguration"][0]["agentVersion"]
            # Check if the version is numeric and higher than the current highest
            if agent_version.isdigit() and (
                highest_version is None or int(agent_version) > highest_version
            ):
                highest_version = int(agent_version)
                highest_version_alias_id = alias_summary["agentAliasId"]

    # Return the highest version alias ID or None if not found
    return highest_version_alias_id


def invoke_agent(user_input, session_id):
    """
    Get response from Agent
    """
    response = agent_client.list_agent_aliases(agentId=AGENT_ID)

    log(f"list_agent_aliases: {response}")
    agent_alias_id = get_highest_agent_version_alias_id(response)
    if not agent_alias_id:
        return "No agent published alias found - cannot invoke agent"
    streaming_response = agent_runtime_client.invoke_agent(
        agentId=AGENT_ID,
        agentAliasId=agent_alias_id,
        sessionId=session_id,
        enableTrace=True,
        inputText=user_input,
    )

    return streaming_response


def get_agent_response(response):
    log(f"Getting agent response... {response}")
    if "completion" not in response:
        return f"No completion found in response: {response}"
    trace_list = []
    for event in response["completion"]:
        log(f"Event keys: {event.keys()}")
        if "trace" in event:
            log(event["trace"])
            trace_list.append(event["trace"])

        # Extract the traces
        if "chunk" in event:
            # Extract the bytes from the chunk
            chunk_bytes = event["chunk"]["bytes"]

            # Convert bytes to string, assuming UTF-8 encoding
            chunk_text = chunk_bytes.decode("utf-8")

            # Print the response text
            print("Response from the agent:", chunk_text)
    sql_query_from_llm = None
    for t in trace_list:
        if "orchestrationTrace" in t["trace"].keys():
            if "observation" in t["trace"]["orchestrationTrace"].keys():
                obs = t["trace"]["orchestrationTrace"]["observation"]
                if obs["type"] == "ACTION_GROUP":
                    sql_query_from_llm = extract_sql_query(
                        obs["actionGroupInvocationOutput"]["text"]
                    )
    if sql_query_from_llm:
        source_file_list = sql_query_from_llm
    else:
        try:
            source_file_list = extract_source_list_from_kb(trace_list)
        except Exception as e:
            log(f"Error extracting source list from KB: {e}")
            source_file_list = ""
    return chunk_text, source_file_list


def extract_source_list_from_kb(trace_list):
    """
    Extract the knowledge base lookup output from the trace list and return the S3 bucket paths.
    """
    for trace in trace_list:
        if  'orchestrationTrace' in trace['trace'].keys() and 'observation' in trace['trace']['orchestrationTrace'].keys():
            if 'knowledgeBaseLookupOutput' in trace['trace']['orchestrationTrace']['observation']:
                ref_list = trace['trace']['orchestrationTrace']['observation']['knowledgeBaseLookupOutput']['retrievedReferences']
    log(f"ref_list: {ref_list}")
    ref_s3_list = []
    for rl in ref_list:
        ref_s3_list.append(rl['location']['s3Location']['uri'])
    
    return ref_s3_list


def source_link(input_source_list):
    """
    Retrieves and formats the source URLs and titles of relevant documents from a given list of S3 bucket paths.

    This function takes a list of S3 bucket paths, extracts the bucket name and object key from each path, and then reads
    the content of these objects assuming they are JSON files containing 'Url' and 'Topic' keys. It then formats these
    into a markdown-style numbered list of references with clickable links.

    Parameters:
    - input_source_list (list of str): A list containing S3 bucket paths to the relevant documents.

    Returns:
    - str: A string representing a markdown-formatted numbered list of document titles linked to their source URLs.
    """
    source_dict_list = []
    for i, input_source in enumerate(input_source_list):
        string = input_source.split("//")[1]
        bucket = string.partition("/")[0]
        obj = string.partition("/")[2]
        file = s3_resource.Object(bucket, obj)
        body = file.get()["Body"].read()
        res = json.loads(body)
        source_link_url = res["Url"]
        source_title = res["Topic"]
        source_dict = (source_title, source_link_url)
        source_dict_list.append(source_dict)

    # get the unique sources
    unique_sources = list(OrderedDict.fromkeys(source_dict_list))

    refs_str = ""
    for i, (title, link) in enumerate(unique_sources, start=1):
        refs_str += f"{i}. [{title}]({link})\n\n"

    return refs_str


def extract_sql_query(input_string):
    """
    Extracts the SQL query from a given input string.

    This function takes an input string, searches for a SQL query in it, and returns the extracted query. It
    assumes the SQL query is the first string that starts with "SELECT" and ends with a non-SQL keyword.


    example input: "\n Source: SELECT instance_type, price_per_hour \nFROM training_price\nWHERE instance_type = 'ml.m5.xlarge'\n Returned information: According to the latest information, the ml.m5.xlarge instance type costs '$0.23' per hour for training.\n\n"

    Parameters:
    - input_string (str): The input string to search for a SQL query.

    Returns:
    - str: The extracted SQL query, or None if no SQL query is found.
    """

    pattern = r"(SELECT.*?)(?=\n\s*(?:Returned information|$))"

    # Search for the pattern in the input string using DOTALL flag to match across multiple lines
    match = re.search(pattern, input_string, re.DOTALL | re.IGNORECASE)

    # If a match is found, return the matched string, otherwise return None
    if match:
        return match.group(
            1
        ).strip()  # Use strip() to remove leading/trailing whitespace
    else:
        return None


def lambda_handler(event, context):
    """
    Lambda handler to answer user's question
    """
    log("Event:")
    log(json.dumps(event))

    body = event["body"]

    streaming_response = invoke_agent(body["query"], body["session_id"])
    response, source_file_list = get_agent_response(streaming_response)
    if isinstance(source_file_list, list):
        reference_str = source_link(source_file_list)
    else:
        reference_str = source_file_list
    print(f"reference_str: {reference_str}")

    output = {"answer": response, "source": reference_str}

    return output
