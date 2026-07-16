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

SESSION_CHECK_INTERVAL = int(os.getenv("SESSION_CHECK_INTERVAL", "60"))
BACKUP_DIRECTORY = os.getenv("BACKUP_DIRECTORY", "/tmp")
LOG_DIRECTORY = os.getenv("LOG_DIRECTORY", "/tmp")
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