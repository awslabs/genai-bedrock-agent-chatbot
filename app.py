#!/usr/bin/env python3
import os
import aws_cdk as cdk
import cdk_nag
import json

from code.code_stack import CodeStack
from cdk_nag import NagSuppressions
from aws_cdk import Aspects

app = cdk.App()

with open("cdk.json", encoding="utf-8") as f:
    data = json.load(f)
config = data["context"]["config"]
stack_name = config["names"]["stack_name"]

appStack = CodeStack(
    app,
    stack_name,
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"), region=os.getenv("CDK_DEFAULT_REGION")
    ),
)
Aspects.of(appStack).add(cdk_nag.AwsSolutionsChecks())

NagSuppressions.add_stack_suppressions(
    appStack,
    suppressions=[
        {"id": "AwsSolutions-IAM5", "reason": "Dynamic resource creation"},
        {
            "id": "AwsSolutions-IAM4",
            "reason": "Managed policies are used for log stream access",
        },
        {
            "id": "AwsSolutions-L1",
            "reason": "Lambda auto-created by CDK library construct",
        },
    ],
)

app.synth()
