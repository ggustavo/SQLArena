# Bucket S3 para armazenamento dos arquivos SQL das questões (schema.sql, data.sql, answer.sql)
resource "aws_s3_bucket" "questions_bucket" {
  bucket        = var.s3_bucket_name
  force_destroy = var.is_local ? true : false

  tags = {
    Name        = var.s3_bucket_name
    Description = "Bucket para scripts SQL das questoes do SQLArena"
  }
}

# Bloqueio de acesso público ao bucket S3 para segurança dos dados e gabaritos
resource "aws_s3_bucket_public_access_block" "questions_bucket_public_block" {
  bucket = aws_s3_bucket.questions_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
