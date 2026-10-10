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

def update_amis_tfvars(web_ami=None, worker_ami=None):
    """Grava as variáveis web_ami e worker_ami em terraform/amis.auto.tfvars (ignorado pelo git)."""
    amis_path = _terraform_dir / "amis.auto.tfvars"
    existing = {}
    if amis_path.exists():
        with open(amis_path, "r", encoding="utf-8") as f:
            for line in f:
                m = re.match(r'(\w+)\s*=\s*"([^"]*)"', line.strip())
                if m:
                    existing[m.group(1)] = m.group(2)

    if web_ami:
        existing["web_ami"] = web_ami
    if worker_ami:
        existing["worker_ami"] = worker_ami

    with open(amis_path, "w", encoding="utf-8") as f:
        f.write("# ==============================================================================\n")
        f.write("# Golden AMIs geradas automaticamente por build_golden_amis.py\n")
        f.write("# Este arquivo e ignorado pelo Git (*.auto.tfvars) e carregado automaticamente!\n")
        f.write("# ==============================================================================\n")
        for k in sorted(existing.keys()):
            f.write(f'{k} = "{existing[k]}"\n')

    print(f"   ✓ [amis.auto.tfvars Atualizado] Novas AMIs salvas em {amis_path.name} (ignorado pelo Git).")

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
    max_wait_seconds = 600  # 10 minutos limite
    poll_interval = 15

    try:
        while True:
            time.sleep(poll_interval)
            elapsed = int(time.time() - start_wait)

            resp = ec2.describe_instances(InstanceIds=[instance_id])
            state = resp["Reservations"][0]["Instances"][0]["State"]["Name"]

            if state == "stopped":
                print(f"\n   ✓ Instalação finalizada com sucesso! Máquina desligou em {elapsed}s.")
                break
            elif state in ("terminated", "shutting-down"):
                raise RuntimeError(f"Instância entrou em estado de encerramento inesperado: {state}")
            elif elapsed > max_wait_seconds:
                raise TimeoutError(f"Tempo limite ({max_wait_seconds}s) excedido aguardando máquina desligar. Estado atual: {state}")

            status_desc = {
                "pending": "Inicializando hardware na AWS...",
                "running": "Executando scripts de instalação e build...",
                "stopping": "Finalizando serviços e desligando..."
            }.get(state, state)
            print(f"   ⏳ [{elapsed:3d}s decorridos] Estado: {state} ({status_desc})")

    except Exception as ex:
        print(f"\n⚠ Falha ou tempo limite aguardando desligamento da máquina {instance_id}: {ex}")
        print("Cancelando instância temporária...")
        try:
            ec2.terminate_instances(InstanceIds=[instance_id])
        except Exception:
            pass
        raise

    try:
        # 3. Criar a Golden AMI a partir do disco limpo e parado
        print(f"\n[3/4] Congelando disco e gerando Golden AMI '{ami_name}'...")
        img_resp = ec2.create_image(
            InstanceId=instance_id,
            Name=ami_name,
            Description=f"SQLArena {role.upper()} Golden AMI ({timestamp})",
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
        print("   Aguardando estado 'available' da AMI na AWS (~3 a 5 minutos)...")

        ami_start = time.time()
        while True:
            time.sleep(10)
            ami_elapsed = int(time.time() - ami_start)
            ami_resp = ec2.describe_images(ImageIds=[new_ami_id])
            ami_state = ami_resp["Images"][0]["State"]
            if ami_state == "available":
                print(f"\n   ✓ Golden AMI pronta para uso em {ami_elapsed}s: {new_ami_id}")
                break
            elif ami_state == "failed":
                raise RuntimeError(f"Criação da AMI {new_ami_id} falhou na AWS.")
            elif ami_elapsed > 600:
                raise TimeoutError(f"Tempo limite ({ami_elapsed}s) excedido aguardando AMI ficar disponível.")
            print(f"   ⏳ [{ami_elapsed:3d}s decorridos] Snapshot EBS em andamento (Estado: {ami_state})...")

        return new_ami_id

    finally:
        # 4. Excluir a instância temporária sempre (sucesso ou falha)
        print(f"\n[4/4] Limpando e terminando a instância temporária {instance_id}...")
        try:
            ec2.terminate_instances(InstanceIds=[instance_id])
            print(f"   ✓ Instância temporária encerrada.")
        except Exception as e:
            print(f"   [Aviso] Falha ao encerrar instância {instance_id}: {e}")

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
        update_amis_tfvars(worker_ami=worker_ami_id)

    if args.target in ("all", "web"):
        web_ami_id = build_single_ami(
            ec2,
            role="web",
            base_ami=args.base_ami,
            instance_type=args.instance_type
        )
        update_amis_tfvars(web_ami=web_ami_id)

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
