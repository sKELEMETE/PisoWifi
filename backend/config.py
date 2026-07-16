from dotenv import load_dotenv
import os

# Check /opt/pisowifi/.env first, otherwise look for .env in the project directory
env_path = "/opt/pisowifi/.env" if os.path.exists("/opt/pisowifi/.env") else os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(env_path)

DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_PORT = os.getenv("DATABASE_PORT", "3306")
DATABASE_NAME = os.getenv("DATABASE_NAME", "pisowifi")
DATABASE_USER = os.getenv("DATABASE_USER", "pisowifi")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "password")

DATABASE_TYPE = os.getenv("PISOWIFI_DATABASE_TYPE", "mysql")
if DATABASE_TYPE.lower() == "sqlite":
    DATABASE_URL = os.getenv("PISOWIFI_DATABASE_URL", f"sqlite:///{os.path.join(os.path.dirname(__file__), '..', 'pisowifi.db')}")
else:
    DATABASE_URL = os.getenv("PISOWIFI_DATABASE_URL", f"mysql+pymysql://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}")

BASE_DIR = os.getenv("PISOWIFI_BASE_DIR", "/opt/pisowifi")
RUN_DIR = os.getenv("PISOWIFI_RUN_DIR", os.path.join(BASE_DIR, "run"))
SFX_DIRECTORY = os.getenv("SFX_DIRECTORY", os.path.join(BASE_DIR, "sfx"))

SESSION_CHECK_INTERVAL = int(os.getenv("SESSION_CHECK_INTERVAL", "60"))
BACKUP_DIRECTORY = os.getenv("BACKUP_DIRECTORY", os.path.join(BASE_DIR, "backups"))
LOG_DIRECTORY = os.getenv("LOG_DIRECTORY", os.path.join(BASE_DIR, "logs"))
NFT_TABLE_NAME = os.getenv("NFT_TABLE_NAME", "pisowifi")
NFT_SET_NAME = os.getenv("NFT_SET_NAME", "authenticated_clients")
CAPTIVE_PORTAL_PORT = int(os.getenv("CAPTIVE_PORTAL_PORT", "80"))
PAUSE_EXPIRATION_DAYS = int(os.getenv("PAUSE_EXPIRATION_DAYS", "30"))

SERIAL_PORT = os.getenv("SERIAL_PORT")
SERIAL_BAUDRATE = int(os.getenv("SERIAL_BAUDRATE", "9600"))
SERIAL_TIMEOUT = int(os.getenv("SERIAL_TIMEOUT", "1"))
SERIAL_RECONNECT_INTERVAL = int(os.getenv("SERIAL_RECONNECT_INTERVAL", "5"))
SERIAL_DEBOUNCE_MS = int(os.getenv("SERIAL_DEBOUNCE_MS", "300"))
SCHEDULER_INTERVAL = int(os.getenv("SCHEDULER_INTERVAL", "1"))
BACKUP_TIME = os.getenv("BACKUP_TIME", "03:00")

GATEWAY_IP = os.getenv("PISOWIFI_GATEWAY_IP", "10.0.0.1")
SUBNET_CIDR = os.getenv("PISOWIFI_SUBNET_CIDR", "10.0.0.0/24")
LAN_INTERFACE_FALLBACK = os.getenv("PISOWIFI_LAN_INTERFACE_FALLBACK", "enxc817f552a5c6")

import shutil

def find_binary(name: str, fallback_path: str) -> str:
    path = shutil.which(name)
    if path:
        return path
    return fallback_path

PATH_NFT = os.getenv("PATH_NFT", find_binary("nft", "/usr/sbin/nft"))
PATH_TC = os.getenv("PATH_TC", find_binary("tc", "/usr/sbin/tc"))
PATH_IP = os.getenv("PATH_IP", find_binary("ip", "/usr/sbin/ip"))
PATH_MODPROBE = os.getenv("PATH_MODPROBE", find_binary("modprobe", "/usr/sbin/modprobe"))

BANDWIDTH_RATE = os.getenv("PISOWIFI_BANDWIDTH_RATE", "10mbit")
BANDWIDTH_CEIL = os.getenv("PISOWIFI_BANDWIDTH_CEIL", "10mbit")

FIREWALL_DRIVER = os.getenv("PISOWIFI_FIREWALL_DRIVER", "nftables")
BANDWIDTH_DRIVER = os.getenv("PISOWIFI_BANDWIDTH_DRIVER", "linux_tc")
NETWORK_PROVIDER = os.getenv("PISOWIFI_NETWORK_PROVIDER", "local_arp")
SERIAL_DRIVER = os.getenv("PISOWIFI_SERIAL_DRIVER", "pyserial")
BACKEND_PORT = int(os.getenv("PISOWIFI_BACKEND_PORT", "8000"))

COIN_RESERVATION_TIMEOUT = int(os.getenv("COIN_RESERVATION_TIMEOUT", "30"))

# Centralized pricing table: amount -> (minutes, pause_allowed)
PRICING_TABLE = {
    1: (20, True),
    2: (40, True),
    3: (60, True),
    4: (80, True),
    5: (180, True),
    6: (200, True),
    7: (220, True),
    8: (240, True),
    9: (260, True),
    10: (360, True),
    11: (380, True),
    12: (400, True),
    13: (420, True),
    14: (440, True),
    15: (600, True),
    16: (620, True),
    17: (640, True),
    18: (660, True),
    19: (680, True),
    20: (1440, False),
}

def get_minutes_and_pause_eligibility(amount: int) -> tuple[int, bool]:
    if amount <= 0:
        return 0, True
    if amount in PRICING_TABLE:
        return PRICING_TABLE[amount]
    # Handle composite values (e.g. combinations of packages for values > 20)
    twenties = amount // 20
    remainder = amount % 20
    total_mins = twenties * 1440
    pause_allowed = True if twenties == 0 else False
    if remainder > 0:
        rem_mins, rem_pause = PRICING_TABLE[remainder]
        total_mins += rem_mins
        pause_allowed = pause_allowed and rem_pause
    return total_mins, pause_allowed