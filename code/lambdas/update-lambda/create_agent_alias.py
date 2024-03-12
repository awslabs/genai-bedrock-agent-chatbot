"""
create_agent_alias.py

To create an agent alias before invoking the agent.
Ref: https://docs.aws.amazon.com/bedrock/latest/APIReference/API_agent_CreateAgentAlias.html
"""

import time
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def create_bedrock_agent_alias(
    bedrock_agent, agent_id, agent_alias_name, description="agent alias description"
):
    """
    Create Amazon Bedrock Agent Alias before invoking the agent.

    Args:
        bedrock_agent (BedrockAgent): The Amazon Bedrock Agent client object.
        agent_id (str): The ID of the agent to create the alias for.
        agent_alias_name (str): The name of the alias to create.
        description (str): The description of the alias to create.

    Returns:
        None
    """
    # Create Bedrock Agent Alias
    response = bedrock_agent.create_agent_alias(
        agentId=agent_id,
        agentAliasName=agent_alias_name,
        description=description,  # A description of the alias of the agent.
    )

    # Get Agent Alias ID
    agent_alias_id = response["agentAlias"]["agentAliasId"]

    # Initial backoff interval in seconds
    backoff_interval = 5
    # Maximum backoff interval
    max_backoff = 60
    # Maximum number of retries
    max_retries = 10

    # Check the create agent alias status in a loop
    for attempt in range(max_retries):
        response = bedrock_agent.get_agent_alias(
            agentId=agent_id, agentAliasId=agent_alias_id
        )
        alias_state = response["agentAlias"]["agentAliasStatus"]

        if alias_state == "PREPARED":
            logger.info(
                f"The Bedrock Agent {agent_id} Alias {agent_alias_name} created successfully."
            )
            break
        elif alias_state in ["CREATING", "UPDATING"]:
            logger.info(
                f"The Bedrock Agent {agent_id} Alias {agent_alias_name} is currently {alias_state.lower()}. Waiting..."
            )
            # nosemgrep: <arbitrary-sleep Message: time.sleep() call>
            time.sleep(backoff_interval)  # nosem: arbitrary-sleep
            backoff_interval = min(
                max_backoff, backoff_interval * 2
            )  # Exponential backoff with a maximum limit
        else:
            logger.info(
                f"Unexpected state for create_agent_alias {agent_alias_id}: {alias_state}"
            )
            break
