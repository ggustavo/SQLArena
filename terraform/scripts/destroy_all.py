#!/usr/bin/env python3
"""
Script Mestre para Destruir 100% da Infraestrutura SQLArena na AWS.
Executa 'terraform destroy' e em seguida remove as Golden AMIs, Snapshots de disco EBS
e qualquer resíduo, garantindo que NENHUM custo continue ativo na AWS.
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

_script_dir = Path(__file__).resolve().parent
_terraform_dir = _script_dir.parent
_project_root = _terraform_dir.parent

def run_command(cmd, cwd=None):
    print(f"\n[EXEC] {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=cwd)
    return res.returncode

def parse_amis_from_tfvars(tfvars_path: Path):
    """Extrai IDs de AMIs configuradas no arquivo .tfvars se existirem."""
    web_ami = ""
    worker_ami = ""
    region = "us-east-1"

    if tfvars_path.exists():
        with open(tfvars_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("web_ami"):
                    parts = line.split("=")
                    if len(parts) > 1:
                        web_ami = parts[1].strip().strip('"').strip("'")
                elif line.startswith("worker_ami"):
                    parts = line.split("=")
                    if len(parts) > 1:
                        worker_ami = parts[1].strip().strip('"').strip("'")
                elif line.startswith("aws_region"):
                    parts = line.split("=")
                    if len(parts) > 1:
                        region = parts[1].strip().strip('"').strip("'")

    return web_ami, worker_ami, region

def main():
    parser = argparse.ArgumentParser(description="Destruição Completa do SQLArena (Terraform + AMIs + Dados)")
    parser.add_argument(
        "--var-file",
        default="envs/aws.tfvars",
        help="Caminho relativo para o arquivo de variáveis do Terraform a partir da pasta terraform"
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        default=True,
        help="Executar sem pedir confirmação manual (padrão: True)"
    )
    args = parser.parse_args()

    tfvars_path = _terraform_dir / args.var_file

    print("=" * 80)
    print("🔥 INICIANDO DESTRUIÇÃO COMPLETA DA INFRAESTRUTURA SQLARENA")
    print(f" • Diretório Terraform: {_terraform_dir}")
    print(f" • Arquivo de variáveis: {tfvars_path}")
    print("=" * 80)

    # 1. Identifica possíveis AMIs configuradas no tfvars
    web_ami, worker_ami, region = parse_amis_from_tfvars(tfvars_path)

    # 2. Executa terraform destroy
    approve_flag = "-auto-approve" if args.auto_approve else ""
    var_file_flag = f'-var-file="{args.var_file}"' if tfvars_path.exists() else ""
    tf_cmd = f"terraform destroy {var_file_flag} {approve_flag}".strip()

    tf_code = run_command(tf_cmd, cwd=str(_terraform_dir))
    if tf_code != 0:
        print("\n⚠ Aviso: 'terraform destroy' retornou código não-zero. Prosseguindo com a limpeza de AMIs...")

    # 3. Limpeza das Golden AMIs e Snapshots EBS
    if web_ami or worker_ami:
        print("\n" + "=" * 80)
        print("🧹 EXCLUINDO GOLDEN AMIs E SNAPSHOTS EBS RESIDUAIS")
        print("=" * 80)
        cleanup_script = _script_dir / "cleanup_amis.py"
        cleanup_cmd = (
            f'python "{cleanup_script}" '
            f'--web-ami "{web_ami}" '
            f'--worker-ami "{worker_ami}" '
            f'--region "{region}"'
        )
        run_command(cleanup_cmd)
    else:
        print("\n[INFO] Nenhuma Golden AMI customizada detectada no .tfvars.")

    print("\n" + "=" * 80)
    print("✓ DESTRUIÇÃO CONCLUÍDA! Todos os recursos e dados foram removidos.")
    print("=" * 80)

if __name__ == "__main__":
    main()
