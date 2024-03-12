"""
trigger_glue_crawler.py

Trigger AWS Glue Crawler, to generate AWS Glue Database before querying.
"""

import time
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def trigger_glue_crawler(glue_client, crawler_name):
    """
    Triggers a Glue crawler.

    Args:
        glue_client (boto3.client): The Glue client.
        crawler_name (str): The name of the crawler to trigger.

    Returns:
        None
    """
    # Start the Glue Crawler
    _ = glue_client.start_crawler(Name=crawler_name)

    logger.info(f"Triggered Crawler {crawler_name}. Waiting for it to complete...")

    # Initial backoff interval in seconds
    backoff_interval = 5
    # Maximum backoff interval
    max_backoff = 60
    # Maximum number of retries
    max_retries = 10

    # Check the status in a loop
    for attempt in range(max_retries):
        # Fetch the current state of the crawler
        crawler_metadata = glue_client.get_crawler(Name=crawler_name)
        crawler_state = crawler_metadata["Crawler"]["State"]

        if crawler_state == "READY":
            logger.info(f"Crawler {crawler_name} completed successfully.")
            break
        elif crawler_state in ["RUNNING", "STOPPING"]:
            # Crawler is still running or in the process of stopping, wait and check again
            logger.info(
                f"Crawler {crawler_name} is currently {crawler_state.lower()}. Waiting..."
            )
            # nosemgrep: <arbitrary-sleep Message: time.sleep() call>
            time.sleep(backoff_interval)  # nosem: arbitrary-sleep
            backoff_interval = min(
                max_backoff, backoff_interval * 2
            )  # Exponential backoff with a maximum limit
        else:
            # Handle unexpected crawler state
            logger.info(f"Unexpected state for Crawler {crawler_name}: {crawler_state}")
            break


# Function to check the crawler's state
def is_crawler_ready(glue_client, crawler_name):
    """
    Checks if the crawler is ready.

    Args:
        crawler_name (str): The name of the crawler to check.

    Returns:
        bool: True if the crawler is ready, False otherwise.
    """
    # Get the crawler's state from Glue
    crawler_status = glue_client.get_crawler(Name=crawler_name)["Crawler"]["State"]

    # Check if the crawler is ready
    return crawler_status
