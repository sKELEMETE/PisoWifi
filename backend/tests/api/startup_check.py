import requests
import sys

BASE = "http://127.0.0.1:8000"


def check():
    endpoints = [
        "/api/v1/health",
        "/api/v1/client/AA:BB:CC:DD:EE:FF",
    ]

    for e in endpoints:
        r = requests.get(f"{BASE}{e}")
        if r.status_code != 200:
            print("FAIL:", e)
            sys.exit(1)

    print("SYSTEM OK")


if __name__ == "__main__":
    check()
