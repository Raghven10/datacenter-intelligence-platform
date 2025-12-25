
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.audit import register_audit_listeners
import os

# Load database URL from environment or construct from individual variables
DATABASE_URL = os.getenv(
    "POSTGRES_DSN",
    f"postgresql+psycopg2://{os.getenv('POSTGRES_USER', 'postgres')}:"
    f"{os.getenv('POSTGRES_PASSWORD', 'postgres')}@"
    f"{os.getenv('POSTGRES_HOST', 'localhost')}:"
    f"{os.getenv('POSTGRES_PORT', '5432')}/"
    f"{os.getenv('POSTGRES_DB', 'datacenter_db')}"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
register_audit_listeners(SessionLocal)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
