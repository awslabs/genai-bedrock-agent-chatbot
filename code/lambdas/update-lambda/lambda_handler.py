from trigger_glue_crawler import trigger_glue_crawler
from trigger_data_source_sync import trigger_data_source_sync
from prepare_agent import prepare_bedrock_agent
from create_agent_alias import create_bedrock_agent_alias
from fix_agent_thinking_config import fix_agent_thinking_config
from connections import Connections
import cfnresponse

import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

glue_client = Connections.glue_client
bedrock_agent = Connections.bedrock_agent
agent_id = Connections.agent_id
agent_alias_name = Connections.agent_alias_name
agent_name = Connections.agent_name
agent_resource_role_arn = Connections.agent_resource_role_arn
data_source_id = Connections.data_source_id
knowledgebase_id = Connections.knowledgebase_id
crawler_name = Connections.crawler_name
update_agent = Connections.update_agent


def lambda_handler(event, context):
    """
    Trigger Glue Crawler, Data Source Sync, Create Agent Alias, and Update Agent Prompts (optional).
    """
    logger.info(f"Received event: {event}")

    status = cfnresponse.SUCCESS
    status_code = 200
    status_body = "Success"
    response = {}

    try:
        if event["RequestType"] == "Create":
            # Trigger Glue Crawler
            logger.info("Starting Glue Crawler trigger.")
            trigger_glue_crawler(glue_client, crawler_name)
            logger.info("Glue Crawler triggered successfully.")

            # Trigger Data Source Sync
            logger.info("Starting Data Source Sync.")
            trigger_data_source_sync(bedrock_agent, knowledgebase_id, data_source_id)
            logger.info("Data Source Sync triggered successfully.")

            # Correct the reasoning configuration before preparing, so the agent
            # version captured by the alias carries the fix.
            logger.info("Checking Bedrock Agent reasoning configuration.")
            fix_agent_thinking_config(bedrock_agent, agent_id)
            logger.info("Reasoning configuration check complete.")

            # Preapre Bedrock Agent
            logger.info("Starting Preparing Bedrock Agent.")
            prepare_bedrock_agent(bedrock_agent, agent_id)
            logger.info("Bedrock Agent Prepared successfully.")

            # Create Agent Alias
            logger.info("Creating Agent Alias.")
            create_bedrock_agent_alias(bedrock_agent, agent_id, agent_alias_name)
            logger.info("Agent Alias created successfully.")

        elif event["RequestType"] == "Delete":

            response = bedrock_agent.list_agent_aliases(agentId=agent_id)
            # Bedrock always returns the built-in test alias "TSTALIASID", which
            # cannot be deleted -- DeleteAgentAlias rejects it with the constraint
            # (?!\bTSTALIASID\b)[0-9a-zA-Z]+. Attempting it fails the custom
            # resource and leaves the whole stack in DELETE_FAILED, orphaning
            # resources. It is removed along with the agent itself.
            alias_ids = [
                summary["agentAliasId"]
                for summary in response["agentAliasSummaries"]
                if summary["agentAliasId"] != "TSTALIASID"
            ]
            logger.info(f"Deleting alias ids: {alias_ids}.")

            for agent_alias_id in alias_ids:
                bedrock_agent.delete_agent_alias(
                    agentId=agent_id, agentAliasId=agent_alias_id
                )

            response = bedrock_agent.delete_agent(
                agentId=agent_id, skipResourceInUseCheck=False
            )
            logger.info(f"Deleted agent id: {agent_id}.")
        else:
            logger.info("Continuing without action.")

    except Exception as e:
        # Log the error
        logger.error(f"An error occurred: {e}")

        status = cfnresponse.FAILED
        status_code = 500
        status_body = "An error occurred during the process."

        response = {"Error": str(e)}

    finally:
        logger.error(f"Sending status: {status} with response: {response}")
        cfnresponse.send(event, context, status, response)

    # If everything went well
    return {"statusCode": status_code, "body": status_body}
