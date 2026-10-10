#!/usr/bin/env python3
"""
Automação Zero-Touch para Criação de Golden AMIs do SQLArena.
Executa a subida de instâncias de build na AWS, aguarda o término da instalação
(que desliga a máquina automaticamente quando pronta), gera as AMIs,
atualiza o arquivo 'terraform/envs/aws.tfvars' e exclui as máquinas temporárias.

NÃO PRECISA DE SSH OU ACESSO MANUAL AO CONSOLE.
Basta executar:
    python terraform/scripts/build_golden_amis.py
"""

import argparse
import datetime
import os
import re
import sys
import time
from pathlib import Path
import boto3
from botocore.exceptions import ClientError

_script_dir = Path(__file__).resolve().parent
_terraform_dir = _script_dir.parent
_project_root = _terraform_dir.parent

def load_credentials_from_tfvars():
    """Lê as credenciais AWS a partir de terraform/credentials.auto.tfvars."""
    cred_file = _terraform_dir / "credentials.auto.tfvars"
    creds = {}
    if cred_file.exists():
        with open(cred_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                match = re.match(r'(\w+)\s*=\s*["\']?([^"\']+)["\']?', line)
                if match:
                    creds[match.group(1)] = match.group(2)
    return creds

def get_ec2_client(region="us-east-1"):
    """Instancia o cliente EC2 usando credenciais do tfvars ou variáveis de ambiente."""
    creds = load_credentials_from_tfvars()
    kwargs = {"region_name": region}
    if "aws_access_key" in creds and "aws_secret_key" in creds:
        kwargs["aws_access_key_id"] = creds["aws_access_key"]
        kwargs["aws_secret_access_key"] = creds["aws_secret_key"]
        if "aws_session_token" in creds and creds["aws_session_token"]:
            kwargs["aws_session_token"] = creds["aws_session_token"]

    return boto3.client("ec2", **kwargs)

def update_aws_tfvars(web_ami=None, worker_ami=None):
    """Atualiza as variáveis web_ami e worker_ami em terraform/envs/aws.tfvars."""
    tfvars_path = _terraform_dir / "envs" / "aws.tfvars"
    if not tfvars_path.exists():
        print(f"   [AVISO] Arquivo {tfvars_path} não encontrado para atualização automática.")
        return

    with open(tfvars_path, "r", encoding="utf-8") as f:
        content = f.read()

    if web_ami:
        content = re.sub(r'web_ami\s*=\s*"[^"]*"', f'web_ami           = "{web_ami}"', content)
    if worker_ami:
        content = re.sub(r'worker_ami\s*=\s*"[^"]*"', f'worker_ami        = "{worker_ami}"', content)

    with open(tfvars_path, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"   ✓ [tfvars Atualizado] Novas AMIs salvas em {tfvars_path.name}.")

def build_single_ami(ec2, role: str, base_ami: str, instance_type: str) -> str:
    """
    Executa o ciclo de vida completo de uma Golden AMI:
    1. Lê o script de setup correspondente.
    2. Sobe a EC2 com InstanceInitiatedShutdownBehavior='stop'.
    3. Aguarda a máquina desligar (instalação finalizada).
    4. Tira a foto (Create Image) da máquina parada.
    5. Termina a máquina temporária.
    Retorna o ID da nova AMI (ami-xxxx).
    """
    script_file = _script_dir / f"setup_{role}.sh"
    if not script_file.exists():
        raise FileNotFoundError(f"Script de setup não encontrado: {script_file}")

    with open(script_file, "r", encoding="utf-8") as f:
        user_data_script = f.read()

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M")
    ami_name = f"sqlarena-{role}-golden-{timestamp}"
    instance_name = f"sqlarena-{role}-builder"

    print("\n" + "=" * 78)
    print(f"🔨 INICIANDO CONSTRUÇÃO AUTOMÁTICA DA GOLDEN AMI: {role.upper()}")
    print("=" * 78)
    print(f" • AMI Base:         {base_ami}")
    print(f" • Tipo EC2:         {instance_type}")
    print(f" • Script de Setup:  {script_file.name}")
    print(f" • Nome da Imagem:   {ami_name}")

    # 1. Subir EC2 Builder
    print(f"\n[1/4] Lançando máquina temporária '{instance_name}' na AWS...")
    run_kwargs = {
        "ImageId": base_ami,
        "InstanceType": instance_type,
        "MinCount": 1,
        "MaxCount": 1,
        "UserData": user_data_script,
        "InstanceInitiatedShutdownBehavior": "stop",
        "TagSpecifications": [
            {
                "ResourceType": "instance",
                "Tags": [
                    {"Key": "Name", "Value": instance_name},
                    {"Key": "Project", "Value": "sqlarena"},
                    {"Key": "Role", "Value": f"{role}-builder"}
                ]
            }
        ]
    }

    # Tenta usar o perfil de IAM do AWS Academy se disponível
    try:
        run_kwargs["IamInstanceProfile"] = {"Name": "LabInstanceProfile"}
        res = ec2.run_instances(**run_kwargs)
    except ClientError as e:
        if "InvalidParameterValue" in str(e) and "LabInstanceProfile" in str(e):
            del run_kwargs["IamInstanceProfile"]
            res = ec2.run_instances(**run_kwargs)
        else:
            raise

    instance_id = res["Instances"][0]["InstanceId"]
    print(f"   ✓ Instância lançada com sucesso: {instance_id}")

    # 2. Aguardar a máquina desligar sozinha
    print(f"\n[2/4] Aguardando instalação automática na AWS (~3 a 4 minutos)...")
    print(f"   (A máquina instalará pacotes e serviços, e desligará sozinha ao concluir)")

    start_wait = time.time()
    waiter = ec2.get_waiter("instance_stopped")
    try:
        waiter.wait(
            InstanceIds=[instance_id],
            WaiterConfig={"Delay": 15, "MaxAttempts": 32}
        )
    except Exception as ex:
        print(f"\n⚠ Falha ou tempo limite aguardando desligamento da máquina {instance_id}: {ex}")
        print("Cancelando instância temporária...")
        ec2.terminate_instances(InstanceIds=[instance_id])
        raise

    elapsed = int(time.time() - start_wait)
    print(f"   ✓ Instalação finalizada com sucesso! Máquina desligou em {elapsed}s.")

    # 3. Criar a Golden AMI a partir do disco limpo e parado
    print(f"\n[3/4] Congelando disco e gerando Golden AMI '{ami_name}'...")
    img_resp = ec2.create_image(
        InstanceId=instance_id,
        Name=ami_name,
        Description=f"Golden AMI pré-instalada para SQLArena {role.upper()} ({timestamp})",
        NoReboot=True,
        TagSpecifications=[
            {
                "ResourceType": "image",
                "Tags": [
                    {"Key": "Name", "Value": ami_name},
                    {"Key": "Project", "Value": "sqlarena"},
                    {"Key": "Role", "Value": role}
                ]
            }
        ]
    )
    new_ami_id = img_resp["ImageId"]
    print(f"   ✓ Imagem solicitada com sucesso: ID {new_ami_id}")
    print("   Aguardando estado 'available' na AWS...")

    ami_waiter = ec2.get_waiter("image_available")
    ami_waiter.wait(
        ImageIds=[new_ami_id],
        WaiterConfig={"Delay": 10, "MaxAttempts": 30}
    )
    print(f"   ✓ Golden AMI pronta para uso: {new_ami_id}")

    # 4. Excluir a instância temporária
    print(f"\n[4/4] Limpando e terminando a instância temporária {instance_id}...")
    ec2.terminate_instances(InstanceIds=[instance_id])
    print(f"   ✓ Instância temporária encerrada.")

    return new_ami_id

def main():
    parser = argparse.ArgumentParser(description="Criador Automático de Golden AMIs do SQLArena")
    parser.add_argument(
        "--target",
        choices=["all", "worker", "web"],
        default="all",
        help="Qual AMI gerar (worker, web ou all - padrão: all)"
    )
    parser.add_argument(
        "--region",
        default="us-east-1",
        help="Região AWS (padrão: us-east-1)"
    )
    parser.add_argument(
        "--base-ami",
        default="ami-0c7217cdde317cfec",
        help="AMI Ubuntu 22.04 LTS base oficial"
    )
    parser.add_argument(
        "--instance-type",
        default="t3.micro",
        help="Tipo de instância temporária para build (padrão: t3.micro)"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("🚀 SQLARENA GOLDEN AMI BUILDER - 100% AUTOMATIZADO")
    print("=" * 80)

    try:
        ec2 = get_ec2_client(region=args.region)
        ec2.describe_regions(RegionNames=[args.region])
    except Exception as e:
        print(f"\n❌ Erro de autenticação com a AWS: {e}")
        print("Verifique se o arquivo 'terraform/credentials.auto.tfvars' está preenchido corretamente.")
        return 1

    worker_ami_id = None
    web_ami_id = None

    if args.target in ("all", "worker"):
        worker_ami_id = build_single_ami(
            ec2,
            role="worker",
            base_ami=args.base_ami,
            instance_type=args.instance_type
        )
        update_aws_tfvars(worker_ami=worker_ami_id)

    if args.target in ("all", "web"):
        web_ami_id = build_single_ami(
            ec2,
            role="web",
            base_ami=args.base_ami,
            instance_type=args.instance_type
        )
        update_aws_tfvars(web_ami=web_ami_id)

    print("\n" + "=" * 80)
    print("🎉 TODAS AS GOLDEN AMIS FORAM CRIADAS COM SUCESSO!")
    print("-" * 80)
    if worker_ami_id:
        print(f" • Worker AMI: {worker_ami_id}")
    if web_ami_id:
        print(f" • Web AMI:    {web_ami_id}")
    print("-" * 80)
    print("O arquivo 'terraform/envs/aws.tfvars' foi atualizado automaticamente.")
    print("Agora, para subir a infraestrutura completa na AWS, basta rodar:")
    print("   cd terraform")
    print("   terraform apply -var-file=\"envs/aws.tfvars\"")
    print("=" * 80)

    return 0

if __name__ == "__main__":
    sys.exit(main())
