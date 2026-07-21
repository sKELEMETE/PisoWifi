import os
import re
import shutil
import bcrypt
import logging
import config
from utils.auth import verify_password

logger = logging.getLogger("admin_credentials")

USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9_-]{3,32}$")


class AdminCredentialsService:
    @staticmethod
    def validate_username(username: str) -> str:
        if not username or not isinstance(username, str):
            raise ValueError("Username must be a non-empty string.")
        cleaned = username.strip()
        if not USERNAME_REGEX.match(cleaned):
            raise ValueError("Username must be 3-32 characters long and contain only letters, numbers, underscores, or hyphens.")
        return cleaned

    @staticmethod
    def validate_password(password: str) -> str:
        if not password or not isinstance(password, str):
            raise ValueError("Password must be a non-empty string.")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters long.")
        return password

    @staticmethod
    def generate_hash(password: str) -> str:
        valid_pass = AdminCredentialsService.validate_password(password)
        return bcrypt.hashpw(valid_pass.encode("utf-8"), bcrypt.gensalt(12)).decode("utf-8")

    @staticmethod
    def validate_hash(hash_str: str) -> bool:
        if not hash_str or not isinstance(hash_str, str) or len(hash_str.strip()) < 50:
            return False
        try:
            bcrypt.checkpw(b"dry_run", hash_str.strip().encode("utf-8"))
            return True
        except Exception:
            return False

    @staticmethod
    def _update_env_file(target_env_path: str, new_username: str = None, new_hash: str = None) -> None:
        lines = []
        if os.path.exists(target_env_path):
            with open(target_env_path, "r", encoding="utf-8") as f:
                lines = f.readlines()

        updated_username = False
        updated_hash = False
        new_lines = []

        for line in lines:
            stripped = line.strip()
            if new_username and (stripped.startswith("ADMIN_USERNAME=") or stripped.startswith("export ADMIN_USERNAME=")):
                new_lines.append(f"ADMIN_USERNAME={new_username}\n")
                updated_username = True
            elif new_hash and (stripped.startswith("ADMIN_PASSWORD_HASH=") or stripped.startswith("export ADMIN_PASSWORD_HASH=")):
                new_lines.append(f"ADMIN_PASSWORD_HASH='{new_hash}'\n")
                updated_hash = True
            else:
                new_lines.append(line)

        if new_username and not updated_username:
            new_lines.append(f"ADMIN_USERNAME={new_username}\n")
        if new_hash and not updated_hash:
            new_lines.append(f"ADMIN_PASSWORD_HASH='{new_hash}'\n")

        # Create a backup of the current env file before modifying
        backup_path = f"{target_env_path}.bak"
        try:
            shutil.copy2(target_env_path, backup_path)
            logger.info("Backed up %s to %s", target_env_path, backup_path)
        except Exception as exc:
            logger.warning("Failed to backup env file before update: %s", exc)

        tmp_path = f"{target_env_path}.tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
                f.flush()
                os.fsync(f.fileno())

            os.replace(tmp_path, target_env_path)
        except Exception as exc:
            if os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
            logger.error("Failed atomic update of env file %s: %s", target_env_path, exc)
            raise RuntimeError(f"Atomic configuration file update failed: {exc}")

        # Reload in-memory configuration immediately after atomic write
        config.reload_admin_config()

    @classmethod
    def set_username(cls, new_username: str) -> str:
        validated_user = cls.validate_username(new_username)
        local_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
        target_env = local_env if os.path.exists(local_env) else "/opt/pisowifi/.env"
        cls._update_env_file(target_env, new_username=validated_user)
        return validated_user

    @classmethod
    def reset_password(cls, new_password: str) -> str:
        new_hash = cls.generate_hash(new_password)
        local_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
        target_env = local_env if os.path.exists(local_env) else "/opt/pisowifi/.env"
        cls._update_env_file(target_env, new_hash=new_hash)
        return new_hash

    @classmethod
    def change_credentials(cls, current_password: str, new_username: str = None, new_password: str = None) -> dict:
        if not current_password or not verify_password(current_password):
            logger.warning("Admin credential change failed: Invalid current password.")
            raise ValueError("Current password verification failed. Please enter your correct current password.")

        if not new_username and not new_password:
            raise ValueError("Either new username or new password must be provided.")

        validated_username = None
        if new_username:
            validated_username = cls.validate_username(new_username)

        validated_password_hash = None
        if new_password:
            validated_password_hash = cls.generate_hash(new_password)

        local_env = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".env"))
        target_env = local_env if os.path.exists(local_env) else "/opt/pisowifi/.env"

        cls._update_env_file(target_env, new_username=validated_username, new_hash=validated_password_hash)

        logger.info("Admin credentials updated successfully (username_changed=%s, password_changed=%s)", bool(validated_username), bool(validated_password_hash))

        return {
            "username_changed": bool(validated_username),
            "password_changed": bool(validated_password_hash),
            "username": config.ADMIN_USERNAME,
        }

