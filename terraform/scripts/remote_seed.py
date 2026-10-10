import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
from terraform.scripts.build_golden_amis import load_credentials_from_tfvars
import boto3

def run_remote_seed():
    creds = load_credentials_from_tfvars()
    ssm = boto3.client(
        "ssm",
        region_name="us-east-1",
        aws_access_key_id=creds["aws_access_key"],
        aws_secret_access_key=creds["aws_secret_key"],
        aws_session_token=creds["aws_session_token"]
    )
    ec2 = boto3.client(
        "ec2",
        region_name="us-east-1",
        aws_access_key_id=creds["aws_access_key"],
        aws_secret_access_key=creds["aws_secret_key"],
        aws_session_token=creds["aws_session_token"]
    )
    # Encontra a instancia web
    res = ec2.describe_instances(
        Filters=[
            {"Name": "tag:Role", "Values": ["WebFastAPI", "Web"]},
            {"Name": "instance-state-name", "Values": ["running"]}
        ]
    )
    instances = [i["InstanceId"] for r in res["Reservations"] for i in r["Instances"]]
    if not instances:
        # Busca pela tag Name
        res = ec2.describe_instances(
            Filters=[
                {"Name": "tag:Name", "Values": ["*web*"]},
                {"Name": "instance-state-name", "Values": ["running"]}
            ]
        )
        instances = [i["InstanceId"] for r in res["Reservations"] for i in r["Instances"]]

    if not instances:
        print("Nenhuma instancia Web encontrada!")
        return

    web_id = instances[0]
    print(f"Executando seed na instancia Web {web_id}...")

    cmd = ssm.send_command(
        InstanceIds=[web_id],
        DocumentName="AWS-RunShellScript",
        Parameters={
            "commands": [
                "cd /opt/sqlarena",
                "export PYTHONPATH='.'",
                "/opt/sqlarena/app/.venv/bin/python app/database/seed.py"
            ]
        }
    )
    cmd_id = cmd["Command"]["CommandId"]

    for _ in range(30):
        time.sleep(3)
        res = ssm.get_command_invocation(CommandId=cmd_id, InstanceId=web_id)
        status = res["Status"]
        if status in ["Success", "Failed", "TimedOut"]:
            print(f"Status do Seed: {status}")
            print("--- Saida ---")
            print(res.get("StandardOutputContent", ""))
            if res.get("StandardErrorContent"):
                print("--- Erros ---")
                print(res.get("StandardErrorContent", ""))
            break
        print(f"Aguardando execucao do seed... ({status})")

if __name__ == "__main__":
    run_remote_seed()
