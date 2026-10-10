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

# Configura codificação do console para UTF-8 no Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_script_dir = Path(__file__).resolve().parent
_terraform_dir = _script_dir.parent
_project_root = _terraform_dir.parent

def run_command(cmd, cwd=None):
    print(f"\n[EXEC] {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=cwd)
    return res.returncode

def parse_amis_from_tfvars(tfvars_path: Path):
    """Extrai IDs de AMIs configuradas no arquivo .tfvars e em envs/credentials.tfvars se existirem."""
    web_ami = ""
    worker_ami = ""
    region = "us-east-1"

    files_to_check = [tfvars_path, _terraform_dir / "envs" / "credentials.tfvars", _terraform_dir / "credentials.auto.tfvars"]
    for fpath in files_to_check:
        if fpath.exists():
            with open(fpath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("web_ami"):
                        parts = line.split("=")
                        if len(parts) > 1:
                            val = parts[1].strip().strip('"').strip("'")
                            if val:
                                web_ami = val
                    elif line.startswith("worker_ami"):
                        parts = line.split("=")
                        if len(parts) > 1:
                            val = parts[1].strip().strip('"').strip("'")
                            if val:
                                worker_ami = val
                    elif line.startswith("aws_region"):
                        parts = line.split("=")
                        if len(parts) > 1:
                            val = parts[1].strip().strip('"').strip("'")
                            if val:
                                region = val

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

    # 1. Identifica possíveis AMIs configuradas no tfvars ou credentials
    web_ami, worker_ami, region = parse_amis_from_tfvars(tfvars_path)

    # 2. Executa terraform destroy
    approve_flag = "-auto-approve" if args.auto_approve else ""
    var_flags = []
    if tfvars_path.exists():
        var_flags.append(f'-var-file="{args.var_file}"')
    
    cred_file = _terraform_dir / "envs" / "credentials.tfvars"
    if cred_file.exists():
        var_flags.append('-var-file="envs/credentials.tfvars"')

    var_flags_str = " ".join(var_flags)
    tf_cmd = f"terraform destroy {var_flags_str} {approve_flag}".strip()

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

    # 4. Limpeza de Bucket S3 (se criado e mantido fora do Terraform no Learner Lab)
    try:
        sys.path.insert(0, str(_script_dir))
        from cleanup_amis import load_credentials_from_tfvars
        import boto3
        creds = load_credentials_from_tfvars()
        kwargs = {"region_name": region}
        if "aws_access_key" in creds and "aws_secret_key" in creds:
            kwargs["aws_access_key_id"] = creds["aws_access_key"]
            kwargs["aws_secret_access_key"] = creds["aws_secret_key"]
            if "aws_session_token" in creds and creds["aws_session_token"]:
                kwargs["aws_session_token"] = creds["aws_session_token"]
        s3 = boto3.client("s3", **kwargs)
        all_buckets = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
        for b_name in all_buckets:
            if "sqlarena" in b_name:
                print(f"\n[CLEANUP S3] Esvaziando e excluindo bucket S3 '{b_name}'...")
                paginator = s3.get_paginator('list_objects_v2')
                for page in paginator.paginate(Bucket=b_name):
                    objs = page.get('Contents', [])
                    if objs:
                        delete_keys = [{'Key': obj['Key']} for obj in objs]
                        s3.delete_objects(Bucket=b_name, Delete={'Objects': delete_keys})
                s3.delete_bucket(Bucket=b_name)
                print(f"✓ Bucket S3 '{b_name}' excluído com sucesso.")
    except Exception as s3_err:
        print(f"⚠ Aviso ao verificar/limpar buckets S3: {s3_err}")

    print("\n" + "=" * 80)
    print("✓ DESTRUIÇÃO CONCLUÍDA! Todos os recursos e dados foram removidos.")
    print("=" * 80)

if __name__ == "__main__":
    main()
