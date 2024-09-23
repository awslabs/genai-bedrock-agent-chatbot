import os
import tempfile

os.environ["NLTK_DATA"] = tempfile.gettempdir()

from build_query_engine import query_engine
import json
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def log(message):
    logger.info(message)


def get_response(event, context):
    """
    Get response RAG or Query
    """

    log("Logging event:")
    log(json.dumps(event))
    responses = []

    prediction = event
    response_code = 200
    api_path = prediction["apiPath"]
    parameters = prediction["parameters"]
    user_input = parameters[0]["value"]

    # Only allow one str, to mitigate mixed prompt injection
    if isinstance(user_input, str):

        log(f"Question {user_input}")
        if api_path == "/uc2":
            response = query_engine.query(user_input)

            log("Sql query:")
            log(response.metadata["sql_query"].replace("\n", " "))
            log(f"Provided response: {response.response}")
            output = {
                "source": response.metadata["sql_query"],
                "answer": response.response,
            }

        elif api_path == "/uc1":
            output = {
                "source": "Doc retrieval",
                "answer": "Getting info from knowledgebase.",
            }

        else:
            output = {
                "source": "Not Found",
                "answer": "I don't know enough to answer this question, please try to clarify you quesiton.",
            }

    else:
        output = {
            "source": "Not Found",
            "answer": "Please ask questions one by one.",
        }

    body = f"""
            Source: {output["source"]}
            Returned information: {output["answer"]}

            """
    response_body = {"application/json": {"body": body}}  # output["answer"]#str(body)

    action_response = {
        "actionGroup": prediction["actionGroup"],
        "apiPath": prediction["apiPath"],
        "httpMethod": prediction["httpMethod"],
        "httpStatusCode": response_code,
        "responseBody": response_body,
    }

    responses.append(action_response)

    return {"messageVersion": "1.0", "response": action_response}
