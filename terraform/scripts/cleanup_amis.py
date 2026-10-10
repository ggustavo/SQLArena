#!/usr/bin/env python3
"""
Script de Limpeza de Golden AMIs e Snapshots do SQLArena.
Utilizado durante o 'terraform destroy' para garantir que as AMIs e
snapshots de disco EBS criados para o Web e Worker sejam 100% eliminados da AWS.
"""

import argparse
import sys
import boto3
from botocore.exceptions import ClientError

def cleanup_ami(ec2_client, ami_id: str):
    """Desregistra a AMI e remove todos os snapshots EBS vinculados a ela."""
    if not ami_id or not ami_id.startswith("ami-"):
        return

    print(f"\n[CLEANUP] Processando remoção da AMI '{ami_id}'...")
    try:
        response = ec2_client.describe_images(ImageIds=[ami_id])
        images = response.get("Images", [])
        if not images:
            print(f"   [INFO] AMI '{ami_id}' não encontrada (já removida ou inexistente).")
            return

        image = images[0]
        name = image.get("Name", "sem-nome")
        snapshot_ids = []

        # Localiza todos os snapshots EBS associados ao volume de disco da imagem
        for bdm in image.get("BlockDeviceMappings", []):
            ebs = bdm.get("Ebs")
            if ebs and "SnapshotId" in ebs:
                snapshot_ids.append(ebs["SnapshotId"])

        # 1. Desregistrar a AMI
        print(f"   [1/2] Desregistrando AMI '{ami_id}' ('{name}')...")
        ec2_client.deregister_image(ImageId=ami_id)
        print(f"   ✓ AMI '{ami_id}' desregistrada com sucesso.")

        # 2. Deletar os snapshots EBS subjacentes
        for snap_id in snapshot_ids:
            try:
                print(f"   [2/2] Excluindo Snapshot EBS '{snap_id}' vinculado...")
                ec2_client.delete_snapshot(SnapshotId=snap_id)
                print(f"   ✓ Snapshot '{snap_id}' excluído com sucesso.")
            except ClientError as snap_err:
                print(f"   ⚠ Não foi possível excluir o snapshot '{snap_id}': {snap_err}")

    except ClientError as err:
        err_code = err.response.get("Error", {}).get("Code", "")
        if err_code in ("InvalidAMIID.NotFound", "InvalidAMIID.Malformed"):
            print(f"   [INFO] AMI '{ami_id}' já desregistrada ou não existe.")
        else:
            print(f"   ⚠ Erro ao manipular AMI '{ami_id}': {err}")
    except Exception as e:
        print(f"   ⚠ Exceção inesperada: {e}")

def cleanup_by_project_tags(ec2_client, project_name: str = "sqlarena"):
    """Busca e limpa qualquer AMI pertencente à conta marcada com tags do projeto."""
    try:
        resp = ec2_client.describe_images(
            Owners=["self"],
            Filters=[{"Name": "tag:Project", "Values": [project_name]}]
        )
        images = resp.get("Images", [])
        if images:
            print(f"\n[CLEANUP] Encontradas {len(images)} AMIs registradas com tag Project={project_name}.")
            for img in images:
                cleanup_ami(ec2_client, img["ImageId"])
    except Exception as e:
        pass

def main():
    parser = argparse.ArgumentParser(description="Limpeza de Golden AMIs e Snapshots do SQLArena")
    parser.add_argument("--web-ami", default="", help="ID da AMI Web (ex: ami-0abc1234)")
    parser.add_argument("--worker-ami", default="", help="ID da AMI Worker (ex: ami-0def5678)")
    parser.add_argument("--region", default="us-east-1", help="Região AWS")
    parser.add_argument("--project", default="sqlarena", help="Tag de projeto")
    args = parser.parse_args()

    if not args.web_ami and not args.worker_ami:
        print("[CLEANUP] Nenhuma AMI específica configurada para exclusão.")
        return 0

    try:
        ec2 = boto3.client("ec2", region_name=args.region)
    except Exception as e:
        print(f"[CLEANUP] Aviso: cliente AWS não inicializado ({e}). Ignorando remoção de AMI.")
        return 0

    if args.web_ami:
        cleanup_ami(ec2, args.web_ami.strip())

    if args.worker_ami:
        cleanup_ami(ec2, args.worker_ami.strip())

    if args.project:
        cleanup_by_project_tags(ec2, args.project.strip())

    print("\n[✓] Limpeza de AMIs e Snapshots concluída.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
