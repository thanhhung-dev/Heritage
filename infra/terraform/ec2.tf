# Tạo SSH Key Pair tự động
resource "tls_private_key" "ssh" {
  algorithm = "RSA"
  rsa_bits  = 4096
}

resource "aws_key_pair" "generated" {
  key_name   = "${var.project_name}-${var.environment}-key"
  public_key = tls_private_key.ssh.public_key_openssh
}

# Lưu chìa khóa private ra file .pem để SSH
resource "local_file" "private_key" {
  content         = tls_private_key.ssh.private_key_pem
  filename        = "${path.module}/heritagegraph-staging-key.pem"
  file_permission = "0400"
}

# Security Group mở port 22 (SSH) và port 1818
resource "aws_security_group" "ec2_app" {
  name_prefix = "${var.project_name}-${var.environment}-ec2-"
  vpc_id      = aws_vpc.staging.id

  # Port 8000 cho ALB
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Port 22 cho SSH trực tiếp
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "SSH direct access"
  }

  # Port 1818 theo yêu cầu của Nhóm trưởng
  ingress {
    from_port   = 1818
    to_port     = 1818
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "Service Port 1818"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

resource "aws_instance" "app" {
  ami                         = data.aws_ami.amazon_linux.id
  instance_type               = var.ec2_instance_type
  subnet_id                   = aws_subnet.public_a.id
  associate_public_ip_address = true  # Cấp IP Public
  key_name                    = aws_key_pair.generated.key_name # Gắn SSH Key
  vpc_security_group_ids      = [aws_security_group.ec2_app.id]
  iam_instance_profile        = aws_iam_instance_profile.ec2_app.name

  root_block_device {
    volume_size = 20
    volume_type = "gp3"
  }

  user_data = base64encode(<<-EOF
    #!/bin/bash
    dnf update -y
    dnf install -y docker
    systemctl enable docker
    systemctl start docker
    usermod -aG docker ec2-user
    
    # Cài Docker Compose
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -SL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-x86_64" -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose
  EOF
  )

  tags = {
    Name = "${var.project_name}-${var.environment}-app"
  }
}

resource "aws_lb_target_group_attachment" "app" {
  target_group_arn = aws_lb_target_group.app.arn
  target_id        = aws_instance.app.id
  port             = 8000
}
