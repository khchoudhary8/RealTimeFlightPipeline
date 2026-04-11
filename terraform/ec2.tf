# -----------------------------------------------------------------------------
# EC2 Instance (Self-Managed Docker Deployment)
# -----------------------------------------------------------------------------

# 1. Security Group for EC2
# Allows SSH (22) for administration, and ports for our apps
resource "aws_security_group" "ec2_sg" {
  name        = "${var.project_name}-ec2-sg"
  description = "Security group for flight pipeline EC2"
  vpc_id      = aws_vpc.main.id

  # SSH access (Restrict to your IP in production!)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Grafana Dashboard
  ingress {
    from_port   = 3001
    to_port     = 3001
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  
  # Streamlit App
  ingress {
    from_port   = 8501
    to_port     = 8501
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Ingestion API
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Prometheus
  ingress {
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Dagster
  ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Live Map Dashboard
  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # Kafka - Inbound from everywhere (for local prod testing) AND specifically from ECS Fargate
  ingress {
    from_port       = 9092
    to_port         = 9092
    protocol        = "tcp"
    cidr_blocks     = ["0.0.0.0/0"]
    security_groups = [aws_security_group.ecs_tasks_sg.id]
  }

  # Redis - Allow Fargate to cache
  ingress {
    from_port       = 6379   
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_tasks_sg.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-ec2-sg"
  }
}

# 2. Amazon Linux 2023 AMI lookup
data "aws_ami" "amazon_linux_2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

# 3. Create SSH Key Pair dynamically
resource "tls_private_key" "ec2_key" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "generated_key" {
  key_name   = "${var.project_name}-dynamic-key"
  public_key = tls_private_key.ec2_key.public_key_openssh
}

# 4. EC2 Instance Launch
resource "aws_instance" "pipeline_server" {
  ami           = data.aws_ami.amazon_linux_2023.id
  instance_type = "c7i-flex.large" # Upgraded to c7i-flex.large for 4GB RAM to support full 10-container stack.
  
  subnet_id                   = aws_subnet.public_1.id
  vpc_security_group_ids      = [aws_security_group.ec2_sg.id]
  associate_public_ip_address = true
  
  key_name = aws_key_pair.generated_key.key_name

  # The Boot Script! Automates Docker installation.
  user_data = <<-EOF
              #!/bin/bash
              sudo dnf update -y
              sudo dnf install -y docker git
              sudo systemctl enable docker
              sudo systemctl start docker
              sudo usermod -aG docker ec2-user

              # Install Docker Compose
              sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
              sudo chmod +x /usr/local/bin/docker-compose
              EOF

  tags = {
    Name = "${var.project_name}-server"
  }
}

# 5. Elastic IP for permanent address
resource "aws_eip" "pipeline_eip" {
  instance = aws_instance.pipeline_server.id
  domain   = "vpc"

  tags = {
    Name = "${var.project_name}-eip"
  }
}

output "ec2_public_ip" {
  description = "Permanent Public IP address of the EC2 Server"
  value       = aws_eip.pipeline_eip.public_ip
}

output "private_key" {
  description = "Private key for SSH access (Run 'terraform output -raw private_key > key.pem' to save it)"
  value       = tls_private_key.ec2_key.private_key_pem
  sensitive   = true
}
