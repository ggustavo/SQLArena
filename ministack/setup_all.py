"""
Master provisioning script for all local Ministack services.
"""

from setup_rds import provision_rds
from setup_elasticache import provision_elasticache


def main():
    print("=== Starting Ministack Infrastructure Provisioning ===")
    provision_rds()
    provision_elasticache()
    print("=== Provisioning commands sent. Containers are starting via Docker! ===")


if __name__ == "__main__":
    main()
