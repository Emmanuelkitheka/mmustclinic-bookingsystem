"""Create an admin account from the terminal.

Run:
    python create_admin.py

The password is hashed before it is stored in MySQL.
"""

import getpass
import mysql.connector
from werkzeug.security import generate_password_hash
from config import Config


name = input("Admin name: ").strip()
email = input("Admin email: ").strip().lower()
password = getpass.getpass("Admin password (8+ characters): ")

if len(password) < 8:
    raise SystemExit("Password must contain at least 8 characters.")

db = mysql.connector.connect(
    host=Config.MYSQL_HOST,
    port=Config.MYSQL_PORT,
    user=Config.MYSQL_USER,
    password=Config.MYSQL_PASSWORD,
    database=Config.MYSQL_DATABASE,
)
cursor = db.cursor()

cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
if cursor.fetchone():
    raise SystemExit("An account with that email already exists.")

cursor.execute(
    "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'admin')",
    (name, email, generate_password_hash(password)),
)
db.commit()
cursor.close()
db.close()

print("Admin account created successfully.")
