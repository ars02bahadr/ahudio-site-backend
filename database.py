import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# Dosyanın bulunduğu dizini tam yol olarak al
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "data.db")

SQLALCHEMY_DATABASE_URL = f"sqlite:///{db_path}"

# sqlite için check_same_thread False
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency: route içinde kullanmak için
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()