#!/usr/bin/env python3
"""
Script para Destruir as Tabelas do DynamoDB no SQLArena (Terraform).
"""

import argparse
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_script_dir = Path(__file__).resolve().parent
_terraform_dir = _script_dir.parent

def run_command(cmd, cwd=None):
    print(f"\n[EXEC] {cmd}")
    res = subprocess.run(cmd, shell=True, cwd=cwd)
    return res.returncode

def main():
    parser = argparse.ArgumentParser(description="Destruição das Tabelas DynamoDB (Terraform)")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Destruir no Ministack local (usa envs/local.tfvars)"
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        default=True,
        help="Executar sem confirmação manual"
    )
    args = parser.parse_args()

    print("=" * 80)
    print("🔥 DESTRUINDO TABELAS DYNAMODB DO SQLARENA")
    print(f" • Diretório Terraform: {_terraform_dir}")
    print("=" * 80)

    approve_flag = "-auto-approve" if args.auto_approve else ""
    var_file = "envs/local.tfvars" if args.local else "envs/credentials.tfvars"
    var_path = _terraform_dir / var_file

    var_flags = f'-var-file="{var_file}"' if var_path.exists() else ""
    tf_cmd = f"terraform destroy {var_flags} {approve_flag}".strip()
    run_command(tf_cmd, cwd=str(_terraform_dir))

    print("\n" + "=" * 80)
    print("✓ DESTRUIÇÃO CONCLUÍDA!")
    print("=" * 80)

if __name__ == "__main__":
    main()
