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

    args = parser.parse_args()

    if args.command == "version":
        print(f"PisoWiFi Version: {get_version()}")
    elif args.command == "doctor":
        doctor = DoctorCheck()
        success = doctor.run_all()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
