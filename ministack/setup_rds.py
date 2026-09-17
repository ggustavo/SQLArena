"""
Provisioning script for RDS PostgreSQL on Ministack.
"""

from botocore.exceptions import ClientError
from aws_clients import get_boto3_client
from config import RDS_DB_NAME, RDS_USERNAME, RDS_PASSWORD


def provision_rds():
    print("[RDS] Provisioning PostgreSQL instance on Ministack...")
    rds_client = get_boto3_client("rds")
    instance_id = "local-postgres"

    try:
        response = rds_client.create_db_instance(
            DBInstanceIdentifier=instance_id,
            DBName=RDS_DB_NAME,
            Engine="postgres",
            EngineVersion="15",
            MasterUsername=RDS_USERNAME,
            MasterUserPassword=RDS_PASSWORD,
            DBInstanceClass="db.t3.micro",
            AllocatedStorage=20,
        )
        status = response.get("DBInstance", {}).get("DBInstanceStatus", "creating")
        print(f"[RDS] Instance '{instance_id}' requested successfully. Status: {status}")
        print(f"[RDS] PostgreSQL will be accessible on host port 15432 (database: {RDS_DB_NAME}).")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "DBInstanceAlreadyExists":
            print(f"[RDS] Instance '{instance_id}' already exists.")
        else:
            print(f"[RDS] Error provisioning RDS: {e}")


if __name__ == "__main__":
    provision_rds()
