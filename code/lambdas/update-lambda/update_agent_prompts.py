"""
update_agent_prompts.py (optional)
Optionally, you can update the 'preprocessing' and '.'orchestration' prompts.
"""
import time
import logging
from agent_prompts import PREPROCESSING_TEMPLATE, ORCHESTRATION_TEMPLATE

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Configure the prompts
promptOverrideConfiguration = {
    "promptConfigurations": [
        {
            "promptType": "PRE_PROCESSING",
            "promptCreationMode": "OVERRIDDEN",
            "promptState": "ENABLED",
            "basePromptTemplate": PREPROCESSING_TEMPLATE,
            "inferenceConfiguration": {
                "temperature": 0,
                "topP": 1,
                "topK": 250,
                "maximumLength": 256,
                "stopSequences": ["\n\nHuman:"],
            },
            "parserMode": "DEFAULT",
        },
        {
            "promptType": "ORCHESTRATION",
            "promptCreationMode": "OVERRIDDEN",
            "promptState": "ENABLED",
            "basePromptTemplate": ORCHESTRATION_TEMPLATE,
            "inferenceConfiguration": {
                "temperature": 0,
                "topP": 1,
                "topK": 250,
                "maximumLength": 2048,
                "stopSequences": ["\n\nHuman:"],
            },
            "parserMode": "DEFAULT",
        },
    ]
}


def update_agent_prompts(
    bedrock_agent,
    agent_id,
    agent_name,
    agent_resource_role_arn,
    prompt_config=promptOverrideConfiguration,
):
    """
    Update Bedrock Agent prompts.

    Args:
        bedrock_agent (BedrockAgent): The Bedrock Agent object.
        agent_id (str): The ID of the agent.
        agent_name (str): The name of the agent.
        agent_resource_role_arn (str): The ARN of the agent resource role.
        prompt_config (dict): The prompt configuration.

    Returns:
        None

    Raises:
        Exception: If the agent prompts update fails.

    Example:
        update_agent_prompts(
            bedrock_agent=bedrock_agent,
            agent_id=agent_id,
            agent_name=agent_name,
            agent_resource_role_arn=agent_resource_role_arn,
            prompt_config=promptOverrideConfiguration
        )

    """
    try:
        response = bedrock_agent.update_agent(
            agentId=agent_id,
            agentName=agent_name,
            agentResourceRoleArn=agent_resource_role_arn,
            promptOverrideConfiguration=prompt_config,
        )
    except Exception as e:
        raise Exception(f"Failed to update agent prompts: {e}")

    # Initial backoff interval in seconds
    backoff_interval = 5
    # Maximum backoff interval
    max_backoff = 60
    # Maximum number of retries
    max_retries = 10

    # Check the update agent prompt status in a loop
    for attempt in range(max_retries):
        # Get the agent update status.
        response = bedrock_agent.get_agent(agentId=agent_id)
        agent_status = response["agent"]["agentStatus"]

        if (
            agent_status == "PREPARED"
        ):  # 'CREATING'|'PREPARED'|'FAILED'|'UPDATING'|'DELETING'
            logger.info(
                f"The Bedrock Agent {agent_id} prompts are updated successfully."
            )
            break
        elif agent_status in ["UPDATING"]:
            logger.info(
                f"The Bedrock Agent {agent_id} prompts are being updated. Waiting..."
            )
            # nosemgrep: <arbitrary-sleep Message: time.sleep() call>
            time.sleep(backoff_interval)  # nosem: arbitrary-sleep
            backoff_interval = min(
                max_backoff, backoff_interval * 2
            )  # Exponential backoff with a maximum limit
        else:
            # Handle unexpected prompt update
            logger.info(
                f"Unexpected for updating agent prompts {agent_id}: {agent_status}"
            )
            break
