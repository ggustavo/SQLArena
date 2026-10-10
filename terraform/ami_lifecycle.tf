# ==============================================================================
# Ciclo de Vida e Limpeza de Golden AMIs durante o 'terraform destroy'
# ==============================================================================
# Quando 'terraform destroy' for executado em ambiente real (is_local = false),
# este recurso aciona automaticamente o script de limpeza para desregistrar as AMIs
# do Web e do Worker e apagar os Snapshots EBS associados, garantindo custo ZERO residual.

resource "terraform_data" "ami_cleanup" {
  count = var.is_local ? 0 : 1

  input = {
    web_ami_id    = var.web_ami
    worker_ami_id = var.worker_ami
    aws_region    = var.aws_region
    project_name  = var.project_name
  }

  provisioner "local-exec" {
    when       = destroy
    command    = "python ${path.module}/scripts/cleanup_amis.py --web-ami \"${self.input.web_ami_id}\" --worker-ami \"${self.input.worker_ami_id}\" --region \"${self.input.aws_region}\" --project \"${self.input.project_name}\""
    on_failure = continue
  }
}
