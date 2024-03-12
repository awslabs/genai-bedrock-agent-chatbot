# Invoke Bedrock Agent

## Introduction

This lambda is to invoke the Bedrock Agent, to respond to user's query from the Frondend (streamlit UI).

## Component Details
#### Prerequisites
- Run the 'update-lambda' successfully.
    - Trigger AWS Glue Crawler to create the AWS Glue database succuessfully
    - Data Source Sync between Amazon Bedrock Knowledge base and Opensearch serverless vector index
    - Associate the Knowledgebase with the Bedrock Agent
    - Prepare Amazon Bedrock Agent
    - Create Alias for Amazon Bedrock Agent

#### Technology stack
- [AWS Lambda](https://aws.amazon.com/lambda/)
- [Amazon Bedrock](https://aws.amazon.com/bedrock/)

#### Package Details

| Files                                                                    | Description                                                                                                                                                                                                                          |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [index.py](index.py)                                         | Python file  containing the `lambda_handler` function that acts as the starting point for Amazon Lambda invocation                                                                                                                           |

#### Input

The Amazon Lambda is part of the Action Group associated the Amazon Bedrock Agent, the event is sent by the Amazon Bedrock Agent when the user asks a question.

```json
{
    "query": "user query from the frontend",
    "session_id": "session id that governs chat sessions"
}
```

#### Output

This lambda generats the following output

```json
{
    "answer": "response from the Amazon Bedrock Agent",
    "source": "source file link leverage by Amazon Bedrock Agent to give the answer"}
}
```

#### Environmental Variables

| Field                          | Description                                                                              | Data Type |
| ------------------------------ | ---------------------------------------------------------------------------------------- | --------- |
| `AGENT_ID`         | Set the Amazon Bedrock Agent id                                   | String    |
| `REGION_NAME` | Sets the AWS region                            | String    |
