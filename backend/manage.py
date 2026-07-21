#!/usr/bin/env python3
import sys
import os

# Auto-activate / re-exec under project virtual environment if running outside venv
_script_dir = os.path.dirname(os.path.abspath(__file__))
_venv_python = os.path.join(_script_dir, "venv", "bin", "python")
if os.path.exists(_venv_python) and os.path.abspath(sys.executable) != os.path.abspath(_venv_python) and "PYTHON_IN_VENV" not in os.environ:
    os.environ["PYTHON_IN_VENV"] = "1"
    os.execv(_venv_python, [_venv_python] + sys.argv)

import argparse
import bcrypt

# Ensure backend path is in sys.path
sys.path.insert(0, _script_dir)

import config
from services.admin_credentials_service import AdminCredentialsService


def cmd_check(args):
    print("=== PisoWiFi Admin Credentials Diagnostic ===")
    print(f"Configured Admin Username: {config.ADMIN_USERNAME}")
    has_hash = bool(config.ADMIN_PASSWORD_HASH and config.ADMIN_PASSWORD_HASH.strip())
    print(f"Bcrypt Hash Configured   : {has_hash} (Length: {len(config.ADMIN_PASSWORD_HASH) if has_hash else 0})")
    print(f"JWT Secret Configured    : {bool(config.ADMIN_JWT_SECRET)} (Length: {len(config.ADMIN_JWT_SECRET) if config.ADMIN_JWT_SECRET else 0})")
    print(f"JWT Token Expiration     : {config.ADMIN_TOKEN_EXPIRE_HOURS} hours")
    print(f"Default Credentials Flag : {config.IS_DEFAULT_CREDENTIALS}")

    valid_bcrypt = AdminCredentialsService.validate_hash(config.ADMIN_PASSWORD_HASH) if has_hash else False
    print(f"Bcrypt Hash Valid        : {valid_bcrypt}")
    if valid_bcrypt and not config.IS_DEFAULT_CREDENTIALS and len(config.ADMIN_JWT_SECRET) >= 16:
        print("\n[OK] Configuration Health Status: SECURE & VALID")
    else:
        print("\n[WARNING] Configuration Health Status: REQUIRES ATTENTION")


def cmd_set_username(args):
    new_user = args.username
    if not new_user:
        new_user = input("Enter new admin username: ").strip()

    try:
        updated = AdminCredentialsService.set_username(new_user)
        print(f"[SUCCESS] Admin username successfully updated to '{updated}'.")
    except Exception as exc:
        print(f"[ERROR] Failed updating username: {exc}")
        sys.exit(1)


def cmd_reset_password(args):
    new_pass = args.password
    if not new_pass:
        import getpass
        new_pass = getpass.getpass("Enter new admin password: ").strip()
        confirm = getpass.getpass("Confirm new admin password: ").strip()
        if new_pass != confirm:
            print("[ERROR] Passwords do not match.")
            sys.exit(1)

    try:
        AdminCredentialsService.reset_password(new_pass)
        print("[SUCCESS] Admin password successfully updated and bcrypt hash saved to environment configuration.")
    except Exception as exc:
        print(f"[ERROR] Failed resetting password: {exc}")
        sys.exit(1)


def cmd_generate_hash(args):
    plain_pass = args.password
    if not plain_pass:
        import getpass
        plain_pass = getpass.getpass("Enter plain password to hash: ").strip()

    try:
        generated = AdminCredentialsService.generate_hash(plain_pass)
        print(f"Generated Bcrypt Hash: {generated}")
    except Exception as exc:
        print(f"[ERROR] Failed generating hash: {exc}")
        sys.exit(1)


def cmd_validate_hash(args):
    target_hash = args.hash
    if not target_hash:
        target_hash = input("Enter bcrypt hash to validate: ").strip()

    is_valid = AdminCredentialsService.validate_hash(target_hash)
    if is_valid:
        print("[VALID] String is a syntactically valid bcrypt hash structure.")
    else:
        print("[INVALID] String is NOT a valid bcrypt hash structure.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="PisoWiFi CLI Administration & Credentials Manager")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Credentials command group
    cred_parser = subparsers.add_parser("credentials", help="Admin credentials operations")
    cred_sub = cred_parser.add_subparsers(dest="action", help="Credential action")

    # Check
    cred_sub.add_parser("check", help="Check credentials configuration health")

    # Set username
    set_user_p = cred_sub.add_parser("set-username", help="Change admin username")
    set_user_p.add_argument("--username", help="New username string")

    # Reset password
    reset_p = cred_sub.add_parser("reset-password", help="Reset admin password")
    reset_p.add_argument("--password", help="New password string")

    # Set password (alias for reset-password)
    set_pass_p = cred_sub.add_parser("set-password", help="Set admin password")
    set_pass_p.add_argument("--password", help="New password string")

    # Generate hash
    gen_hash_p = cred_sub.add_parser("generate-hash", help="Generate bcrypt hash from plain string")
    gen_hash_p.add_argument("--password", help="Plain password string")

    # Validate hash
    val_hash_p = cred_sub.add_parser("validate-hash", help="Validate bcrypt hash structure")
    val_hash_p.add_argument("--hash", help="Bcrypt hash string to validate")

    args = parser.parse_args()

    if args.command == "credentials":
        if args.action == "check":
            cmd_check(args)
        elif args.action == "set-username":
            cmd_set_username(args)
        elif args.action in ("reset-password", "set-password"):
            cmd_reset_password(args)
        elif args.action == "generate-hash":
            cmd_generate_hash(args)
        elif args.action == "validate-hash":
            cmd_validate_hash(args)
        else:
            cred_parser.print_help()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

