from build_query_engine import query_engine
import json
import logging
from process_image import image_to_text, image_base64_encoder
from connections import Connections

logger = logging.getLogger()
logger.setLevel(logging.INFO)
import os


def log(message):
    logger.info(message)


def get_named_parameter(parameters, name, default="NoValueFound"):
    return next(
        (item for item in parameters if item["name"] == name),
        {"value": default},
    )["value"]


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
        log(f"parameters {parameters}")
        if api_path == "/query_pricing":
            log("Text to SQL api called.")
            response = query_engine.query(user_input)

            log("Sql query:")
            log(response.metadata["sql_query"].replace("\n", " "))
            log(f"Provided response: {response.response}")
            output = {
                "source": response.metadata["sql_query"],
                "answer": response.response,
            }

        elif api_path == "/send_email":
            log("Send email api called.")

            # Add code to send email to a list of emails, such as sns
            output = {
                "source": "email source",
                "answer": "Emails sent.",
            }

        elif api_path == "/image_description":
            log("Image description api called")
            # get filename from paramter
            log(f"parameters {parameters}")
            file_name = get_named_parameter(parameters, "image_file_name")
            local_folder = "/tmp/"
            local_path = f"{local_folder}" + file_name
            s3_key = f"assets/images/{file_name}"

            log(
                f"Downloading image from s3://{Connections.agent_bucket_name}/{s3_key}, local path: {local_path}"
            )
            Connections.s3_client.download_file(
                Connections.agent_bucket_name, s3_key, local_path
            )
            # call image_to_text(filename, user_input)
            answer = image_to_text(local_path, user_input)
            log(f"Img Answer: {answer}")

            output = {
                "source": file_name,
                "answer": answer,
            }
            log(f"Img output: {output}")

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

    log(f"final body: {body}")
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
