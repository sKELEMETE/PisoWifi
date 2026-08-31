import os
import sys
import argparse

# Resolve project base directory relative to this script path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

from installer.utils import get_version
from installer.doctor import DoctorCheck


def main():
    parser = argparse.ArgumentParser(description="PisoWiFi Management CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Doctor subcommand
    subparsers.add_parser("doctor", help="Run comprehensive system diagnostics check")

    # Version subcommand
    subparsers.add_parser("version", help="Show PisoWiFi active release version")

    # Upgrade subcommand
    subparsers.add_parser("upgrade", help="Perform automated PisoWiFi upgrade workflow")

    subparsers.add_parser("hardware-status", help="Show configured and live coin hardware state")
    hardware_test_parser = subparsers.add_parser("hardware-test", help="Interactively test GPIO relay and coin input")
    hardware_test_parser.add_argument("--calibrate", action="store_true", help="Capture and save denomination pulse mappings")

    args = parser.parse_args()

    if args.command == "version":
        print(f"PisoWiFi Version: {get_version()}")
    elif args.command == "doctor":
        doctor = DoctorCheck()
        success = doctor.run_all()
        sys.exit(0 if success else 1)
    elif args.command == "upgrade":
        from installer.upgrade import run_upgrade
        success = run_upgrade(BASE_DIR)
        sys.exit(0 if success else 1)
    elif args.command == "hardware-status":
        from installer.hardware_cli import hardware_status
        sys.exit(0 if hardware_status() else 1)
    elif args.command == "hardware-test":
        from installer.hardware_cli import hardware_test
        sys.exit(0 if hardware_test(args.calibrate) else 1)


if __name__ == "__main__":
    main()
