from recovery.database_recovery import DatabaseRecovery

print("Waiting for MariaDB...")

DatabaseRecovery().wait_until_available()

print("Database Ready.")

