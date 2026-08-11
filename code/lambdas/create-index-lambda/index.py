from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import os
import boto3
import json
import logging
import cfnresponse
import time

HOST = os.environ.get("COLLECTION_HOST")
VECTOR_INDEX_NAME = os.environ.get("VECTOR_INDEX_NAME")
VECTOR_FIELD_NAME = os.environ.get("VECTOR_FIELD_NAME")
# Must match the KnowledgeBase embedding model's output vector size. Set from
# cdk.json (context.config.models.bedrock_embedding_dimension) so it cannot drift
# from the configured embedding model.
VECTOR_DIMENSION = int(os.environ.get("VECTOR_DIMENSION", "1024"))
REGION_NAME = os.environ.get("REGION_NAME")
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def log(message):
    logger.info(message)


def build_index_body(dimension):
    """
    Build the OpenSearch index definition for a given k-NN vector dimension.
    """
    return {
        # This section contains specific index-level configurations.
        "settings": {
            # This setting enables you to perform real-time k-NN search on an index. k-NN search lets you find the "k" closest points in your vector space by Euclidean distance or cosine similarity.
            "index.knn": True,
            "index.knn.algo_param.ef_search": 512,
        },
        "mappings": {
            "properties": {  # Properties section is where you define the fields (properties) of the documents that will be stored in the index.
                VECTOR_FIELD_NAME: {  # Name of the field
                    # This specifies that the field is a k-NN vector type. This type is provided by the k-NN plugin and is necessary for performing nearest neighbor searches on the data.
                    "type": "knn_vector",
                    "dimension": dimension,
                    "method": {  # 'method' contains settings for the algorithm used for k-NN calculations. Default method is l2(stands for Euclidean distance). You can also use cosine similarity.
                        # Space in which distance calculations will be done. "l2" stands for L2 space (Euclidean distance)
                        "space_type": "innerproduct",
                        # Underlying engine to perform the vector calculations. FAISS is a library for efficient similarity search and clustering of dense vectors. The alternative is "nmslib".
                        "engine": "FAISS",
                        # This specifies the exact algorithm FAISS will use for k-NN calculations. HNSW stands for Hierarchical Navigable Small World, which is efficient for similarity searches.
                        "name": "hnsw",
                        "parameters": {
                            "m": 16,
                            "ef_construction": 512,
                        },
                    },
                },
                "AMAZON_BEDROCK_METADATA": {"type": "text", "index": False},
                "AMAZON_BEDROCK_TEXT_CHUNK": {"type": "text"},
                "id": {"type": "text"},
            }
        },
    }


def existing_dimension(client, index_name):
    """
    Return the k-NN dimension of the vector field on an existing index, or None
    if the index or the field is absent.
    """
    mapping = client.indices.get_mapping(index=index_name)
    properties = (
        mapping.get(index_name, {})
        .get("mappings", {})
        .get("properties", {})
        .get(VECTOR_FIELD_NAME, {})
    )
    return properties.get("dimension")


def ensure_index(client, index_name, dimension):
    """
    Create the index if absent. If it exists with a different vector dimension,
    recreate it -- an embedding model change alters the output vector size, and
    OpenSearch cannot change a k-NN field's dimension in place. Recreating drops
    the vectors, so the KnowledgeBase data source must be re-ingested afterwards
    (the update lambda triggers a sync on every deployment).
    """
    if client.indices.exists(index=index_name):
        current = existing_dimension(client, index_name)
        if current == dimension:
            log(
                f"Index {index_name} already exists with dimension {dimension}; nothing to do."
            )
            return
        log(
            f"Index {index_name} exists with dimension {current}, expected {dimension}. Recreating."
        )
        client.indices.delete(index=index_name)
        # Deletions are not immediately visible to subsequent creates.
        # nosemgrep: <arbitrary-sleep Message: time.sleep() call>
        time.sleep(30)  # nosem: arbitrary-sleep
    else:
        log(f"Index {index_name} does not exist. Creating.")

    response = client.indices.create(
        index=index_name, body=build_index_body(dimension)
    )
    log(f"Response: {response}")

    # wait 1 minute - need to change to syncronous call in cdk and implement response
    log("Sleeping for 1 minutes to let index create.")
    # nosemgrep: <arbitrary-sleep Message: time.sleep() call>
    time.sleep(60)  # nosem: arbitrary-sleep


def lambda_handler(event, context):
    """
    Lambda handler to create OpenSearch Index
    """
    log(f"Event: {json.dumps(event)}")

    session = boto3.Session()

    # Get STS client from session
    sts_client = session.client("sts")

    # Get caller identity
    caller_identity = sts_client.get_caller_identity()

    # Print the caller identity information
    log(f"Caller Identity: {caller_identity}")

    # Specifically, print the ARN of the caller
    log(f"ARN: {caller_identity['Arn']}")

    creds = session.get_credentials()

    # Get STS client from session
    sts_client = session.client("sts")

    # Get caller identity
    caller_identity = sts_client.get_caller_identity()

    # Print the caller identity information
    log(f"Caller Identity: {caller_identity}")

    # Specifically, print the ARN of the caller
    log(f"ARN: {caller_identity['Arn']}")

    log(f"HOST: {HOST}")
    host = HOST.split("//")[1]

    region = REGION_NAME
    service = "aoss"
    status = cfnresponse.SUCCESS
    response = {}

    try:
        auth = AWSV4SignerAuth(creds, region, service)

        client = OpenSearch(
            hosts=[{"host": host, "port": 443}],
            http_auth=auth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            pool_maxsize=20,
        )
        index_name = VECTOR_INDEX_NAME

        if event["RequestType"] in ("Create", "Update"):
            log(
                f"{event['RequestType']}: ensuring index {index_name} "
                f"with dimension {VECTOR_DIMENSION}"
            )
            ensure_index(client, index_name, VECTOR_DIMENSION)

        elif event["RequestType"] == "Delete":
            log(f"Deleting index: {index_name}")
            response = client.indices.delete(index=index_name)
            log(f"Response: {response}")
        else:
            log("Continuing without action.")

    except Exception as e:
        logging.error("Exception: %s" % e, exc_info=True)
        status = cfnresponse.FAILED

    finally:
        cfnresponse.send(event, context, status, response)

    return {
        "statusCode": 200,
        "body": json.dumps("Create index lambda ran successfully."),
    }
