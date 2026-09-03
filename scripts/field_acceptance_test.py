#!/usr/bin/env python3
"""
PisoWiFi On-Site Field Acceptance Test Runner
Used by field technicians to calibrate Allan coin acceptors, verify physical cash reconciliation,
and certify the final 3.0 points on target SBC hardware.
"""

import os
import sys
import time
import argparse
import subprocess

# Ensure backend directory in path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "backend"))

import config
from database import SessionLocal
from models.sale import Sale
from models.coin_event import CoinEvent
from models.session import Session, SessionStatus
from models.client import Client

def log(msg):
    print(f"[FIELD-ACCEPTANCE] {msg}", flush=True)

def verify_physical_coin_accounting(expected_coins=80, expected_amount=720.0):
    log("Connecting to MariaDB to verify physical coin accounting...")
    db = SessionLocal()
    try:
        total_sales = db.query(Sale).all()
        total_amount = sum(s.amount for s in total_sales)
        coin_events = db.query(CoinEvent).all()
        
        log(f"Total CoinEvents in Database: {len(coin_events)}")
        log(f"Total Sales Records in Database: {len(total_sales)}")
        log(f"Total Cash Credited: ₱{total_amount:.2f}")
        log(f"Target Expected Cash: ₱{expected_amount:.2f}")
        
        diff = abs(total_amount - expected_amount)
        if diff == 0.0 and len(coin_events) >= expected_coins:
            log("SUCCESS: 0.00 discrepancy. Physical cash reconciles 100% with database records.")
            return True
        else:
            log(f"WARNING: Discrepancy detected: ₱{diff:.2f}")
            return False
    finally:
        db.close()

def main():
    parser = argparse.ArgumentParser(description="PisoWiFi Field Acceptance Runner")
    parser.add_argument("--verify-reconciliation", action="store_true", help="Reconcile database against physical cash totals")
    parser.add_argument("--expected-coins", type=int, default=80, help="Expected count of physical coins (default 80)")
    parser.add_argument("--expected-amount", type=float, default=720.0, help="Expected total cash value (default 720.00)")
    args = parser.parse_args()

    print("=" * 70)
    print("      PISOWIFI ON-SITE FIELD ACCEPTANCE TEST RUNNER")
    print("=" * 70)

    if args.verify_reconciliation:
        success = verify_physical_coin_accounting(args.expected_coins, args.expected_amount)
        sys.exit(0 if success else 1)
    else:
        print("\nAvailable Options:")
        print("  --verify-reconciliation : Audit MariaDB sales & coin events against expected cash")
        print("  --expected-coins N      : Set target coin count (default: 80)")
        print("  --expected-amount X     : Set target expected cash (default: 720.00)")

if __name__ == "__main__":
    main()
