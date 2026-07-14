# Database Documentation

The project uses SQLite via SQLAlchemy.

## Tables

### 1. `sessions`
Tracks active and paused internet sessions.
- **id** (Integer, Primary Key)
- **mac_address** (String, Unique, Index)
- **ip_address** (String)
- **status** (Enum/String): `ACTIVE`, `PAUSED`, `EXPIRED`
- **remaining_seconds** (Integer): Cached remaining time (updated dynamically or paused).
- **started_at** (DateTime)
- **updated_at** (DateTime)

### 2. `clients`
Tracks devices that have connected to the hotspot, regardless of session status.
- **id** (Integer, Primary Key)
- **mac_address** (String, Unique, Index)
- **first_seen** (DateTime)
- **last_seen** (DateTime)

### 3. `coins_ledger` (or `coins`)
Logs individual physical coin drops for auditing and accounting.
- **id** (Integer, Primary Key)
- **mac_address** (String, Foreign Key -> `sessions.mac_address`)
- **amount** (Float/Integer): Denomination of the coin inserted (e.g. 1, 5, 10).
- **inserted_at** (DateTime)
- **status** (String): `CREDITED`, `PENDING`

### 4. `pricing` (or configuration rules)
Defines conversion rates. (Often hardcoded or kept in a simple key-value table).
- **amount** (Integer) -> **time_seconds** (Integer)
