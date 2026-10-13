import os

class Config:
    MYSQL_HOST = os.getenv("MYSQL_HOST")
    MYSQL_USER = os.getenv("MYSQL_USER")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
    MYSQL_PORT = os.getenv("MYSQL_PORT", "13090")
    MYSQL_DATABASE = os.getenv("MYSQL_DATABASE") or os.getenv("MYSQL_DB") or "defaultdb"
    MYSQL_DB = MYSQL_DATABASE
    
    DB_HOST = os.getenv("DB_HOST") or MYSQL_HOST
    DB_USER = os.getenv("DB_USER") or MYSQL_USER
    DB_PASSWORD = os.getenv("DB_PASSWORD") or MYSQL_PASSWORD
    DB_PORT = os.getenv("DB_PORT") or MYSQL_PORT
    DB_NAME = os.getenv("DB_NAME") or MYSQL_DATABASE
    
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")