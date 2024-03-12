# Action Lambda

## Introduction

This Lambda acts as 'Action Group' of the Amazon Bedrock Agent.
It's triggered to answer questions related to querying structured data.

The Lambda handler needs to have a schema in order to execute the function call issued by the Amazon Bedrock Agent.

Here is the API schema for this lambda:

- [artifacts_schema](../../../assets/agent_api_schema/artifacts_schema.json)

## Component Details

#### Prerequisites (requirements.txt)

- boto3==1.34.37
- llama-index==0.10.6
- llama-index-embeddings-bedrock==0.1.3
- llama-index-llms-bedrock==0.1.3
- sqlalchemy==2.0.23
- PyAthena[SQLAlchemy]

#### Technology stack

- [AWS Lambda](https://aws.amazon.com/lambda/)
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)
- [AWS Secrets Manger](https://aws.amazon.com/secrets-manager/)
- [AWS Key Management Service](https://aws.amazon.com/kms/)
- [Amazon Athena](https://aws.amazon.com/athena/)

#### Package Details

| Files                                          | Description                                                                                                       |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| [connections.py](connections.py)               | Python file with `Connections` class for establishing connections with external dependencies of the lambda        |
| [build_query_engine.py](build_query_engine.py) | Python file build query engine that translate natural language to SQL, and execute against the connected database |
| [index.py](index.py)                           | Python file containing the `lambda_handler` function that acts as the starting point for Amazon Lambda invocation |
| [prompt_templates.py](prompt_templates.py)     | Python variables with input Prompts for the LLM to operate                                                        |
| [dynamic_examples.csv](dynamic_examples.csv)   | CSV file contains 'natural language t SQL' example pairs. invocation                                              |     |
| [Dockerfile](Dockerfile)                       | Dockerfile to build image for Amazon Lambda deployment service                                                    |
| [requirements.txt](requirements.txt)           | requirements.txt file used to build the docker image                                                              |

#### Input

The Amazon Lambda is part of the Action Group associated the Amazon Bedrock Agent, the event is sent by the Amazon Bedrock Agent when the user asks a question.

```json
{
  "agent": {
    "alias": "agent-alias",
    "name": "agent-name",
    "version": "agent-version",
    "id": "agent-id"
  },
  "sessionId": "216876597295710",
  "sessionAttributes": {},
  "promptSessionAttributes": {},
  "inputText": "your input query",
  "apiPath": "/uc2",
  "httpMethod": "GET",
  "messageVersion": "1.0",
  "actionGroup": "ChatBotBedrockAgentActionGroup",
  "parameters": [
    {
      "name": "uc2Question",
      "type": "string",
      "value": "what is the price per hour of the most expensive ec2 instance? (from your input query)"
    }
  ]
}
```

#### Output

This lambda generates the following output

```json
{
    "actionGroup": prediction["actionGroup"],
    "apiPath": prediction["apiPath"],
    "httpMethod": prediction["httpMethod"],
    "httpStatusCode": response_code,
    "responseBody": response_body
}
```

| Field            | Description                                                                                                                                                      | Data Type  |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| `actionGroup`    | Action group associate with the Amazon Bedrock Agent                                                                                                             | String     |
| `apiPath`        | Denotes the path of the API call                                                                                                                                 | String     |
| `httpMethod`     | A HTTP method defined in the lambda handler                                                                                                                      | String     |
| `httpStatusCode` | A HTTP status code that denotes the output status of validation. A `200` value means validation completed successfully                                           | Number     |
| `responseBody`   | List of answer IDs that are determined to be off-topic when compared to the question asked. A string literal of '-1' means there is no answers that are off-topic. | Dictionary |

Here is the the structure of the `responseBody`:

```json
body = f"""
        Source: {output["source"]}
        Returned information: {output["answer"]}

        """
response_body = {
    "application/json": {
        "body": body
    }
}
```

#### Environmental Variables

| Field                   | Description                                                         | Data Type |
| ----------------------- | ------------------------------------------------------------------- | --------- |
| `ATHENA_BUCKET_NAME`    | Set the S3 bucket name before running Athena query                  | String    |
| `TEXT2SQL_DATABASE`     | Sets the database in AWS Glue                                       | String    |
| `LOG_LEVEL`             | Sets service log level                                              | String    |
| `FEWSHOT_EXAMPLES_PATH` | Sets the path toe retrieve examples for LLM to convert query to SQL | String    |
