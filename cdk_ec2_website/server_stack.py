from pathlib import Path

from aws_cdk import CfnOutput, Duration, RemovalPolicy, Stack
from aws_cdk import aws_ec2 as ec2
from aws_cdk import aws_elasticloadbalancingv2 as elbv2
from aws_cdk import aws_elasticloadbalancingv2_targets as targets
from aws_cdk import aws_rds as rds
from constructs import Construct

USER_DATA_FILE = Path(__file__).resolve().parent.parent / "user_data" / "web_server.sh"


class ServerStack(Stack):
    """Two web servers (one per public subnet), a MySQL RDS instance in the
    private subnets, and an Application Load Balancer in front of the web servers."""

    def __init__(self, scope: Construct, construct_id: str, *, vpc: ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ---------- Security groups ----------
        web_sg = ec2.SecurityGroup(
            self,
            "WebServerSG",
            vpc=vpc,
            description="Web servers: HTTP from anywhere",
            allow_all_outbound=True,
        )
        web_sg.add_ingress_rule(ec2.Peer.any_ipv4(), ec2.Port.tcp(80), "HTTP from anywhere")

        db_sg = ec2.SecurityGroup(
            self,
            "DatabaseSG",
            vpc=vpc,
            description="RDS MySQL: 3306 from web servers only",
            allow_all_outbound=False,
        )
        db_sg.add_ingress_rule(
            ec2.Peer.security_group_id(web_sg.security_group_id),
            ec2.Port.tcp(3306),
            "MySQL from web server security group only",
        )

        # ---------- Web servers: one in each public subnet ----------
        user_data = ec2.UserData.for_linux()
        user_data.add_commands(USER_DATA_FILE.read_text())

        # Optional key pair for SSH, e.g.  cdk deploy --all -c key_name=vockey
        key_name = self.node.try_get_context("key_name")
        key_pair = ec2.KeyPair.from_key_pair_name(self, "KeyPair", key_name) if key_name else None

        self.web_servers = []
        for i, subnet in enumerate(vpc.public_subnets, start=1):
            instance = ec2.Instance(
                self,
                f"WebServer{i}",
                vpc=vpc,
                vpc_subnets=ec2.SubnetSelection(subnets=[subnet]),
                instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
                machine_image=ec2.MachineImage.latest_amazon_linux2023(),
                security_group=web_sg,
                user_data=user_data,
                key_pair=key_pair,
                associate_public_ip_address=True,
            )
            self.web_servers.append(instance)
            CfnOutput(self, f"WebServer{i}PublicIp", value=instance.instance_public_ip)
            CfnOutput(self, f"WebServer{i}Id", value=instance.instance_id)

        # ---------- RDS MySQL in the private subnets ----------
        subnet_group = rds.SubnetGroup(
            self,
            "DbSubnetGroup",
            vpc=vpc,
            description="All private subnets",
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED),
            removal_policy=RemovalPolicy.DESTROY,
        )

        database = rds.DatabaseInstance(
            self,
            "MySqlDatabase",
            engine=rds.DatabaseInstanceEngine.mysql(version=rds.MysqlEngineVersion.VER_8_0),
            instance_type=ec2.InstanceType.of(ec2.InstanceClass.T3, ec2.InstanceSize.MICRO),
            vpc=vpc,
            subnet_group=subnet_group,
            security_groups=[db_sg],
            credentials=rds.Credentials.from_generated_secret("admin"),  # password stored in Secrets Manager
            database_name="webappdb",
            allocated_storage=20,
            storage_encrypted=True,
            multi_az=False,
            publicly_accessible=False,
            backup_retention=Duration.days(0),
            delete_automated_backups=True,
            deletion_protection=False,
            removal_policy=RemovalPolicy.DESTROY,  # no final snapshot, so cdk destroy cleans up fully
        )

        # ---------- Application Load Balancer ----------
        alb = elbv2.ApplicationLoadBalancer(
            self,
            "WebAlb",
            vpc=vpc,
            internet_facing=True,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PUBLIC),
        )
        # Let the load balancer send traffic to the web servers on port 80
        alb.connections.allow_to(web_sg, ec2.Port.tcp(80), "ALB to web servers")

        listener = alb.add_listener("HttpListener", port=80, open=True)
        target_group = listener.add_targets(
            "WebServerTargets",
            port=80,
            protocol=elbv2.ApplicationProtocol.HTTP,
            targets=[targets.InstanceTarget(instance, 80) for instance in self.web_servers],
            health_check=elbv2.HealthCheck(
                path="/",
                healthy_http_codes="200",
                interval=Duration.seconds(15),
                healthy_threshold_count=2,
            ),
        )

        # ---------- Outputs ----------
        CfnOutput(self, "LoadBalancerDNS", value=f"http://{alb.load_balancer_dns_name}")
        CfnOutput(self, "TargetGroupArn", value=target_group.target_group_arn)
        CfnOutput(self, "DatabaseEndpoint", value=database.db_instance_endpoint_address)
        CfnOutput(self, "DatabaseSecretName", value=database.secret.secret_name)
        CfnOutput(self, "WebServerSecurityGroupId", value=web_sg.security_group_id)
        CfnOutput(self, "DatabaseSecurityGroupId", value=db_sg.security_group_id)
