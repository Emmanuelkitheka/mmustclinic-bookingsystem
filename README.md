# Clinic Appointment Booking System

A university Computer Science project built with Python Flask, MySQL, Jinja2, HTML, CSS and JavaScript.

The application supports patient registration and login, doctor browsing, appointment booking, patient appointment management, and an authorized admin/staff area for managing doctors, patients and appointment statuses.

## Technologies

- Python 3.10+
- Flask
- Jinja2
- MySQL
- mysql-connector-python
- HTML5
- CSS3
- JavaScript
- Werkzeug password hashing

## Project structure

```text
clinic_booking_system/
├── app.py
├── config.py
├── create_admin.py
├── requirements.txt
├── .env
├── README.md
├── database/
│   └── schema.sql
├── templates/
│   ├── base.html
│   ├── index.html
│   ├── login.html
│   ├── register.html
│   ├── doctors.html
│   ├── error.html
│   ├── patient/
│   │   ├── dashboard.html
│   │   └── book_appointment.html
│   └── admin/
│       ├── dashboard.html
│       ├── doctors.html
│       └── patients.html
└── static/
    ├── css/
    │   └── style.css
    └── js/
        └── script.js
```

### Main files

- `app.py`: Flask application, routes, authentication, validation and database operations.
- `config.py`: Loads environment variables and application configuration.
- `create_admin.py`: Creates a hashed admin account from the terminal.
- `database/schema.sql`: Creates the MySQL database and tables.
- `templates/`: Jinja2 pages shown by Flask.
- `static/css/style.css`: Clinic interface styling.
- `static/js/script.js`: Small browser-side enhancements.
- `.env`: Configuration template. Copy it to `.env` and enter local values.
- `requirements.txt`: Python packages required by the project.

## Database design

The core tables are:

1. `users`
   - Stores login identity and role.
   - Passwords are stored as secure hashes, not plain text.

2. `patients`
   - Extends a patient user with patient-specific contact information.

3. `doctors`
   - Stores doctor name, specialization, contact, availability and active/inactive status.

4. `appointments`
   - Links patients to doctors and stores date, time, reason, status and creation time.

Foreign keys enforce the relationships. Parameterized MySQL queries are used throughout the Flask routes.

## Installation

### 1. Create a virtual environment

Windows:

```powershell
python -m venv venv
venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure MySQL

Create a `.env` file by copying `.env.example`.

Example for a local MySQL server:

```text
FLASK_SECRET_KEY=replace-with-a-long-random-secret
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=clinic_booking
```

Do not commit `.env` to GitHub.

If your MySQL server uses port `3307`, set:

```text
MYSQL_PORT=3307
```

### 4. Create the database

Open MySQL Workbench or the MySQL command line and run:

```sql
SOURCE database/schema.sql;
```

Alternatively, open `database/schema.sql` in MySQL Workbench and execute it.

### 5. Create an admin account

With the virtual environment active:

```bash
python create_admin.py
```

Enter the administrator name, email and password when prompted.

### 6. Run Flask

```bash
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## Main workflow

### Patient

1. Register an account.
2. Log in.
3. View active doctors.
4. Open the booking page.
5. Select doctor, date and time.
6. Submit the appointment reason.
7. View the request from the patient dashboard.
8. Wait for staff confirmation.
9. Cancel a pending or confirmed appointment when necessary.

### Admin/staff

1. Run `create_admin.py` once.
2. Log in with the admin account.
3. Open the admin dashboard.
4. Add or deactivate doctors.
5. View registered patients.
6. Review appointments.
7. Change appointment status to Pending, Confirmed, Completed or Cancelled.

## Double-booking protection

Before inserting an appointment, the Flask route checks whether the same doctor already has an active appointment for the selected date and time. Cancelled appointments do not block the slot.

For production use, the application should also add a database-level uniqueness strategy or transaction/locking approach to protect against simultaneous booking requests.

## Security notes

- Passwords use Werkzeug's password hashing.
- Session authentication protects patient and admin pages.
- Role checks protect admin routes.
- SQL queries use `%s` parameters instead of string concatenation.
- Sensitive credentials are read from environment variables.
- Input length and basic email/password validation are included.
- Flask error handlers provide user-friendly error pages.

For a production deployment, also configure HTTPS, secure cookie settings, CSRF protection, stronger audit logging and database transaction locking.

## Learning notes

The project intentionally keeps the Flask architecture straightforward. Routes directly demonstrate:

- how Flask receives form data,
- how sessions identify logged-in users,
- how decorators protect routes,
- how `mysql.connector` executes parameterized SQL,
- how Jinja2 renders database results,
- how HTML forms send POST requests,
- how database foreign keys connect users, patients, doctors and appointments.

This makes the project suitable for studying Flask before introducing larger application architectures.
