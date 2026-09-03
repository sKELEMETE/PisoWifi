from dotenv import load_dotenv
import os
import shutil
import json

# Load system-wide environment configuration
if os.path.exists("/opt/pisowifi/.env"):
    load_dotenv("/opt/pisowifi/.env", interpolate=False)

# Load project-local backend environment configuration
local_env = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(local_env):
    # Explicit process/systemd environment values take precedence over a
    # developer checkout's convenience file.
    load_dotenv(local_env, interpolate=False, override=False)

ENVIRONMENT = os.getenv("ENVIRONMENT", os.getenv("PISOWIFI_ENVIRONMENT", "production")).lower()
DEBUG = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

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

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_default_base = "/opt/pisowifi" if os.path.exists("/opt/pisowifi") else _REPO_ROOT
BASE_DIR = os.getenv("PISOWIFI_BASE_DIR", _default_base)
RUN_DIR = os.getenv("PISOWIFI_RUN_DIR", os.path.join(BASE_DIR, "run"))
SFX_DIRECTORY = os.getenv("SFX_DIRECTORY", os.path.join(BASE_DIR, "sfx"))
if not os.path.exists(SFX_DIRECTORY) and os.path.exists(os.path.join(_REPO_ROOT, "sfx")):
    SFX_DIRECTORY = os.path.join(_REPO_ROOT, "sfx")

SESSION_CHECK_INTERVAL = int(os.getenv("SESSION_CHECK_INTERVAL", "60"))
BACKUP_DIRECTORY = os.getenv("BACKUP_DIRECTORY", os.path.join(BASE_DIR, "backups"))
if not os.path.exists(BACKUP_DIRECTORY) and os.path.exists(os.path.join(_REPO_ROOT, "backups")):
    BACKUP_DIRECTORY = os.path.join(_REPO_ROOT, "backups")

LOG_DIRECTORY = os.getenv("LOG_DIRECTORY", os.path.join(BASE_DIR, "logs"))
if not os.path.exists(LOG_DIRECTORY) and os.path.exists(os.path.join(_REPO_ROOT, "logs")):
    LOG_DIRECTORY = os.path.join(_REPO_ROOT, "logs")
NFT_TABLE_NAME = os.getenv("NFT_TABLE_NAME", "pisowifi")
NFT_SET_NAME = os.getenv("NFT_SET_NAME", "authenticated_clients")
CAPTIVE_PORTAL_PORT = int(os.getenv("CAPTIVE_PORTAL_PORT", "80"))
PAUSE_EXPIRATION_DAYS = int(os.getenv("PAUSE_EXPIRATION_DAYS", "30"))

SERIAL_PORT = os.getenv("SERIAL_PORT")
SERIAL_BAUDRATE = int(os.getenv("SERIAL_BAUDRATE", "9600"))
SERIAL_TIMEOUT = int(os.getenv("SERIAL_TIMEOUT", "1"))
SERIAL_RECONNECT_INTERVAL = int(os.getenv("SERIAL_RECONNECT_INTERVAL", "5"))
SERIAL_DEBOUNCE_MS = int(os.getenv("SERIAL_DEBOUNCE_MS", "50"))

SCHEDULER_INTERVAL = int(os.getenv("SCHEDULER_INTERVAL", "1"))
BACKUP_TIME = os.getenv("BACKUP_TIME", "03:00")

GATEWAY_IP = os.getenv("PISOWIFI_GATEWAY_IP", "10.0.0.1")
SUBNET_CIDR = os.getenv("PISOWIFI_SUBNET_CIDR", "10.0.0.0/24")
LAN_INTERFACE_FALLBACK = os.getenv("PISOWIFI_LAN_INTERFACE_FALLBACK", "enxc817f552a5c6")

def find_binary(name: str, fallback_path: str) -> str:
    # Search standard paths first to support restricted systemd PATH environment
    search_paths = "/usr/sbin:/usr/bin:/sbin:/bin"
    path = shutil.which(name, path=search_paths)
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

CORS_ORIGINS = [
    origin.strip() for origin in os.getenv(
        "PISOWIFI_CORS_ORIGINS",
        f"http://10.0.0.1,http://localhost,http://localhost:5173,http://127.0.0.1,http://{GATEWAY_IP}"
    ).split(",") if origin.strip() and origin.strip() != "*"
]

COIN_RESERVATION_TIMEOUT = int(os.getenv("COIN_RESERVATION_TIMEOUT", "30"))
COIN_INTERFACE = os.getenv("COIN_INTERFACE", "arduino").strip().lower()
COIN_SESSION_LEASE_SECONDS = int(os.getenv("COIN_SESSION_LEASE_SECONDS", "12"))
COIN_HEARTBEAT_SECONDS = int(os.getenv("COIN_HEARTBEAT_SECONDS", "3"))
COIN_LEASE_CHECK_INTERVAL = int(os.getenv("COIN_LEASE_CHECK_INTERVAL", "1"))
COIN_CURRENCY_SYMBOL = os.getenv("COIN_CURRENCY_SYMBOL", "₱")

GPIO_COIN_CHIP = os.getenv("GPIO_COIN_CHIP", "")
GPIO_COIN_LINE = int(os.getenv("GPIO_COIN_LINE", "-1"))
GPIO_COIN_NAME = os.getenv("GPIO_COIN_NAME", "")
GPIO_COIN_PHYSICAL_PIN = int(os.getenv("GPIO_COIN_PHYSICAL_PIN", "0"))
GPIO_COIN_EDGE = os.getenv("GPIO_COIN_EDGE", "falling").strip().lower()
GPIO_RELAY_CHIP = os.getenv("GPIO_RELAY_CHIP", "")
GPIO_RELAY_LINE = int(os.getenv("GPIO_RELAY_LINE", "-1"))
GPIO_RELAY_NAME = os.getenv("GPIO_RELAY_NAME", "")
GPIO_RELAY_PHYSICAL_PIN = int(os.getenv("GPIO_RELAY_PHYSICAL_PIN", "0"))
GPIO_RELAY_ACTIVE_LOW = os.getenv("GPIO_RELAY_ACTIVE_LOW", "true").lower() in ("true", "1", "yes")
COIN_DEBOUNCE_MS = int(os.getenv("COIN_DEBOUNCE_MS", "20"))
COIN_INTER_PULSE_GAP_MS = int(os.getenv("COIN_INTER_PULSE_GAP_MS", "250"))

if COIN_INTERFACE not in ("arduino", "gpio"):
    raise RuntimeError("COIN_INTERFACE must be 'arduino' or 'gpio'")
if COIN_HEARTBEAT_SECONDS <= 0 or COIN_SESSION_LEASE_SECONDS <= COIN_HEARTBEAT_SECONDS:
    raise RuntimeError("COIN_SESSION_LEASE_SECONDS must be greater than COIN_HEARTBEAT_SECONDS")


def _load_pulse_mapping() -> dict[int, int]:
    raw = os.getenv("COIN_PULSE_MAP", "{}")
    try:
        parsed = json.loads(raw)
        mapping = {int(pulses): int(value) for pulses, value in parsed.items()}
        if any(pulses <= 0 or value <= 0 or value > 1000 for pulses, value in mapping.items()):
            raise ValueError("pulse counts must be positive and values must be between 1 and 1000")
        return mapping
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Invalid COIN_PULSE_MAP: {exc}") from exc


COIN_PULSE_MAP = _load_pulse_mapping()

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

# Admin Panel Settings & Fail-Fast Startup Validation
import logging
logger = logging.getLogger("admin_config")

def reload_admin_config():
    global ADMIN_USERNAME, ADMIN_PASSWORD_HASH, ADMIN_JWT_SECRET, ADMIN_TOKEN_EXPIRE_HOURS, IS_DEFAULT_CREDENTIALS
    if os.path.exists("/opt/pisowifi/.env"):
        load_dotenv("/opt/pisowifi/.env", interpolate=False, override=True)
    local_env = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(local_env):
        load_dotenv(local_env, interpolate=False, override=True)

    ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin").strip()
    ADMIN_PASSWORD_HASH = os.getenv("ADMIN_PASSWORD_HASH", "").strip().strip("'\"")
    ADMIN_JWT_SECRET = os.getenv("ADMIN_JWT_SECRET", "").strip().strip("'\"")

    try:
        ADMIN_TOKEN_EXPIRE_HOURS = int(os.getenv("ADMIN_TOKEN_EXPIRE_HOURS", "2"))
    except ValueError:
        ADMIN_TOKEN_EXPIRE_HOURS = 2

    is_default_hash = False
    try:
        import bcrypt
        is_default_hash = bcrypt.checkpw("admin123".encode("utf-8"), ADMIN_PASSWORD_HASH.encode("utf-8"))
    except Exception:
        pass
    IS_DEFAULT_CREDENTIALS = (ADMIN_USERNAME == "admin") and is_default_hash

ADMIN_USERNAME = ""
ADMIN_PASSWORD_HASH = ""
ADMIN_JWT_SECRET = ""
ADMIN_TOKEN_EXPIRE_HOURS = 2
IS_DEFAULT_CREDENTIALS = False

reload_admin_config()

if not ADMIN_USERNAME or len(ADMIN_USERNAME) < 3:
    msg = "Configuration Error: ADMIN_USERNAME is missing, empty, or too short (minimum 3 characters)."
    logger.critical(msg)
    raise RuntimeError(msg)

if not ADMIN_PASSWORD_HASH:
    msg = "Configuration Error: ADMIN_PASSWORD_HASH is missing or empty in environment (.env). Bcrypt hash authentication is required for production."
    logger.critical(msg)
    raise RuntimeError(msg)

# Validate bcrypt hash structure and salt format at startup
try:
    import bcrypt
    # Perform a dry-run validation check against the configured hash
    bcrypt.checkpw("dry_run_validation".encode("utf-8"), ADMIN_PASSWORD_HASH.encode("utf-8"))
except ValueError as exc:
    msg = f"Configuration Error: ADMIN_PASSWORD_HASH is malformed or contains an invalid salt structure: {exc}"
    logger.critical(msg)
    raise RuntimeError(msg)
except Exception as exc:
    msg = f"Configuration Error: ADMIN_PASSWORD_HASH validation failed: {exc}"
    logger.critical(msg)
    raise RuntimeError(msg)

if not ADMIN_JWT_SECRET or len(ADMIN_JWT_SECRET) < 16:
    msg = "Configuration Error: ADMIN_JWT_SECRET is missing, empty, or insecure (minimum 16 characters required)."
    logger.critical(msg)
    raise RuntimeError(msg)

if IS_DEFAULT_CREDENTIALS:
    logger.critical("CRITICAL SECURITY WARNING: Default credentials (admin / admin123) are detected! Please update ADMIN_PASSWORD_HASH in .env immediately.")

# Detect weak/predictable JWT secrets (common defaults or low-complexity patterns)
_WEAK_JWT_PATTERNS = ["secret", "jwt_secret", "change_me", "password", "default", "key", "token", "admin"]
_jwt_lower = ADMIN_JWT_SECRET.lower().strip()
if any(pattern in _jwt_lower for pattern in _WEAK_JWT_PATTERNS) and len(set(ADMIN_JWT_SECRET)) < 10:
    logger.warning(
        "SECURITY WARNING: ADMIN_JWT_SECRET appears weak or predictable. "
        "Generate a strong random secret using: openssl rand -hex 32"
    )
