# CDK Lab: Website on EC2 Instances

AWS CDK (Python) project with two stacks:

| Stack | Resources |
|---|---|
| **NetworkStack** | VPC `10.0.0.0/16` across 2 AZs: 1 public + 1 private subnet in each AZ, Internet Gateway |
| **ServerStack** | 2 web servers (EC2, Amazon Linux 2023, Apache), one in each public subnet · RDS MySQL 8.0 using both private subnets as its subnet group · Application Load Balancer in front of the web servers |

**Security groups**
- `WebServerSG`: inbound TCP **80** from `0.0.0.0/0`
- `DatabaseSG`: inbound TCP **3306** from `WebServerSG` only
- ALB security group: inbound TCP 80 from anywhere (created by CDK)

The web server user data is in `user_data/web_server.sh`. Swap in the script from your CloudFormation assignment if you prefer.

## Project layout

```
app.py                         # CDK app entry point, creates both stacks
cdk_ec2_website/network_stack.py
cdk_ec2_website/server_stack.py
user_data/web_server.sh        # EC2 user data (installs Apache + index page)
```

## Prerequisites

- AWS CLI configured (`aws configure`, or Learner Lab credentials in `~/.aws/credentials`)
- Node.js and the CDK CLI: `npm install -g aws-cdk`
- Python 3.9+

## Deploy

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cdk bootstrap                      # once per account/region
cdk synth
cdk deploy --all                   # approve the IAM/security-group changes when prompted
# optional SSH key:  cdk deploy --all -c key_name=vockey
```

RDS takes about 5 to 10 minutes to create. When the deploy finishes, the stack outputs show the load balancer URL, web server IPs, and the DB endpoint.

## Verify

```bash
# Stack outputs
aws cloudformation describe-stacks --stack-name ServerStack \
  --query "Stacks[0].Outputs" --output table

# Subnets: 2 public + 2 private across 2 AZs
aws ec2 describe-subnets --filters "Name=vpc-id,Values=<VpcId>" \
  --query "Subnets[].{Id:SubnetId,AZ:AvailabilityZone,CIDR:CidrBlock,Public:MapPublicIpOnLaunch}" --output table

# Web servers
aws ec2 describe-instances --filters "Name=tag:aws:cloudformation:stack-name,Values=ServerStack" \
  --query "Reservations[].Instances[].{Id:InstanceId,AZ:Placement.AvailabilityZone,Subnet:SubnetId,PublicIp:PublicIpAddress,State:State.Name}" --output table

# Security group rules
aws ec2 describe-security-groups --group-ids <WebServerSecurityGroupId> <DatabaseSecurityGroupId> \
  --query "SecurityGroups[].{Name:GroupName,Ingress:IpPermissions}" --output json

# RDS instance and its subnet group
aws rds describe-db-instances \
  --query "DBInstances[].{Id:DBInstanceIdentifier,Engine:Engine,Version:EngineVersion,Status:DBInstanceStatus,Public:PubliclyAccessible,Subnets:DBSubnetGroup.Subnets[].SubnetIdentifier}" --output json

# Load balancer target health (both should be "healthy")
aws elbv2 describe-target-health --target-group-arn <TargetGroupArn> --output table

# Load balancing: run several times; the Instance ID / AZ should alternate
for i in 1 2 3 4 5 6; do curl -s http://<LoadBalancerDNS> | grep -E "Instance ID|Availability Zone"; done
```

You can also open the `LoadBalancerDNS` URL in a browser and refresh. The page alternates between the two servers.

## Clean up (avoid charges)

```bash
cdk destroy --all
```

RDS is created with `DeletionPolicy: Delete`, no deletion protection, and no final snapshot, so `cdk destroy` removes everything. Confirm in the console (EC2, RDS, Load Balancers, VPC) that nothing is left.

## Push to GitHub

```bash
git init
git add .
git commit -m "CDK lab: network and server stacks"
git branch -M main
git remote add origin https://github.com/<your-username>/cdk-ec2-website.git
git push -u origin main
```

Make the repository **public**, or add your instructor as a collaborator.
