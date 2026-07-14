# PisoWiFi Complete System

## Project Overview
PisoWiFi is a captive portal-based hotspot gateway running on Ubuntu Server. Customers connect to the WiFi Access Point (AP), get redirected to a captive portal, insert coins, and purchase internet time. It integrates a physical coin acceptor (via Arduino), bandwidth shaping per user (10 Mbps), session pausing, and audio feedback.

## Tech Stack
- **Backend**: Python 3.10+, FastAPI, SQLAlchemy, SQLite, Pyserial.
- **Frontend**: React 18, Vite, Zustand (state management), React Router.
- **Web Server**: Nginx (serves React build, intercepts captive portal requests, proxies API and `/sfx/` sounds).
- **Network / Firewall**: `nftables` (for NAT, captive portal redirection, internet authorization), `tc` (Traffic Control using HTB and IFB for bandwidth shaping).
- **Hardware**: 
  - Ubuntu Server (Core system).
  - Arduino (Serial interface for Coin Acceptor).
  - WiFi Access Point (Providing the network).

## Folder Structure
- `/opt/pisowifi/backend/`: Backend application, API routes, database models, background schedulers.
- `/opt/pisowifi/frontend/`: React frontend application.
- `/opt/pisowifi/sfx/`: Audio files for the centralized sound system.
- `/opt/pisowifi/docs/`: Permanent source-of-truth documentation.

## Installation & Startup
The application runs using `systemd` services.
- Nginx: Serves static files and proxies `/api/` to port 8000.
- Backend Service: `pisowifi-backend.service` (Runs Uvicorn on 127.0.0.1:8000).

## Useful Commands
- **Restart Backend**: `sudo systemctl restart pisowifi-backend`
- **Check Backend Logs**: `sudo journalctl -u pisowifi-backend -f`
- **Restart Nginx**: `sudo systemctl restart nginx`
- **Check Traffic Shaping (Egress)**: `tc class show dev <INTERFACE>`
- **Check Traffic Filters (Egress)**: `tc filter show dev <INTERFACE>`
- **Check IFB Interface (Ingress)**: `tc class show dev ifb0`
