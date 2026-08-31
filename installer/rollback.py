import os
import shutil


class RollbackManager:

    def __init__(self, backup_dir="/tmp/pisowifi_install_backup"):
        self.backup_dir = backup_dir
        self.written_files = []  # list of (action, path, backup_path)
        os.makedirs(backup_dir, exist_ok=True)

    def write_file(self, path: str, content: str) -> None:
        """Writes content to path, backing up any existing file first."""
        backup_path = None
        if os.path.exists(path):
            rel_name = path.replace("/", "_")
            backup_path = os.path.join(self.backup_dir, rel_name)
            shutil.copy2(path, backup_path)
            self.written_files.append(("overwrite", path, backup_path))
        else:
            self.written_files.append(("create", path, None))

        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    def copy_file(self, src: str, dst: str) -> None:
        """Copies file from src to dst, backing up any existing dst file first."""
        backup_path = None
        if os.path.exists(dst):
            rel_name = dst.replace("/", "_")
            backup_path = os.path.join(self.backup_dir, rel_name)
            shutil.copy2(dst, backup_path)
            self.written_files.append(("overwrite", dst, backup_path))
        else:
            self.written_files.append(("create", dst, None))

        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

    def create_symlink(self, src: str, dst: str) -> None:
        """Creates symlink at dst targeting src."""
        if os.path.exists(dst) or os.path.islink(dst):
            rel_name = dst.replace("/", "_")
            backup_path = os.path.join(self.backup_dir, rel_name)
            if os.path.islink(dst):
                with open(backup_path, "w") as f:
                    f.write(os.readlink(dst))
                self.written_files.append(("overwrite_link", dst, backup_path))
                os.remove(dst)
            else:
                shutil.copy2(dst, backup_path)
                self.written_files.append(("overwrite", dst, backup_path))
                os.remove(dst)
        else:
            self.written_files.append(("create", dst, None))

        os.symlink(src, dst)

    def remove_path(self, path: str) -> None:
        """Remove one file/symlink while retaining enough state to roll back."""
        if not (os.path.exists(path) or os.path.islink(path)):
            return
        rel_name = path.replace("/", "_")
        backup_path = os.path.join(self.backup_dir, rel_name)
        if os.path.islink(path):
            with open(backup_path, "w") as stream:
                stream.write(os.readlink(path))
            self.written_files.append(("remove_link", path, backup_path))
        else:
            shutil.copy2(path, backup_path)
            self.written_files.append(("remove_file", path, backup_path))
        os.remove(path)

    def rollback(self) -> None:
        """Reverts all tracked changes in reverse order."""
        print("\n[ROLLBACK] Reverting system modifications...")
        for action, path, backup_path in reversed(self.written_files):
            try:
                if action == "create":
                    if os.path.exists(path) or os.path.islink(path):
                        if os.path.isdir(path) and not os.path.islink(path):
                            shutil.rmtree(path)
                        else:
                            os.remove(path)
                        print(f" -> Removed created file/dir: {path}")
                elif action == "overwrite":
                    if backup_path and os.path.exists(backup_path):
                        # Ensure directory exists before copy
                        os.makedirs(os.path.dirname(path), exist_ok=True)
                        shutil.copy2(backup_path, path)
                        print(f" -> Restored original file: {path}")
                elif action == "overwrite_link":
                    if backup_path and os.path.exists(backup_path):
                        with open(backup_path, "r") as f:
                            target = f.read().strip()
                        if os.path.exists(path) or os.path.islink(path):
                            os.remove(path)
                        os.symlink(target, path)
                        print(f" -> Restored original symlink: {path} -> {target}")
                elif action == "remove_link":
                    with open(backup_path) as f:
                        os.symlink(f.read().strip(), path)
                    print(f" -> Restored removed symlink: {path}")
                elif action == "remove_file":
                    shutil.copy2(backup_path, path)
                    print(f" -> Restored removed file: {path}")
            except Exception as e:
                print(f" -> Failed to revert {path}: {e}")
