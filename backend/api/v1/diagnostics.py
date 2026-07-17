import os
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from utils.api_response import success
import config

router = APIRouter(prefix="/diagnostics", tags=["Diagnostics"])


@router.get("")
def get_diagnostics(db: Session = Depends(get_db)):
    # 1. DB connection check
    db_connected = False
    db_message = ""
    try:
        db.execute(text("SELECT 1"))
        db_connected = True
        db_message = "Connected successfully"
    except Exception as exc:
        db_message = str(exc)

    # 2. File permissions check
    run_dir_exists = os.path.exists(config.RUN_DIR)
    run_dir_writable = os.access(config.RUN_DIR, os.W_OK) if run_dir_exists else False

    # 3. Tool availability check
    tools = {}
    for name, path in [
        ("nftables", config.PATH_NFT),
        ("tc", config.PATH_TC),
        ("ip", config.PATH_IP),
        ("modprobe", config.PATH_MODPROBE)
    ]:
        exists = os.path.exists(path)
        executable = os.access(path, os.X_OK) if exists else False
        tools[name] = {
            "path": path,
            "exists": exists,
            "executable": executable
        }

    # 4. Serial Port status check
    serial_port = config.SERIAL_PORT
    serial_connected = False
    serial_driver = config.SERIAL_DRIVER

    try:
        if serial_driver.lower() == "mock":
            serial_connected = True
            serial_port = "MOCK"
        elif serial_port and serial_port != "AUTO":
            serial_connected = os.path.exists(serial_port)
        else:
            from coin_serial.device_detector import detect_serial_device
            detected = detect_serial_device()
            if detected:
                serial_port = detected
                serial_connected = os.path.exists(detected)
    except Exception:
        pass

    data = {
        "database": {
            "connected": db_connected,
            "details": db_message
        },
        "filesystem": {
            "run_dir": config.RUN_DIR,
            "exists": run_dir_exists,
            "writable": run_dir_writable
        },
        "tools": tools,
        "serial": {
            "port": serial_port,
            "connected": serial_connected,
            "driver": serial_driver
        },
        "admin_security": {
            "default_credentials_detected": config.IS_DEFAULT_CREDENTIALS,
            "plaintext_password_mode": config.PLAINTEXT_MODE,
            "rate_limiter_active": True,
            "admin_auth_mode": "cookie-jwt"
        }
    }

    # Overall health evaluation: mark unhealthy if default credentials are detected for hardening
    overall_healthy = db_connected and run_dir_writable and all(t["exists"] for t in tools.values()) and not config.IS_DEFAULT_CREDENTIALS
    if serial_driver.lower() != "mock":
        overall_healthy = overall_healthy and serial_connected

    return success(
        data=data,
        message="Diagnostics compiled successfully" if overall_healthy else "Diagnostics completed with warnings"
    )
