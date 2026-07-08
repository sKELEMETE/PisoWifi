import requests

BASE = "http://127.0.0.1:8000"


def test_health():
    r = requests.get(f"{BASE}/api/v1/health")
    print("HEALTH:", r.status_code, r.json())


def test_client():
    mac = "AA:BB:CC:DD:EE:FF"
    r = requests.get(f"{BASE}/api/v1/client/{mac}")
    print("CLIENT:", r.status_code, r.json())


def test_session():
    mac = "AA:BB:CC:DD:EE:FF"

    r = requests.get(f"{BASE}/api/v1/session/{mac}")
    print("SESSION GET:", r.status_code, r.json())

    r = requests.post(f"{BASE}/api/v1/session/pause/{mac}")
    print("SESSION PAUSE:", r.status_code, r.json())

    r = requests.post(f"{BASE}/api/v1/session/resume/{mac}")
    print("SESSION RESUME:", r.status_code, r.json())


def test_coin():
    mac = "AA:BB:CC:DD:EE:FF"

    r = requests.post(f"{BASE}/api/v1/coin/test/{mac}/1")
    print("COIN:", r.status_code, r.json())


def test_voucher():
    mac = "AA:BB:CC:DD:EE:FF"

    r = requests.post(f"{BASE}/api/v1/voucher/redeem/VOUCHER123/{mac}")
    print("VOUCHER:", r.status_code, r.json())


if __name__ == "__main__":
    print("\n--- API SMOKE TEST START ---\n")

    test_health()
    test_client()
    test_session()
    test_coin()
    test_voucher()

    print("\n--- API SMOKE TEST END ---\n")
