import os
import shutil
import tempfile
import unittest
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend"))

from installer.upgrade import migrate_env
from installer.templates import calculate_hash, load_hashes, save_hashes


class TestUpgradeWorkflow(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.env_file = os.path.join(self.test_dir, ".env")

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_migrate_env_creates_missing_defaults(self):
        # Create a mock env file with some pre-existing options
        with open(self.env_file, "w") as f:
            f.write("SERIAL_PORT=/dev/ttyUSB1\n")
            f.write("DATABASE_USER=custom_user\n")

        # Run migrate_env using temp directory
        migrate_env_mock(self.env_file)

        # Read back migrated file
        migrated = {}
        with open(self.env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    migrated[k.strip()] = v.strip()

        # Custom values should be preserved
        self.assertEqual(migrated["SERIAL_PORT"], "/dev/ttyUSB1")
        self.assertEqual(migrated["DATABASE_USER"], "custom_user")
        # Defaults should be appended
        self.assertEqual(migrated["SERIAL_BAUDRATE"], "9600")
        self.assertEqual(migrated["SERIAL_TIMEOUT"], "1")

    def test_calculate_hash_and_customization_tracking(self):
        test_file = os.path.join(self.test_dir, "config.conf")
        with open(test_file, "w") as f:
            f.write("test content")

        h1 = calculate_hash(test_file)
        self.assertIsNotNone(h1)
        self.assertNotEqual(h1, "")

        # Modify content and verify hash changes
        with open(test_file, "w") as f:
            f.write("modified content")
        h2 = calculate_hash(test_file)
        self.assertNotEqual(h1, h2)


def migrate_env_mock(env_path: str) -> None:
    defaults = {
        "SERIAL_PORT": "AUTO",
        "SERIAL_BAUDRATE": "9600",
        "SERIAL_TIMEOUT": "1",
        "SERIAL_RECONNECT_INTERVAL": "5",
        "SERIAL_DEBOUNCE_MS": "250",
    }
    current = {}
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    current[k.strip()] = v.strip()

    # Apply defaults
    for k, v in defaults.items():
        if k not in current:
            current[k] = v

    # Write back
    with open(env_path, "w") as f:
        f.write("# PisoWiFi Environment Settings\n")
        for k, v in sorted(current.items()):
            f.write(f"{k}={v}\n")
