import logging

logger = logging.getLogger(__name__)


class FirewallRecovery:
    """
    Rebuilds the authenticated nftables set from
    all ACTIVE sessions stored in the database.
    """

    def __init__(
        self,
        session_repository,
        firewall_service,
    ):
        self.session_repository = session_repository
        self.firewall_service = firewall_service

    def rebuild(self):
        logger.info("Starting firewall rebuild...")

        self.firewall_service.flush()

        sessions = self.session_repository.get_active_sessions()

        restored = 0

        for session in sessions:

            client = session.client

            if not client:
                continue

            if not client.current_ip:
                continue

            self.firewall_service.authorize(client.current_ip)

            restored += 1

        logger.info(
            "Firewall rebuild complete. Restored %s clients.",
            restored,
        )

        return restored
