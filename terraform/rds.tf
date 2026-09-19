# Instância RDS PostgreSQL
resource "aws_db_instance" "postgres" {
  identifier          = "${var.project_name}-postgres"
  db_name             = var.db_name
  engine              = "postgres"
  engine_version      = "15"
  instance_class      = "db.t3.micro"
  allocated_storage   = 20
  username            = var.db_username
  password            = var.db_password
  skip_final_snapshot = true
  publicly_accessible = true
}
