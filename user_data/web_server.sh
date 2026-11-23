#!/bin/bash
# Web server user data.
# Replace this with the User Data script from your CloudFormation assignment if you prefer.
dnf update -y
dnf install -y httpd

# Look up instance details with IMDSv2 (required on Amazon Linux 2023)
TOKEN=$(curl -s -X PUT "http://169.254.169.254/latest/api/token" -H "X-aws-ec2-metadata-token-ttl-seconds: 21600")
INSTANCE_ID=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/instance-id)
AZ=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/placement/availability-zone)
PRIVATE_IP=$(curl -s -H "X-aws-ec2-metadata-token: $TOKEN" http://169.254.169.254/latest/meta-data/local-ipv4)

cat > /var/www/html/index.html <<EOF
<html>
  <head><title>CDK Website on EC2</title></head>
  <body>
    <h1>Hello from the CDK web server!</h1>
    <p>Instance ID: ${INSTANCE_ID}</p>
    <p>Availability Zone: ${AZ}</p>
    <p>Private IP: ${PRIVATE_IP}</p>
  </body>
</html>
EOF

systemctl enable httpd
systemctl start httpd
