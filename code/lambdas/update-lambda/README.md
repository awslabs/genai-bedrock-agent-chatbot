# Update Lambda

## Introduction

This Lambda is triggered after the stack is deployed, it is to conduct the following tasks:

1. Trigger AWS Glue Crawler
2. Data Source Sync
3. Normalize the Amazon Bedrock Agent reasoning configuration for models that
   require it
4. Prepare Amazon Bedrock Agent
5. Create Alias for Amazon Bedrock Agent
6. Remove Agent resources on stack deletion

Step 3 runs before step 4 deliberately. Bedrock Agents injects a default
orchestration reasoning configuration of
`{"thinking": {"type": "enabled", "budget_tokens": N}}`, which newer models
reject at invoke time in favour of `"thinking.type.adaptive"`. The correction
must be applied before the agent is prepared, because the agent version captured
by the alias in step 5 is a snapshot — an alias pointing at a version created
beforehand would keep serving the rejected configuration.

## Component Details

#### Prerequisites

Provided by the shared boto3 Lambda layer (`code/layers/boto3_layer`):

- boto3==1.42.56

#### Technology stack

- [AWS Lambda](https://aws.amazon.com/lambda/)

#### Package Details

| Files                                                                    | Description                                                                                                                                                                                                                                                                                              |
| ------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [create_agent_alias.py](create_agent_alias.py)                           | Python file that creates Amazon Bedrock Agent Alias after it's prepared database                                                                                                                                                                                                                          |
| [fix_agent_thinking_config.py](fix_agent_thinking_config.py)             | Python file that replaces the agent's default orchestration reasoning configuration with the adaptive form, for foundation models that reject `"thinking.type.enabled"`                                                                                                                                   |
| [prepare_agent.py](prepare_agent.py)                                     | Python file that prepares Amazon Bedrock Agent after it's deployed via AWS CDK.                                                                                                                                                                                                                          |
| [trigger_data_source_sync.py](trigger_data_source_sync.py)               | Python file that triggers the data source sync between Amazon Bedrock Knowledge base and Amazon Opensearch Serverless vector index                                                                                                                                                                       |
| [trigger_glue_crawler.py](trigger_glue_crawler.py)                       | Python file that trigger AWS Glue crawler after it is deployed                                                                                                                                                                                                                                           |
| [lambda_handler.py](lambda_handler.py)                                   | Python file that contains lambda handler to trigger the actions listed above                                                                                                                                                                                                                             |
| [cfnresponse.py](cfnresponse.py)                                         | Python file that is designed for use within AWS Lambda functions that are part of AWS CloudFormation custom resources. The script includes a function named send that constructs and sends a response back to a CloudFormation stack to indicate the success or failure of the Lambda function execution |
| [connections.py](connections.py)                                         | Python file with `Connections` class for establishing connections with external dependencies of the lambda                                                                                                                                                                                               |

Agent prompt templates live in [assets/agent_prompts](../../../assets/agent_prompts/), outside this lambda.

#### Input

AWS CloudFormation invokes this Lambda function asynchronously with an event that includes a callback URL. The following example event is from [here](https://docs.aws.amazon.com/lambda/latest/dg/services-cloudformation.html).

```json
{
  "RequestType": "Create",
  "ServiceToken": "arn:aws:lambda:us-east-1:123456789012:function:lambda-error-processor-primer-14ROR2T3JKU66",
  "ResponseURL": "https://cloudformation-custom-resource-response-useast1.s3-us-east-1.amazonaws.com/***",
  "StackId": "arn:aws:cloudformation:us-east-1:123456789012:stack/lambda-error-processor/1134083a-2608-1e91-9897-022501a2c456",
  "RequestId": "5d478078-13e9-baf0-464a-7ef285ecc786",
  "LogicalResourceId": "primerinvoke",
  "ResourceType": "AWS::CloudFormation::CustomResource",
  "ResourceProperties": {
    "ServiceToken": "arn:aws:lambda:us-east-1:123456789012:function:lambda-error-processor-primer-14ROR2T3JKU66",
    "FunctionName": "lambda-error-processor-randomerror-ZWUC391MQAJK"
  }
}
```

#### Output

This lambda generates the following output

```json
{
    "statusCode": status_code,
    "body": status_body
}
```

| Field        | Description                                          | Data Type |
| ------------ | ---------------------------------------------------- | --------- |
| `statusCode` | `200` indicates success; `500` indicates failure     | Number    |
| `body`       | Denotes the message associated with `the statusCode` | String    |

#### Environmental Variables

| Field                             | Description                                           | Data Type |
| --------------------------------- | ----------------------------------------------------- | --------- |
| `GLUE_CRAWLER_NAME`               | Set the AWS Glue crawler name                         | String    |
| `KNOWLEDGEBASE_ID`                | Sets the Amazon Bedrock Knowledge base id             | String    |
| `KNOWLEDGEBASE_DATASOURCE_ID`     | Sets the Amazon Bedrock Knowledge base data source id | String    |
| `BEDROCK_AGENT_ID`                | Sets the Amazon Bedrock Agent id                      | String    |
| `BEDROCK_AGENT_NAME`              | Sets the Amazon Bedrock Agent name                    | String    |
| `BEDROCK_AGENT_ALIAS`             | Sets the Amazon Bedrock Agent alias                   | String    |
| `BEDROCK_AGENT_RESOURCE_ROLE_ARN` | Sets the Amazon Bedrock Agent resource role arn       | String    |
| `LOG_LEVEL`                       | Sets the log level                                    | String    |
