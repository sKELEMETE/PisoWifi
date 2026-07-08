from services.health_service import HealthService


def test_health():

    service = HealthService()

    result = service.check()

    assert result["database"] == "healthy"
