# Create OpenSearch Serverless Index

## Introduction

This lambda is to create OpenSearch Collection with 'Vectorsearch' type.
This collection serves as the 'Data Source' for Amazon Bedrock Knowledge base.

## Component Details
#### Prerequisites
- boto3==1.34.57

#### Technology stack
- [Amazon Lambda](https://aws.amazon.com/lambda/)
- [Amazon OpenSearch Service](https://aws.amazon.com/opensearch-service/)

#### Package Details

| Files                                                                    | Description                                                                                                                                                                                                                          |
| ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [index.py](index.py)                                         | Python file  containing the `lambda_handler` function that acts as the starting point for Amazon Lambda invocation                                                                                                                           |
| [cfnresponse.py](cfnresponse.py)                       | Python file that is designed for use within AWS Lambda functions that are part of AWS CloudFormation custom resources. The script includes a function named send that constructs and sends a response back to a CloudFormation stack to indicate the success or failure of the Lambda function execution                                                                                                                                                                     |

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

This lambda generats the following output

```json
{
    "statusCode": status_code,
    "body": status_body
}
```

#### Environmental Variables

| Field                          | Description                                                                              | Data Type |
| ------------------------------ | ---------------------------------------------------------------------------------------- | --------- |
| `COLLECTION_HOST`         | Set the Amazon OpenSearch connection host                                  | String    |
| `VECTOR_INDEX_NAME` | Sets vector index name such as `bedrock-knowledgebase-index`                           | String    |
| `VECTOR_FIELD_NAME`         | Set vector field name such as `bedrock-knowledge-base-default-vector`                                   | String    |
| `REGION_NAME` | Sets the AWS region                            | String    |
