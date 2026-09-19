# Fila de Mensagens Mortas (Dead Letter Queue - DLQ) para armazenar falhas de processamento
resource "aws_sqs_queue" "submissions_dlq" {
  name                      = "${var.sqs_queue_name}-dlq"
  message_retention_seconds = 1209600 # 14 dias de retenção para análise de erros

  tags = {
    Name = "${var.sqs_queue_name}-dlq"
  }
}

# Fila principal do SQS para submissões assíncronas
resource "aws_sqs_queue" "submissions_queue" {
  name                       = var.sqs_queue_name
  delay_seconds              = 0
  max_message_size           = 262144 # 256 KB
  message_retention_seconds  = 86400  # 1 dia
  receive_wait_time_seconds  = 10     # Long polling (10s) para economia de chamadas e menor latência
  visibility_timeout_seconds = 30

  # Encaminha para a DLQ após 5 tentativas sem sucesso
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.submissions_dlq.arn
    maxReceiveCount     = 5
  })

  tags = {
    Name = var.sqs_queue_name
  }
}
