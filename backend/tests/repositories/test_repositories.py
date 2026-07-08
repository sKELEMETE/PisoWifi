from sqlalchemy import text

from database import SessionLocal


def test_database_connection():
    db = SessionLocal()

    result = db.execute(text("SELECT 1"))

    assert result.scalar() == 1

    db.close()
