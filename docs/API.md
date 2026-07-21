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

### 8. `POST /api/v1/voucher/redeem`
- **Method**: POST
- **Purpose**: Redeems an internet access voucher for a client MAC address. Automatically registers new client devices if uninitialized.
- **Request Body**: `{"code": "VOUCHER_CODE", "mac": "XX:XX:XX:XX:XX:XX"}`
- **Response**: `{"success": true, "data": {"session_id": 1, "status": "ACTIVE", "added_minutes": 60}}`

### 9. `POST /api/admin/vouchers`
- **Method**: POST (Admin Auth Required)
- **Purpose**: Creates a single internet access voucher.
- **Request Body**: `{"minutes": 60, "expires_at": "ISO_DATE", "notes": "Optional note"}`
- **Response**: `{"success": true, "data": {"id": 1, "code": "...", "status": "UNUSED", "minutes": 60}}`

### 10. `POST /api/admin/vouchers/bulk`
- **Method**: POST (Admin Auth Required)
- **Purpose**: Creates multiple internet access vouchers in bulk with collision handling.
- **Request Body**: `{"count": 10, "minutes": 60}`
- **Response**: `{"success": true, "data": {"created": 10, "vouchers": [...]}}`

### 11. `GET /api/admin/vouchers`
- **Method**: GET (Admin Auth Required)
- **Purpose**: Lists vouchers with pagination, status filtering, and column sorting.
- **Query Parameters**: `status_filter`, `limit`, `offset`, `order_by`, `order_desc`

### 12. `GET /api/admin/vouchers/export`
- **Method**: GET (Admin Auth Required)
- **Purpose**: Exports vouchers in CSV or JSON format.
- **Query Parameters**: `format` (`csv` or `json`), `status_filter`

