from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from envparse import env

env.read_envfile('config/.env.dev')

POSTGRES_USER = env.str('POSTGRES_USER')
POSTGRES_PASSWORD = env.str('POSTGRES_PASSWORD')
POSTGRES_HOST = env.str('POSTGRES_HOST')
POSTGRES_PORT = env.str('POSTGRES_PORT')
POSTGRES_DB = env.str('POSTGRES_DB')
SQLALCHEMY_DATABASE_URL = f'postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}'

engine = create_engine(
    SQLALCHEMY_DATABASE_URL
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

__all__ = ['engine', 'SessionLocal']

