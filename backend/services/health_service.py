class HealthService:

    def get_status(self):

        return {
            "database": "healthy",
            "firewall": "healthy",
            "serial": "healthy",
            "network": "healthy",
        }
