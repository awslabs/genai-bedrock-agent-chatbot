"""
trigger_data_source_sync.py

To trigger the "Data Source" Sync step after Knowledgebase is created.
Ref: https://docs.aws.amazon.com/bedrock/latest/userguide/knowledge-base-ingest.html
"""
import time
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def trigger_data_source_sync(bedrock_agent, knowledgebase_id, data_source_id):
    """
    Trigger the "Data Source" Sync step after Knowledgebase is created.
    Args:
        bedrock_agent (BedrockAgent): The BedrockAgent instance.
        knowledgebase_id (str): The ID of the Knowledgebase.
        data_source_id (str): The ID of the Data Source.
    Returns:
        None.
    Raises:
        Exception: If the "Data Source" Sync step fails.
        Exception: If the "Data Source" Sync step is not complete.
        Exception: If the "Data Source" Sync step is not in progress.
        Exception: If the "Data Source" Sync step is not starting.
        Exception: If the "Data Source" Sync step is not complete.
        Exception: If the "Data Source" Sync step is not failed.
        Exception: If the "Data Source" Sync step is not unknown.
        Exception: If the "Data Source" Sync step is not in progress.
        Exception: If the "Data Source" Sync step is not complete.
        Exception: If the "Data Source" Sync step is not failed.
    """

    # Start the "Data Source" Sync step of the ingestion job.
    response = bedrock_agent.start_ingestion_job(
        knowledgeBaseId=knowledgebase_id, dataSourceId=data_source_id
    )

    # Retrieve the ingestion job ID
    ingestion_job_id = response["ingestionJob"]["ingestionJobId"]

    # Initial backoff interval in seconds
    backoff_interval = 5
    # Maximum backoff interval
    max_backoff = 60
    # Maximum number of retries
    max_retries = 10

    # Check the ingestion job status in a loop
    for attempt in range(max_retries):
        # Get the ingestion job's status.
        response = bedrock_agent.get_ingestion_job(
            knowledgeBaseId=knowledgebase_id,
            dataSourceId=data_source_id,
            ingestionJobId=ingestion_job_id,
        )
        ingestion_job_state = response["ingestionJob"]["status"]

        if ingestion_job_state == "COMPLETE":
            logger.info(
                f"The Knowledgebase ingestion job {ingestion_job_id} completed successfully."
            )
            break
        elif ingestion_job_state in [
            "STARTING",
            "IN_PROGRESS",
        ]:  # 'STARTING'|'IN_PROGRESS'|'COMPLETE'|'FAILED',
            logger.info(
                f"The Knowledgebase ingestion job {ingestion_job_id} is currently {ingestion_job_state.lower()}. Waiting..."
            )
            # nosemgrep: <arbitrary-sleep Message: time.sleep() call>
            time.sleep(backoff_interval)  # nosem: arbitrary-sleep
            backoff_interval = min(
                max_backoff, backoff_interval * 2
            )  # Exponential backoff with a maximum limit
        else:
            # Handle unexpected ingestionJob state
            logger.info(
                f"Unexpected state for ingestionJob {ingestion_job_id}: {ingestion_job_state}"
            )
            break
