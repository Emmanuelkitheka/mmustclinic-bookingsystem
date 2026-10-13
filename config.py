import os

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_DB = os.getenv("MYSQL_DB") or os.getenv("MYSQL_DATABASE")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE") or os.getenv("MYSQL_DB")

DB_HOST = os.getenv("DB_HOST") or MYSQL_HOST
DB_USER = os.getenv("DB_USER") or MYSQL_USER
DB_PASSWORD = os.getenv("DB_PASSWORD") or MYSQL_PASSWORD
DB_PORT = os.getenv("DB_PORT") or MYSQL_PORT