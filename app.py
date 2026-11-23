#!/usr/bin/env python3
import os

import aws_cdk as cdk

from cdk_ec2_website.network_stack import NetworkStack
from cdk_ec2_website.server_stack import ServerStack

app = cdk.App()

# Uses the account/region from your AWS CLI profile (aws configure / env vars).
env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"),
    region=os.getenv("CDK_DEFAULT_REGION", "us-east-1"),
)

network = NetworkStack(app, "NetworkStack", env=env)

ServerStack(
    app,
    "ServerStack",
    vpc=network.vpc,
    env=env,
)
app.synth()
