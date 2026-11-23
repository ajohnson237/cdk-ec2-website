from aws_cdk import CfnOutput, Stack
from aws_cdk import aws_ec2 as ec2
from constructs import Construct


class NetworkStack(Stack):
    """VPC with one public and one private subnet in each of two AZs."""

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        self.vpc = ec2.Vpc(
            self,
            "WebsiteVpc",
            ip_addresses=ec2.IpAddresses.cidr("10.0.0.0/16"),
            max_azs=2,  # two availability zones
            nat_gateways=0,  # no NAT needed (RDS needs no internet); keeps the bill down
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    name="Public",
                    subnet_type=ec2.SubnetType.PUBLIC,
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    name="Private",
                    subnet_type=ec2.SubnetType.PRIVATE_ISOLATED,
                    cidr_mask=24,
                ),
            ],
        )

        CfnOutput(self, "VpcId", value=self.vpc.vpc_id)
        for i, subnet in enumerate(self.vpc.public_subnets, start=1):
            CfnOutput(self, f"PublicSubnet{i}", value=f"{subnet.subnet_id} ({subnet.availability_zone})")
        for i, subnet in enumerate(self.vpc.isolated_subnets, start=1):
            CfnOutput(self, f"PrivateSubnet{i}", value=f"{subnet.subnet_id} ({subnet.availability_zone})")
