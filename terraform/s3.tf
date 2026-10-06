# Bucket S3 para armazenamento dos arquivos SQL das questões (schema.sql, data.sql, answer.sql)
# No Ministack local, o Terraform provisiona o bucket diretamente.
# Na AWS Real (AWS Academy), o Learner Lab possui uma Service Control Policy (SCP) restrita
# que bloqueia GetBucketObjectLockConfiguration com 'explicit deny', o que impede o provider AWS do Terraform de ler o bucket.
# Por isso, na AWS o bucket é gerenciado e mantido diretamente pelo S3Manager / boto3 da aplicação.
resource "aws_s3_bucket" "questions_bucket" {
  count         = var.is_local ? 1 : 0
  bucket        = var.s3_bucket_name
  force_destroy = true

  tags = {
    Name        = var.s3_bucket_name
    Description = "Bucket para scripts SQL das questoes do SQLArena"
  }
}

resource "aws_s3_bucket_public_access_block" "questions_bucket_public_block" {
  count  = var.is_local ? 1 : 0
  bucket = aws_s3_bucket.questions_bucket[0].id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
