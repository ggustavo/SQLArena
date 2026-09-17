"""
Provisioning script for ElastiCache Redis on Ministack.
"""

from botocore.exceptions import ClientError
from aws_clients import get_boto3_client


def provision_elasticache():
    print("[ElastiCache] Provisioning Redis cluster on Ministack...")
    elasticache_client = get_boto3_client("elasticache")
    cluster_id = "local-redis"

    try:
        response = elasticache_client.create_cache_cluster(
            CacheClusterId=cluster_id,
            Engine="redis",
            CacheNodeType="cache.t3.micro",
            NumCacheNodes=1,
        )
        status = response.get("CacheCluster", {}).get("CacheClusterStatus", "creating")
        print(f"[ElastiCache] Cluster '{cluster_id}' requested successfully. Status: {status}")
        print("[ElastiCache] Redis will be accessible on host port 16379.")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code")
        if error_code == "CacheClusterAlreadyExists":
            print(f"[ElastiCache] Cluster '{cluster_id}' already exists.")
        else:
            print(f"[ElastiCache] Error provisioning ElastiCache: {e}")


if __name__ == "__main__":
    provision_elasticache()
