data "aws_rds_engine_version" "postgres" {
  engine = "postgres"
}

resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-${var.environment}-rds-"
  vpc_id      = aws_vpc.staging.id
  description = "Allow Postgres from EC2 app only"

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2_app.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-rds-sg"
  }
}

resource "aws_db_subnet_group" "staging" {
  name       = "${var.project_name}-${var.environment}"
  subnet_ids = [aws_subnet.private_a.id, aws_subnet.private_b.id]
}

resource "random_password" "db" {
  length  = 24
  special = false
}

resource "aws_db_instance" "staging" {
  identifier = "${var.project_name}-${var.environment}-db"

  engine         = "postgres"
  engine_version = data.aws_rds_engine_version.postgres.version
  instance_class = var.db_instance_class

  allocated_storage = 20
  storage_type      = "gp3"

  db_name  = var.db_name
  username = "heritagegraph"
  password = random_password.db.result

  publicly_accessible    = false
  db_subnet_group_name   = aws_db_subnet_group.staging.name
  vpc_security_group_ids = [aws_security_group.rds.id]

  skip_final_snapshot = true

  tags = {
    Name = "${var.project_name}-${var.environment}-rds"
  }
}

resource "aws_secretsmanager_secret" "db_credentials" {
  name                    = "${var.project_name}/${var.environment}/db-credentials"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "db_credentials" {
  secret_id = aws_secretsmanager_secret.db_credentials.id
  secret_string = jsonencode({
    username = "heritagegraph"
    password = random_password.db.result
    dbname   = var.db_name
    host     = aws_db_instance.staging.address
    port     = 5432
  })
}
