from services.health_service import HealthService


def test_health():

    service = HealthService()

    result = service.get_status()

    assert result["database"] == "healthy"
