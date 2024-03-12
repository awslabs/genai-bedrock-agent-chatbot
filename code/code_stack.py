import os
import os.path as path
import json
from aws_cdk import (
    CustomResource,
    custom_resources as cr,
    CfnResource,
    Duration,
    Size,
    Stack,
    Aws,
    RemovalPolicy,
    CfnOutput,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_kms as kms,
    aws_iam as iam,
    aws_s3 as s3,
    aws_glue as glue,
    aws_lambda as lambda_,
    aws_s3_deployment as s3deploy,
    aws_ecs_patterns as ecs_patterns,
    aws_opensearchserverless as opensearchserverless,
)
from aws_cdk.aws_lambda_python_alpha import PythonLayerVersion
from constructs import Construct
from aws_cdk.aws_ecr_assets import Platform
from cdk_nag import NagSuppressions
from bedrock_agent import BedrockAgent, ActionGroup, BedrockKnowledgeBase
from bedrock_agent import (
    OpenSearchServerlessStorageConfiguration,
    OpenSearchServerlessConfiguration,
    OpenSearchFieldMapping,
    DataSource,
    DataSourceConfiguration,
    S3Configuration,
)


class CodeStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        config = self.get_config()
        logging_context = config["logging"]
        kms_key = self.create_kms_key()
        agent_assets_bucket, athena_bucket = self.create_data_source_bucket(
            kms_key)
        self.upload_files_to_s3(agent_assets_bucket, athena_bucket, kms_key)

        self.lambda_runtime = lambda_.Runtime.PYTHON_3_12
        boto3_layer = self.create_lambda_layer("boto3_layer")
        opensearch_layer = self.create_lambda_layer("opensearch_layer")

        glue_database, glue_crawler = self.create_glue_database(athena_bucket, kms_key)
        agent_executor_lambda = self.create_lambda_function(
            agent_assets_bucket,
            athena_bucket,
            kms_key,
            glue_database,
            logging_context,
        )

        agent_resource_role = self.create_agent_execution_role(agent_assets_bucket)

        (cfn_collection, vector_field_name, vector_index_name, lambda_cr) = (
            self.create_opensearch_index(agent_resource_role, opensearch_layer)
        )

        knowledge_base, agent, invoke_lambda, agent_resource_role_arn = (
            self.create_bedrock_agent(
                agent_executor_lambda,
                agent_assets_bucket,
                boto3_layer,
                agent_resource_role,
                cfn_collection,
                vector_field_name,
                vector_index_name,
                lambda_cr,
            )
        )

        _ = self.create_update_lambda(
            glue_crawler, knowledge_base, agent, agent_resource_role_arn, boto3_layer
        )

        self.create_streamlit_app(logging_context, agent, invoke_lambda)

    def get_config(self):

        config = dict(self.node.try_get_context("config"))

        self.ASSETS_FOLDER_NAME = config["paths"]["assets_folder_name"]
        self.ATHENA_DATA_DESTINATION_PREFIX = config["paths"][
            "athena_data_destination_prefix"
        ]
        self.ATHENA_TABLE_DATA_PREFIX = config["paths"]["athena_table_data_prefix"]
        self.KNOWLEDGEBASE_DESTINATION_PREFIX = config["paths"][
            "knowledgebase_destination_prefix"
        ]
        self.KNOWLEDGEBASE_FILE_NAME = config["paths"]["knowledgebase_file_name"]
        self.AGENT_SCHEMA_DESTINATION_PREFIX = config["paths"][
            "agent_schema_destination_prefix"
        ]

        self.BEDROCK_AGENT_NAME = config["names"]["bedrock_agent_name"]
        self.BEDROCK_AGENT_ALIAS = config["names"]["bedrock_agent_alias"]
        self.STREAMLIT_INVOKE_LAMBDA_FUNCTION_NAME = config["names"][
            "streamlit_lambda_function_name"
        ]

        self.BEDROCK_AGENT_FM = config["models"]["bedrock_agent_foundation_model"]

        self.AGENT_INSTRUCTION = config["bedrock_instructions"]["agent_instruction"]
        self.ACTION_GROUP_DESCRIPTION = config["bedrock_instructions"][
            "action_group_description"
        ]
        self.KNOWLEDGEBASE_INSTRUCTION = config["bedrock_instructions"][
            "knowledgebase_instruction"
        ]

        self.FEWSHOT_EXAMPLES_PATH = config["paths"]["fewshot_examples_path"]
        self.LAMBDAS_SOURCE_FOLDER = config["paths"]["lambdas_source_folder"]
        self.LAYERS_SOURCE_FOLDER = config["paths"]["layers_source_folder"]

        return config

    def create_kms_key(self):
        # Creating new KMS key and confgiure it for S3 object encryption
        kms_key = kms.Key(
            self,
            "KMSKey",
            alias=f"alias/{Aws.STACK_NAME}/genai_key",
            enable_key_rotation=True,
            pending_window=Duration.days(7),
            removal_policy=RemovalPolicy.DESTROY,
        )
        kms_key.grant_encrypt_decrypt(
            iam.AnyPrincipal().with_conditions(
                {
                    "StringEquals": {
                        "kms:CallerAccount": f"{Aws.ACCOUNT_ID}",
                        "kms:ViaService": f"s3.{Aws.REGION}.amazonaws.com",
                    },
                }
            )
        )

        kms_key.grant_encrypt_decrypt(
            iam.ServicePrincipal(f"logs.{Aws.REGION}.amazonaws.com")
        )

        return kms_key

    def create_data_source_bucket(self, kms_key):
        # creating kendra source bucket
        agent_assets_bucket = s3.Bucket(
            self,
            "AgentAssetsSourceBaseBucket",
            bucket_name=f"{Aws.STACK_NAME}-agent-assets-bucket-{Aws.ACCOUNT_ID}",
            versioned=True,
            auto_delete_objects=True,
            removal_policy=RemovalPolicy.DESTROY,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=kms_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )
        NagSuppressions.add_resource_suppressions(
            agent_assets_bucket,
            suppressions=[
                {
                    "id": "AwsSolutions-S1",
                    "reason": "Demo app hence server access logs not enabled",
                }
            ],
        )
        CfnOutput(self, "AssetsBucket", value=agent_assets_bucket.bucket_name)

        # creating kendra source bucket
        athena_bucket = s3.Bucket(
            self,
            "AthenaSourceBucket",
            bucket_name=f"{Aws.STACK_NAME}-athena-bucket-{Aws.ACCOUNT_ID}",
            versioned=True,
            removal_policy=RemovalPolicy.DESTROY,
            auto_delete_objects=True,
            encryption=s3.BucketEncryption.KMS,
            encryption_key=kms_key,
            block_public_access=s3.BlockPublicAccess.BLOCK_ALL,
            enforce_ssl=True,
        )
        NagSuppressions.add_resource_suppressions(
            athena_bucket,
            suppressions=[
                {
                    "id": "AwsSolutions-S1",
                    "reason": "Demo app hence server access logs not enabled",
                }
            ],
        )
        CfnOutput(self, "AthenaBucket", value=athena_bucket.bucket_name)
        return agent_assets_bucket, athena_bucket

    def upload_files_to_s3(self, agent_assets_bucket, athena_bucket, kms_key):
        # Uploading files to S3 bucket
        s3deploy.BucketDeployment(
            self,
            "KnowledgeBaseDocumentDeployment",
            sources=[
                s3deploy.Source.asset(
                    path.join(
                        os.getcwd(),
                        self.ASSETS_FOLDER_NAME,
                        f"{self.KNOWLEDGEBASE_DESTINATION_PREFIX}/{self.KNOWLEDGEBASE_FILE_NAME}",
                    )
                )
            ],
            destination_bucket=agent_assets_bucket,
            destination_key_prefix=self.KNOWLEDGEBASE_DESTINATION_PREFIX,
            retain_on_delete=False,
        )

        s3deploy.BucketDeployment(
            self,
            "AthenaDataDeployment",
            sources=[
                s3deploy.Source.asset(
                    path.join(
                        os.getcwd(),
                        self.ASSETS_FOLDER_NAME,
                        self.ATHENA_DATA_DESTINATION_PREFIX,
                    )
                )
            ],
            destination_bucket=athena_bucket,
            retain_on_delete=False,
            destination_key_prefix=self.ATHENA_DATA_DESTINATION_PREFIX,
        ),

        s3deploy.BucketDeployment(
            self,
            "AgentAPISchema",
            sources=[
                s3deploy.Source.asset(
                    path.join(os.getcwd(), self.ASSETS_FOLDER_NAME, "agent_api_schema")
                )
            ],
            destination_bucket=agent_assets_bucket,
            retain_on_delete=False,
            destination_key_prefix=self.AGENT_SCHEMA_DESTINATION_PREFIX,
        )
        return

    def create_glue_database(self, athena_bucket, kms_key):
        # Create IAM role for Glue Crawlers
        glue_role = iam.Role(
            self,
            "GlueRole",
            assumed_by=iam.ServicePrincipal("glue.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSGlueServiceRole"
                )
            ],
        )
        athena_bucket.grant_read(glue_role)
        kms_key.grant_encrypt_decrypt(glue_role)
        glue_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                resources=["*"],
                actions=["logs:AssociateKmsKey"],
            )
        )
        # # Create Glue database
        glue_database = glue.CfnDatabase(
            self,
            "AgentTextToSQLDatabase",
            catalog_id=Aws.ACCOUNT_ID,
            database_input=glue.CfnDatabase.DatabaseInputProperty(
                name=f"{Aws.STACK_NAME}-text2sql-db"
            ),
        )

        cfn_security_configuration = glue.CfnSecurityConfiguration(
            self,
            "SecurityConfiguration",
            encryption_configuration=glue.CfnSecurityConfiguration.EncryptionConfigurationProperty(
                cloud_watch_encryption=glue.CfnSecurityConfiguration.CloudWatchEncryptionProperty(
                    cloud_watch_encryption_mode="SSE-KMS", kms_key_arn=kms_key.key_arn
                ),
                s3_encryptions=[
                    glue.CfnSecurityConfiguration.S3EncryptionProperty(
                        kms_key_arn=kms_key.key_arn, s3_encryption_mode="SSE-KMS"
                    )
                ],
            ),
            name=f"{Aws.STACK_NAME}-security-config",
        )

        cfn_crawler = glue.CfnCrawler(
            self,
            "text2sqlTableCrawler",
            role=glue_role.role_name,
            crawler_security_configuration=cfn_security_configuration.name,
            targets=glue.CfnCrawler.TargetsProperty(
                s3_targets=[
                    glue.CfnCrawler.S3TargetProperty(
                        path=f"s3://{athena_bucket.bucket_name}/{self.ATHENA_DATA_DESTINATION_PREFIX}/{self.ATHENA_TABLE_DATA_PREFIX}",
                    )
                ]
            ),
            database_name=glue_database.ref,
            description="Crawler job for EC2 pricing",
            name=f"{Aws.STACK_NAME}-text2sql-table-crawler",
        )
        NagSuppressions.add_resource_suppressions(
            cfn_crawler,
            suppressions=[
                {
                    "id": "AwsSolutions-GL1",
                    "reason": "Logs encryption enabled for the crawler. False positive warning",
                }
            ],
        )

        return glue_database, cfn_crawler

    def create_lambda_layer(self, layer_name):
        """
        create a Lambda layer with necessary dependencies.
        """
        # Create the Lambda layer
        layer = PythonLayerVersion(
            self,
            layer_name,
            entry=path.join(os.getcwd(), self.LAYERS_SOURCE_FOLDER, layer_name),
            compatible_runtimes=[self.lambda_runtime],
            compatible_architectures=[lambda_.Architecture.ARM_64],
            description="A layer new version of boto3",
            layer_version_name=layer_name,
        )

        return layer

    def create_lambda_function(
        self,
        agent_assets_bucket,
        athena_bucket,
        kms_key,
        glue_database,
        logging_context,
    ):

        ecr_image = lambda_.EcrImageCode.from_asset_image(
            directory=path.join(
                os.getcwd(), self.LAMBDAS_SOURCE_FOLDER, "action-lambda"
            ),
            platform=Platform.LINUX_AMD64,  # LINUX_AMD64, LINUX_ARM64
        )

        # Create IAM role for Lambda function
        lambda_role = iam.Role(
            self,
            "LambdaRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                # Add a managed policy for Amazon Athena AmazonBedrockFullAccess
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonAthenaFullAccess"
                ),
                # Add a managed policy for AmazonBedrockFullAccess
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "AmazonBedrockFullAccess"
                ),
            ],
        )
        lambda_function = lambda_.Function(
            self,
            "AgentActionLambdaFunction",
            function_name=f"{Aws.STACK_NAME}-agent-action-lambda-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            description="Lambda code for GenAI Chatbot",
            architecture=lambda_.Architecture.X86_64,  # X86_64, ARM_64
            handler=lambda_.Handler.FROM_IMAGE,
            runtime=lambda_.Runtime.FROM_IMAGE,
            code=ecr_image,
            environment={
                "ATHENA_BUCKET_NAME": athena_bucket.bucket_name,
                "TEXT2SQL_DATABASE": glue_database.ref,
                "LOG_LEVEL": logging_context["lambda_log_level"],
                "FEWSHOT_EXAMPLES_PATH": self.FEWSHOT_EXAMPLES_PATH,
            },
            environment_encryption=kms_key,
            role=lambda_role,
            timeout=Duration.minutes(15),
            memory_size=4096,
            ephemeral_storage_size=Size.mebibytes(4096),
        )

        lambda_function.add_permission(
            "BedrockLambdaInvokePermission",
            principal=iam.ServicePrincipal("bedrock.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_account=Aws.ACCOUNT_ID,
            source_arn=f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent/*",
        )

        agent_assets_bucket.grant_read_write(lambda_role)
        athena_bucket.grant_read_write(lambda_role)

        return lambda_function

    def create_agent_execution_role(self, agent_assets_bucket):
        agent_resource_role = iam.Role(
            self,
            "ChatBotBedrockAgentRole",
            # must be AmazonBedrockExecutionRoleForAgents_string
            role_name="AmazonBedrockExecutionRoleForAgents_chatbot",
            assumed_by=iam.ServicePrincipal("bedrock.amazonaws.com"),
        )
        policy_statements = [
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:InvokeModel"],
                resources=[
                    f"arn:aws:bedrock:{Aws.REGION}::foundation-model/anthropic.claude-v2",
                    f"arn:aws:bedrock:{Aws.REGION}::foundation-model/anthropic.claude-v2:1",
                    f"arn:aws:bedrock:{Aws.REGION}::foundation-model/anthropic.claude-instant-v1",
                    f"arn:aws:bedrock:{Aws.REGION}::foundation-model/amazon.titan-embed-text-v1",
                ],
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    f"arn:aws:s3:::{agent_assets_bucket.bucket_name}",
                    f"arn:aws:s3:::{agent_assets_bucket.bucket_name}/*",
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceAccount": f"{Aws.ACCOUNT_ID}",
                    },
                },
            ),
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["bedrock:Retrieve", "bedrock:RetrieveAndGenerate"],
                resources=[
                    f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:knowledge-base/*"
                ],
                conditions={
                    "StringEquals": {
                        "aws:ResourceAccount": f"{Aws.ACCOUNT_ID}",
                    },
                },
            ),
        ]

        for statement in policy_statements:
            agent_resource_role.add_to_policy(statement)

        return agent_resource_role

    def create_opensearch_index(self, agent_resource_role, opensearch_layer):
        vector_index_name = "bedrock-knowledgebase-index"
        vector_field_name = "bedrock-knowledge-base-default-vector"

        agent_resource_role_arn = agent_resource_role.role_arn

        create_index_lambda_execution_role = iam.Role(
            self,
            "CreateIndexExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for OpenSearch access",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        cfn_collection = opensearchserverless.CfnCollection(
            self,
            "ChatBotAgentCollection",
            name=f"chatbot-oscollect-{Aws.ACCOUNT_ID}",
            description="ChatBot Agent Collection",
            type="VECTORSEARCH",
        )

        cfn_collection_name = cfn_collection.name

        opensearch_policy_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["aoss:APIAccessAll"],
            resources=[
                f"arn:aws:aoss:{Aws.REGION}:{Aws.ACCOUNT_ID}:collection/{cfn_collection.attr_id}"
            ],
        )

        # Attach the custom policy to the role
        create_index_lambda_execution_role.add_to_policy(
            opensearch_policy_statement)

        # get the role arn
        create_index_lambda_execution_role_arn = (
            create_index_lambda_execution_role.role_arn
        )

        opensearch_api_policy_statement = iam.PolicyStatement(
            effect=iam.Effect.ALLOW,
            actions=["aoss:APIAccessAll"],
            resources=[
                f"arn:aws:aoss:{Aws.REGION}:{Aws.ACCOUNT_ID}:collection/{cfn_collection.attr_id}"
            ],
        )

        agent_resource_role.add_to_policy(opensearch_api_policy_statement)

        policy_json = {
            "Rules": [
                {
                    "ResourceType": "collection",
                    "Resource": [f"collection/{cfn_collection_name}"],
                }
            ],
            "AWSOwnedKey": True,
        }

        json_dump = json.dumps(policy_json)

        encryption_policy = CfnResource(
            self,
            "EncryptionPolicy",
            type="AWS::OpenSearchServerless::SecurityPolicy",
            properties={
                "Name": "chatbot-index-encryption-policy",
                "Type": "encryption",
                "Description": "Encryption policy for Bedrock collection.",
                "Policy": json_dump,
            },
        )

        policy_json = [
            {
                "Rules": [
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{cfn_collection_name}"],
                    },
                    {
                        "ResourceType": "dashboard",
                        "Resource": [f"collection/{cfn_collection_name}"],
                    },
                ],
                "AllowFromPublic": True,
            }
        ]
        json_dump = json.dumps(policy_json)

        network_policy = CfnResource(
            self,
            "NetworkPolicy",
            type="AWS::OpenSearchServerless::SecurityPolicy",
            properties={
                "Name": "chatbot-index-network-policy",
                "Type": "network",
                "Description": "Network policy for Bedrock collection",
                "Policy": json_dump,
            },
        )

        policy_json = [
            {
                "Description": "Access for cfn user",
                "Rules": [
                    {
                        "ResourceType": "index",
                        "Resource": ["index/*/*"],
                        "Permission": ["aoss:*"],
                    },
                    {
                        "ResourceType": "collection",
                        "Resource": [f"collection/{cfn_collection_name}"],
                        "Permission": ["aoss:*"],
                    },
                ],
                "Principal": [
                    agent_resource_role_arn,
                    create_index_lambda_execution_role_arn,
                ],
            }
        ]

        json_dump = json.dumps(policy_json)

        data_policy = CfnResource(
            self,
            "DataPolicy",
            type="AWS::OpenSearchServerless::AccessPolicy",
            properties={
                "Name": "chatbot-index-data-policy",
                "Type": "data",
                "Description": "Data policy for Bedrock collection.",
                "Policy": json_dump,
            },
        )

        cfn_collection.add_dependency(network_policy)
        cfn_collection.add_dependency(encryption_policy)
        cfn_collection.add_dependency(data_policy)

        self.create_index_lambda = lambda_.Function(
            self,
            "CreateIndexLambda",
            function_name=f"{Aws.STACK_NAME}-create-index-lambda-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            runtime=self.lambda_runtime,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset(
                path.join(
                    os.getcwd(), self.LAMBDAS_SOURCE_FOLDER, "create-index-lambda"
                )
            ),
            layers=[opensearch_layer],
            environment={
                "REGION_NAME": Aws.REGION,
                "COLLECTION_HOST": cfn_collection.attr_collection_endpoint,
                "VECTOR_INDEX_NAME": vector_index_name,
                "VECTOR_FIELD_NAME": vector_field_name,
            },
            role=create_index_lambda_execution_role,
            timeout=Duration.minutes(15),
            tracing=lambda_.Tracing.ACTIVE,
        )

        lambda_provider = cr.Provider(
            self,
            "LambdaCreateIndexCustomProvider",
            on_event_handler=self.create_index_lambda,
        )

        lambda_cr = CustomResource(
            self,
            "LambdaCreateIndexCustomResource",
            service_token=lambda_provider.service_token,
        )

        return cfn_collection, vector_field_name, vector_index_name, lambda_cr

    def create_bedrock_agent(
        self,
        agent_executor_lambda,
        agent_assets_bucket,
        boto3_layer,
        agent_resource_role,
        cfn_collection,
        vector_field_name,
        vector_index_name,
        lambda_cr,
    ):
        """
        Create a bedrock agent
        """
        s3_bucket_name = agent_assets_bucket.bucket_name
        s3_object_key = f"{self.AGENT_SCHEMA_DESTINATION_PREFIX}/artifacts_schema.json"

        kb_name = "BedrockKnowledgeBase"
        data_source_name = "BedrockKnowledgeBaseSource"
        text_field = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"
        storage_configuration_type = "OPENSEARCH_SERVERLESS"
        data_source_type = "S3"
        data_source_bucket_arn = f"arn:aws:s3:::{agent_assets_bucket.bucket_name}"
        agent_resource_role_arn = agent_resource_role.role_arn
        knowledge_base = BedrockKnowledgeBase(
            self,
            "BedrockOpenSearchKnowledgeBase",
            name=kb_name,
            description="Use this for returning descriptive answers and instructions directly from AWS EC2 Documentation. Use to answer qualitative/guidance questions such as 'how do I',  general instructions and guidelines.",
            role_arn=agent_resource_role_arn,
            storage_configuration=OpenSearchServerlessStorageConfiguration(
                opensearch_serverless_configuration=OpenSearchServerlessConfiguration(
                    collection_arn=cfn_collection.attr_arn,
                    field_mapping=OpenSearchFieldMapping(
                        metadata_field=metadata_field,
                        text_field=text_field,
                        vector_field=vector_field_name,
                    ),
                    vector_index_name=vector_index_name,
                ),
                type=storage_configuration_type,
            ),
            data_source=DataSource(
                name=data_source_name,
                data_source_configuration=DataSourceConfiguration(
                    s3_configuration=S3Configuration(
                        bucket_arn=data_source_bucket_arn,
                        inclusion_prefixes=[
                            f"{self.KNOWLEDGEBASE_DESTINATION_PREFIX}/"
                        ],
                    ),
                    type=data_source_type,
                ),
            ),
        )

        for child in knowledge_base.node.children:
            if isinstance(child, CustomResource):
                cfn_resource = child
                break

        cfn_resource.node.add_dependency(cfn_collection)
        cfn_resource.node.add_dependency(lambda_cr)

        action_group = ActionGroup(
            action_group_name="ChatBotBedrockAgentActionGroup",
            description=self.ACTION_GROUP_DESCRIPTION,
            action_group_executor=agent_executor_lambda.function_arn,
            s3_bucket_name=s3_bucket_name,
            s3_object_key=s3_object_key,
        )

        agent = BedrockAgent(
            self,
            "ChatbotBedrockAgent",
            agent_name=self.BEDROCK_AGENT_NAME,
            description="Bedrock Chatbot Agent",
            instruction=self.AGENT_INSTRUCTION,
            foundation_model=self.BEDROCK_AGENT_FM,
            agent_resource_role_arn=agent_resource_role_arn,
            action_groups=[action_group],
            idle_session_ttl_in_seconds=3600,
            knowledge_base_associations=[
                {
                    "knowledgeBaseName": kb_name,
                    "instruction": self.KNOWLEDGEBASE_INSTRUCTION,
                }
            ],
        )
        for child in agent.node.children:
            if isinstance(child, CustomResource):
                cfn_agent_resource = child
                break
        cfn_agent_resource.node.add_dependency(knowledge_base)

        invoke_lambda_role = iam.Role(
            self,
            "InvokeLambdaExecutionRole",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            description="Role for Lambda to access Bedrock agents and S3",
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                )
            ],
        )

        # Bedrock agent permissions
        invoke_lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=[
                    "bedrock:ListAgents",
                    "bedrock:ListAgentAliases",
                    "bedrock:InvokeAgent",
                ],
                resources=[
                    f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent/{agent.agent_id}",
                    f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent-alias/{agent.agent_id}/*",
                ],
            )
        )

        # S3 permissions
        invoke_lambda_role.add_to_policy(
            iam.PolicyStatement(
                effect=iam.Effect.ALLOW,
                actions=["s3:GetObject", "s3:ListBucket"],
                resources=[
                    f"arn:aws:s3:::{agent_assets_bucket.bucket_name}",
                    f"arn:aws:s3:::{agent_assets_bucket.bucket_name}/*",
                ],
            )
        )

        self.invoke_lambda = lambda_.Function(
            self,
            self.STREAMLIT_INVOKE_LAMBDA_FUNCTION_NAME,
            function_name=f"{Aws.STACK_NAME}-{self.STREAMLIT_INVOKE_LAMBDA_FUNCTION_NAME}-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            runtime=self.lambda_runtime,
            handler="index.lambda_handler",
            code=lambda_.Code.from_asset(
                path.join(os.getcwd(), self.LAMBDAS_SOURCE_FOLDER, "invoke-lambda")
            ),
            layers=[boto3_layer],
            environment={"AGENT_ID": agent.agent_id, "REGION_NAME": Aws.REGION},
            role=invoke_lambda_role,
            timeout=Duration.minutes(15),
            tracing=lambda_.Tracing.ACTIVE,
        )
        CfnOutput(
            self,
            "StreamlitInvokeLambdaFunction",
            value=self.invoke_lambda.function_name,
        )

        return knowledge_base, agent, self.invoke_lambda, agent_resource_role_arn

    def create_update_lambda(
        self,
        glue_crawler,
        knowledge_base,
        bedrock_agent,
        agent_resource_role_arn,
        boto3_layer,
    ):

        # Create IAM role for the update lambda
        lambda_role = iam.Role(
            self,
            "LambdaRole_update_resources",
            assumed_by=iam.ServicePrincipal("lambda.amazonaws.com"),
            managed_policies=[
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSLambdaBasicExecutionRole"
                ),
                iam.ManagedPolicy.from_aws_managed_policy_name(
                    "service-role/AWSGlueServiceRole"
                ),
            ],
        )

        # Define the policy statement - glue crawler
        glue_crawer_policy_statement = iam.PolicyStatement(
            actions=["glue:GetCrawler", "glue:StartCrawler"],
            resources=[f"arn:aws:glue:{Aws.REGION}::crawler/{glue_crawler.name}"],
            effect=iam.Effect.ALLOW,
        )

        # Create the policy
        glue_crawer_policy = iam.Policy(
            self,
            "TriggerGlueCrawlerPolicy",
            policy_name="allow_trigger_glue_crawler_policy",
            statements=[glue_crawer_policy_statement],
        )

        # Define the policy statement
        bedrock_policy_statement = iam.PolicyStatement(
            actions=[
                "bedrock:StartIngestionJob",
                "bedrock:UpdateAgentKnowledgeBase",
                "bedrock:GetAgentAlias",
                "bedrock:UpdateKnowledgeBase",
                "bedrock:UpdateAgent",
                "bedrock:GetIngestionJob",
                "bedrock:CreateAgentAlias",
                "bedrock:UpdateAgentAlias",
                "bedrock:GetAgent",
                "bedrock:PrepareAgent",
                "bedrock:DeleteAgentAlias",
                "bedrock:DeleteAgent",
                "bedrock:ListAgentAliases",
            ],
            resources=[
                f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent/*",
                f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:agent-alias/*",
                f"arn:aws:bedrock:{Aws.REGION}:{Aws.ACCOUNT_ID}:knowledge-base/*",
            ],
            effect=iam.Effect.ALLOW,
        )

        # Create the policy
        update_agent_kb_policy = iam.Policy(
            self,
            "BedrockAgent_KB_Update_Policy",
            policy_name="allow_update_bedrock_agent_kb_policy",
            statements=[bedrock_policy_statement],
        )

        lambda_role.attach_inline_policy(glue_crawer_policy)
        lambda_role.attach_inline_policy(update_agent_kb_policy)

        # create lambda function to trigger crawler, create bedrock agent alias, knowledgebase data sync
        lambda_function_update = lambda_.Function(
            self,
            "LambdaFunction_update_resources",
            function_name=f"{Aws.STACK_NAME}-update-lambda-{Aws.ACCOUNT_ID}-{Aws.REGION}",
            description="Lambda code to trigger crawler, create bedrock agent alias, knowledgebase data sync",
            architecture=lambda_.Architecture.ARM_64,
            handler="lambda_handler.lambda_handler",
            runtime=self.lambda_runtime,
            code=lambda_.Code.from_asset(
                path.join(os.getcwd(), self.LAMBDAS_SOURCE_FOLDER, "update-lambda")
            ),
            environment={
                "GLUE_CRAWLER_NAME": glue_crawler.name,
                "KNOWLEDGEBASE_ID": knowledge_base.knowledge_base_id,
                "KNOWLEDGEBASE_DATASOURCE_ID": knowledge_base.data_source_id,
                "BEDROCK_AGENT_ID": bedrock_agent.agent_id,
                "BEDROCK_AGENT_NAME": self.BEDROCK_AGENT_NAME,
                "BEDROCK_AGENT_ALIAS": self.BEDROCK_AGENT_ALIAS,
                "BEDROCK_AGENT_RESOURCE_ROLE_ARN": agent_resource_role_arn,
                "LOG_LEVEL": "info",
            },
            role=lambda_role,
            timeout=Duration.minutes(15),
            memory_size=1024,
            layers=[boto3_layer],
        )

        lambda_provider = cr.Provider(
            self,
            "LambdaUpdateResourcesCustomProvider",
            on_event_handler=lambda_function_update,
        )

        _ = CustomResource(
            self,
            "LambdaUpdateResourcesCustomResource",
            service_token=lambda_provider.service_token,
        )

        return lambda_function_update

    def create_streamlit_app(self, logging_context, agent, invoke_lambda):
        # Create a VPC
        vpc = ec2.Vpc(
            self, "ChatBotDemoVPC", max_azs=2, vpc_name=f"{Aws.STACK_NAME}-vpc"
        )
        NagSuppressions.add_resource_suppressions(
            vpc,
            suppressions=[
                {"id": "AwsSolutions-VPC7", "reason": "VPC used for hosting demo app"}
            ],
        )

        # Create ECS cluster
        cluster = ecs.Cluster(
            self,
            "ChatBotDemoCluster",
            cluster_name=f"{Aws.STACK_NAME}-ecs-cluster",
            container_insights=True,
            vpc=vpc,
        )

        # Build Dockerfile from local folder and push to ECR
        image = ecs.ContainerImage.from_asset(
            path.join(os.getcwd(), "code", "streamlit-app"),
            platform=Platform.LINUX_ARM64,
        )

        #  Create Fargate service
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self,
            "ChatBotService",
            cluster=cluster,
            cpu=2048,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=image,
                container_port=8501,
                environment={
                    "LAMBDA_FUNCTION_NAME": invoke_lambda.function_name,
                    "LOG_LEVEL": logging_context["streamlit_log_level"],
                    "AGENT_ID": agent.agent_id,
                },
            ),
            service_name=f"{Aws.STACK_NAME}-chatbot-service",
            memory_limit_mib=4096,
            public_load_balancer=True,
            platform_version=ecs.FargatePlatformVersion.LATEST,
            runtime_platform=ecs.RuntimePlatform(
                operating_system_family=ecs.OperatingSystemFamily.LINUX,
                cpu_architecture=ecs.CpuArchitecture.ARM64,
            ),
        )
        NagSuppressions.add_resource_suppressions(
            fargate_service,
            suppressions=[
                {"id": "AwsSolutions-ELB2", "reason": "LB used for hosting demo app"}
            ],
            apply_to_children=True,
        )
        NagSuppressions.add_resource_suppressions(
            fargate_service,
            suppressions=[
                {
                    "id": "AwsSolutions-EC23",
                    "reason": "Enabling Chatbot access in HTTP port",
                }
            ],
            apply_to_children=True,
        )
        NagSuppressions.add_resource_suppressions(
            fargate_service,
            suppressions=[
                {
                    "id": "AwsSolutions-ECS2",
                    "reason": "Environment variables needed for accessing lambda",
                }
            ],
            apply_to_children=True,
        )

        # Add policies to task role
        invoke_lambda.grant_invoke(fargate_service.task_definition.task_role)

        # Setup task auto-scaling
        scaling = fargate_service.service.auto_scale_task_count(max_capacity=3)
        scaling.scale_on_cpu_utilization(
            "CpuScaling",
            target_utilization_percent=50,
            scale_in_cooldown=Duration.seconds(60),
            scale_out_cooldown=Duration.seconds(60),
        )
        return fargate_service
