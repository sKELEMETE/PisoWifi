# API Documentation

## Endpoints

### 1. `GET /api/v1/health`
- **Method**: GET
- **Purpose**: Server health check.
- **Response**: `{"status": "ok", "version": "1.0.0"}`

### 2. `POST /api/v1/coin/activate/{mac_address}`
- **Method**: POST
- **Purpose**: Reserves the hardware coin slot exclusively for this MAC address. Starts a 30-second reservation timer. Enables the coin acceptor hardware.
- **Request Parameters**: `mac_address` (Path string)
- **Response**: `{"success": true, "message": "Coin slot reserved"}`
- **Error Responses**: `409 Conflict` if the slot is currently reserved by another MAC address.
- **Used Services**: `CoinService`

### 3. `POST /api/v1/coin/release/{mac_address}`
- **Method**: POST
- **Purpose**: Finalizes the coin insertion process. Reads total inserted coins, converts to time via `PricingService`, updates the user's session time, and releases the hardware lock.
- **Request Parameters**: `mac_address` (Path string)
- **Response**: `{"success": true, "added_seconds": 3600, "total_seconds": 7200}`
- **Used Services**: `CoinService`, `SessionService`, `PricingService`

### 4. `POST /api/v1/session/pause/{mac_address}`
- **Method**: POST
- **Purpose**: Pauses an active session. Revokes internet via firewall, removes bandwidth shapers, and freezes the remaining time countdown.
- **Response**: `{"success": true, "status": "PAUSED"}`
- **Used Services**: `SessionService`, `FirewallService`, `BandwidthService`

### 5. `POST /api/v1/session/resume/{mac_address}`
- **Method**: POST
- **Purpose**: Resumes a paused session. Re-adds firewall internet access and reinstates 10 Mbps bandwidth shapers.
- **Response**: `{"success": true, "status": "ACTIVE"}`
- **Used Services**: `SessionService`, `FirewallService`, `BandwidthService`

### 6. `GET /api/v1/session/{mac_address}`
- **Method**: GET
- **Purpose**: Retrieves the current session status for a specific client.
- **Response**: `{"mac_address": "XX:XX:XX:XX:XX:XX", "status": "ACTIVE", "remaining_seconds": 1500}`

### 7. `GET /api/admin/dashboard`
- **Method**: GET
- **Purpose**: Admin dashboard statistics, revenue metrics, active client listing, and diagnostics health details.
- **Response**: Serves consolidated database sales data (today, week, month), lists active clients, and returns cached diagnostics stats (such as CPU tick utilization, memory usage, disk usage, WAN connect, and DNS online statuses).
- **Optimization**: Uses `HealthCacheService` to serve diagnostic stats instantly from cache under 5ms.
