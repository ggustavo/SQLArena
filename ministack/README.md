# Ministack Provisioning Scripts

Scripts to provision local AWS resources (RDS PostgreSQL and ElastiCache Redis) in Ministack.

---

## Provisioning Scripts

- `setup_rds.py`: Provisions the PostgreSQL RDS container on port 15432.
- `setup_elasticache.py`: Provisions the Redis ElastiCache container on port 16379.
- `setup_all.py`: Executes both provisioning steps sequentially.

---

## How to Run

From the `ministack` directory:

1. Start the Ministack container:
   ```bash
   docker compose up -d
   ```

2. Run the provisioning scripts:
   ```bash
   python setup_all.py
   # Or individually:
   python setup_rds.py
   python setup_elasticache.py
   ```
