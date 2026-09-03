import os
import json
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timezone
import config

_SENSITIVE_KEYS = {"password", "secret", "token", "hash", "jwt", "key", "credit_card", "authorization"}


def _sanitize_details(data: dict) -> dict:
    sanitized = {}
    for k, v in data.items():
        if any(sens in k.lower() for sens in _SENSITIVE_KEYS):
            sanitized[k] = "[REDACTED]"
        elif isinstance(v, dict):
            sanitized[k] = _sanitize_details(v)
        else:
            sanitized[k] = v
    return sanitized


class JsonLogFormatter(logging.Formatter):
    """Formats log records as structured JSON lines."""
    def format(self, record: logging.LogRecord) -> str:
        msg = record.getMessage()
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
        }
        try:
            parsed = json.loads(msg)
            if isinstance(parsed, dict):
                log_obj.update(parsed)
            else:
                log_obj["message"] = msg
        except Exception:
            log_obj["message"] = msg

        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)


_audit_logger = None


def get_audit_logger() -> logging.Logger:
    global _audit_logger
    if _audit_logger is not None:
        return _audit_logger

    audit_dir = os.path.join(config.LOG_DIRECTORY, "audit")
    os.makedirs(audit_dir, exist_ok=True)
    audit_file = os.path.join(audit_dir, "audit.log")

    logger = logging.getLogger("pisowifi.audit")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = RotatingFileHandler(
        audit_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
    )
    handler.setFormatter(JsonLogFormatter())
    logger.addHandler(handler)
    _audit_logger = logger
    return _audit_logger


def log_audit_event(event_type: str, actor: str, target: str, status: str, details: dict | None = None):
    """
    Records a structured, sanitized audit log event for security monitoring and compliance.
    """
    logger = get_audit_logger()
    safe_details = _sanitize_details(details or {})
    event = {
        "event_type": event_type,
        "actor": actor,
        "target": target,
        "status": status,
        "details": safe_details,
    }
    logger.info(json.dumps(event))
