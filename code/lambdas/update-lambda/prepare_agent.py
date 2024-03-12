"""
prepare_agent.py

To prepare the Bedrock agent.
Ref: https://docs.aws.amazon.com/bedrock/latest/userguide/agents-api-agent.html#w262aac34c33c21b7
"""

import time
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def prepare_bedrock_agent(bedrock_agent, agent_id):
    """
    Create Amazon Bedrock Agent Alias before invoking the agent.

    Args:
        bedrock_agent (BedrockAgent): The Amazon Bedrock Agent client object.
        agent_id (str): The ID of the agent to create the alias for.

    Returns:
        None
    """
    # Prepare the Agent
    response = bedrock_agent.prepare_agent(agentId=agent_id)

    # Initial backoff interval in seconds
    backoff_interval = 5
    # Maximum backoff interval
    max_backoff = 60
    # Maximum number of retries
    max_retries = 10

    # Check agent status
    for attempt in range(max_retries):
        # Get the alias creating status.
        response = bedrock_agent.get_agent(agentId=agent_id)
        agent_prep_status = response["agent"]["agentStatus"]

        if (
            agent_prep_status == "PREPARED"
        ):  # 'CREATING'|'PREPARED'|'FAILED'|'UPDATING'|'DELETING'
            logger.info(f"The Bedrock Agent {agent_id} is prepared successfully.")
            break
        elif agent_prep_status in ["CREATING", "UPDATING", "PREPARING"]:
            logger.info(
                f"The Bedrock Agent {agent_id} is currently {agent_prep_status.lower()}. Waiting..."
            )
            # nosemgrep: <arbitrary-sleep Message: time.sleep() call>
            time.sleep(backoff_interval)  # nosem: arbitrary-sleep
            backoff_interval = min(
                max_backoff, backoff_interval * 2
            )  # Exponential backoff with a maximum limit
        else:
            # Handle unexpected alias create state
            logger.info(
                f"Unexpected state for the agent {agent_id}: {agent_prep_status}"
            )
            break
