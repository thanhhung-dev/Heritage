output "ec2_public_ip" {
  description = "IP Public cua may chu EC2"
  value       = aws_instance.app.public_ip
}

output "ssh_command" {
  description = "Lenh SSH truc tiep bang File Key"
  value       = "ssh -i heritagegraph-staging-key.pem ec2-user@${aws_instance.app.public_ip}"
}

output "url_port_1818" {
  description = "Link truy cap Port 1818"
  value       = "http://${aws_instance.app.public_ip}:1818"
}

output "alb_dns_name" {
  description = "URL Public cua Load Balancer"
  value       = aws_lb.staging.dns_name
}

output "rds_endpoint" {
  description = "Dia chi RDS Postgres"
  value       = aws_db_instance.staging.address
}
