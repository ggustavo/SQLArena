#!/usr/bin/env python3
"""
Script Mestre para Destruir 100% da Infraestrutura SQLArena na AWS (Modo 1 EKS ou Modo 2 EC2 Compose).
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
    parser = argparse.ArgumentParser(description="Destruição Completa do SQLArena (Terraform)")
    parser.add_argument(
        "--var-file",
        default="envs/modo2-ec2-compose.tfvars",
        help="Arquivo .tfvars do modo ativo (ex: envs/modo1-eks.tfvars ou envs/modo2-ec2-compose.tfvars)"
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        default=True,
        help="Executar sem confirmação manual"
    )
    args = parser.parse_args()

    tfvars_path = _terraform_dir / args.var_file
    print("=" * 80)
    print("🔥 INICIANDO DESTRUIÇÃO DA INFRAESTRUTURA SQLARENA")
    print(f" • Diretório Terraform: {_terraform_dir}")
    print(f" • Arquivo de variáveis: {tfvars_path}")
    print("=" * 80)

    approve_flag = "-auto-approve" if args.auto_approve else ""
    var_flags = []
    if tfvars_path.exists():
        var_flags.append(f'-var-file="{args.var_file}"')

    cred_file = _terraform_dir / "envs" / "credentials.tfvars"
    if cred_file.exists():
        var_flags.append('-var-file="envs/credentials.tfvars"')

    var_flags_str = " ".join(var_flags)
    tf_cmd = f"terraform destroy {var_flags_str} {approve_flag}".strip()
    run_command(tf_cmd, cwd=str(_terraform_dir))

    print("\n" + "=" * 80)
    print("✓ DESTRUIÇÃO CONCLUÍDA!")
    print("=" * 80)

if __name__ == "__main__":
    main()
