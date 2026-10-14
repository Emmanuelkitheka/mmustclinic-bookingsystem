import os
from datetime import datetime
from functools import wraps
from itsdangerous import URLSafeTimedSerializer
from markupsafe import Markup


import mysql.connector
from flask import Flask, flash, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config

app = Flask(__name__)
app.config.from_object(Config)
serializer = URLSafeTimedSerializer(app.secret_key)



def get_db():
    """Create a new MySQL connection for a request."""
    return mysql.connector.connect(
        host=app.config["MYSQL_HOST"],
        port=app.config["MYSQL_PORT"],
        user=app.config["MYSQL_USER"],
        password=app.config["MYSQL_PASSWORD"],
        database=app.config["MYSQL_DATABASE"],
    )


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(role):
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if "user_id" not in session:
                flash("Please log in to continue.", "warning")
                return redirect(url_for("login"))
            if session.get("role") != role:
                flash("You are not authorized to access that page.", "danger")
                return redirect(url_for("index"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def valid_email(email):
    return "@" in email and "." in email.rsplit("@", 1)[-1]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        phone = request.form.get("phone", "").strip()

        if not name or not email or not password:
            flash("Name, email and password are required.", "danger")
            return render_template("register.html")
        if not valid_email(email):
            flash("Enter a valid email address.", "danger")
            return render_template("register.html")
        if len(password) < 8:
            flash("Password must contain at least 8 characters.", "danger")
            return render_template("register.html")

        db = get_db()
        cursor = db.cursor()
        try:
            cursor.execute("SELECT user_id FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                flash("An account with that email already exists.", "warning")
                return render_template("register.html")

            cursor.execute(
                "INSERT INTO users (name, email, password_hash, role) VALUES (%s, %s, %s, 'patient')",
                (name, email, generate_password_hash(password)),
            )
            user_id = cursor.lastrowid
            cursor.execute(
                "INSERT INTO patients (user_id, phone) VALUES (%s, %s)",
                (user_id, phone or None),
            )
            db.commit()
            flash("Registration successful. You can now log in.", "success")
            return redirect(url_for("login"))
        except Exception as e:
             db.rollback()
             print(f"REGISTER ERROR: {e}")
             import traceback; traceback.print_exc()
             flash(f"Error: {e}", "danger")
        finally:
            cursor.close()
            db.close()

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip()
        password = request.form["password"]
        db = get_db()
        cursor = db.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
            user = cursor.fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session["user_id"] = user["user_id"]
                session["role"] = user["role"]
                session["username"] = user["name"]
                session["email"] = user["email"]
                if str(user["role"]).strip().lower() == "admin":
                    return redirect(url_for("admin_dashboard"))
                elif str(user["role"]).strip().lower() == "doctor":
                    return redirect(url_for("doctor_dashboard"))
                else:
                    return redirect(url_for("patient_dashboard"))
        finally:
            cursor.close()
            db.close()
        flash("Invalid email or password", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


@app.route("/doctors")
def doctors():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        try:
            cursor.execute(
                "SELECT doctor_id, name, specialization, phone, availability, status "
                "FROM doctors WHERE status = 'Active' ORDER BY name"
            )
            doctor_rows = cursor.fetchall()
        except Exception:
            db.rollback()
            cursor.execute(
                "SELECT d.doctor_id, u.full_name as name, d.specialization, "
                "COALESCE(d.phone, u.phone) as phone, d.availability, d.status "
                "FROM doctors d JOIN users u ON d.user_id = u.user_id "
                "WHERE d.status = 'Active' ORDER BY u.full_name"
            )
            doctor_rows = cursor.fetchall()
    finally:
        cursor.close()
        db.close()
    return render_template("doctors.html", doctors=doctor_rows)


@app.route("/patient/dashboard")
@role_required("patient")
def patient_dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT user_id FROM patients WHERE user_id = %s", (session["user_id"],))
        prow = cursor.fetchone()
        if prow:
            real_patient_id = prow['user_id']
        else:
            real_patient_id = session["user_id"]
            cursor.execute("INSERT IGNORE INTO patients (user_id) VALUES (%s)", (real_patient_id,))
            db.commit()

        cursor.execute("""
SELECT p.user_id as patient_id, u.name, u.email, p.phone
FROM patients p
JOIN users u ON p.user_id = u.user_id
WHERE p.user_id = %s
""", (real_patient_id,))
        patient = cursor.fetchone()

        if not patient:
           patient = {
               "patient_id": real_patient_id, 
               "name": session.get("username", "Patient"), 
               "email": session.get("email", ""),
               "phone": ""
        }

        cursor.execute("""
        SELECT a.*, u.name as doctor_name, d.specialization
        FROM appointments a
        JOIN doctors d ON a.doctor_id = d.doctor_id
        JOIN users u ON d.user_id = u.user_id
        WHERE a.patient_id = %s
        ORDER BY a.appointment_date DESC
        """, (real_patient_id,))
        appointments = cursor.fetchall()
        
        return render_template("patient/dashboard.html", appointments=appointments, patient=patient)
    finally:
        cursor.close()
        db.close()


@app.route("/appointments/book", methods=["GET", "POST"])
@role_required("patient")
def book_appointment():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            "SELECT doctor_id, name, specialization FROM doctors WHERE status = 'Active'"
        )
        doctors_rows = cursor.fetchall()

        if request.method == "POST":
            doctor_id = request.form.get("doctor_id", "").strip()
            appointment_date = request.form.get("appointment_date", "").strip()
            appointment_time = request.form.get("appointment_time", "").strip()
            reason = request.form.get("reason", "").strip()

            if not doctor_id or not appointment_date or not appointment_time:
                flash("Doctor, date and time are required.", "danger")
                return render_template("patient/book_appointment.html", doctors=doctors_rows)

            try:
                chosen_date = datetime.strptime(appointment_date, "%Y-%m-%d").date()
                if chosen_date < datetime.now().date():
                    flash("Appointment date cannot be in the past.", "danger")
                    return render_template("patient/book_appointment.html", doctors=doctors_rows)
            except ValueError:
                flash("Invalid date format.", "danger")
                return render_template("patient/book_appointment.html", doctors=doctors_rows)

            try:
                cursor.execute("SELECT patient_id FROM patients WHERE user_id = %s", (session["user_id"],))
                prow = cursor.fetchone()
                if prow:
                    real_patient_id = prow['patient_id'] if isinstance(prow, dict) else prow[0]
                else:
                    real_patient_id = session["user_id"]

                cursor.execute(
                    """INSERT INTO appointments
                       (patient_id, doctor_id, appointment_date, appointment_time, reason, status)
                       VALUES (%s, %s, %s, %s, %s, 'Pending')""",
                    (real_patient_id, doctor_id, appointment_date, appointment_time, reason)
                )
                db.commit()
                print(f"---SMS SENT to phone in users table: Appointment {appointment_date} {appointment_time} for patient_id {real_patient_id}---")
                flash("Appointment booked successfully. Sms notification has been logged!", "success")
                return redirect(url_for("patient_dashboard"))
            except Exception as e:
                db.rollback()
                flash(f"Error booking appointment: {e}", "danger")
                return render_template("patient/book_appointment.html", doctors=doctors_rows)

        return render_template("patient/book_appointment.html", doctors=doctors_rows)
    finally:
        cursor.close()
        db.close()

                   
  

    return render_template("patient/book_appointment.html", doctors=doctors_rows)


@app.post("/appointments/<int:appointment_id>/cancel")
@role_required("patient")
def cancel_appointment(appointment_id):
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            """UPDATE appointments SET status = 'Cancelled'
               WHERE appointment_id = %s AND patient_id = %s
                 AND status IN ('Pending', 'Confirmed')""",
            (appointment_id, session["user_id"]),
        )
        db.commit()
        flash("Appointment cancelled if it was eligible for cancellation.", "success")
    finally:
        cursor.close()
        db.close()
    return redirect(url_for("patient_dashboard"))


@app.route("/admin")
@role_required("admin")
def admin_dashboard():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COUNT(*) AS total FROM patients")
        patient_count = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) AS total FROM doctors")
        doctor_count = cursor.fetchone()["total"]
        cursor.execute("SELECT COUNT(*) AS total FROM appointments")
        appointment_count = cursor.fetchone()["total"]
        cursor.execute(
            """SELECT a.appointment_id, p.name AS patient_name, du.name AS doctor_name,
                    a.appointment_date, a.appointment_time, a.status
            FROM appointments a
            JOIN patients pt ON a.patient_id = pt.user_id
            JOIN users p ON pt.user_id = p.user_id
            JOIN doctors d ON a.doctor_id = d.doctor_id
            JOIN users du ON d.user_id = du.user_id
            ORDER BY a.appointment_date DESC, a.appointment_time DESC"""
        )
        appointments = cursor.fetchall()
    finally:
        cursor.close()
        db.close()

    return render_template(
        "admin/dashboard.html",
        patient_count=patient_count,
        doctor_count=doctor_count,
        appointment_count=appointment_count,
        appointments=appointments,
    )
  


@app.route("/admin/doctors", methods=["GET", "POST"])
@role_required("admin")
def admin_doctors():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            specialization = request.form.get("specialization", "").strip()
            phone = request.form.get("phone", "").strip()
            availability = request.form.get("availability", "").strip()
            email = request.form.get("email", "").strip() or f"doctor_{int(__import__('time').time())}@clinic.local"
            password = request.form.get("password", "").strip() or "doctor123"

            if not name or not specialization:
                flash("Doctor name and specialization are required.", "danger")
            else:
                try:
                    cursor.execute(
                        """INSERT INTO doctors (name, specialization, phone, availability, status)
                           VALUES (%s, %s, %s, %s, 'Active')""",
                        (name, specialization, phone or None, availability or None),
                    )
                    db.commit()
                    flash("Doctor added.", "success")
                except Exception:
                    db.rollback()
                    inserted = False
                    for user_col in ["full_name", "name", "username"]:
                        try:
                            cursor.execute(
                                f"INSERT INTO users ({user_col}, email, password_hash, role, phone) VALUES (%s, %s, %s, 'doctor', %s)",
                                (name, email, password, phone or None),
                            )
                            user_id = cursor.lastrowid
                            cursor.execute(
                                "INSERT INTO doctors (user_id, specialization, availability, status) VALUES (%s, %s, %s, 'Active')",
                                (user_id, specialization, availability or None),
                            )
                            db.commit()
                            flash(f"Doctor added (users.{user_col}).", "success")
                            inserted = True
                            break
                        except Exception as e_inner:
                            db.rollback()
                            last_err = e_inner
                            continue
                    if not inserted:
                        flash(f"Failed to add doctor: {last_err}", "danger")


        try:
            cursor.execute("SELECT * FROM doctors ORDER BY doctor_id DESC")
            doctors_rows = cursor.fetchall()
        except Exception:
            db.rollback()
            try:
                cursor.execute(
                    "SELECT d.doctor_id, u.full_name as name, d.specialization, COALESCE(d.phone, u.phone) as phone, d.availability, d.status "
                    "FROM doctors d JOIN users u ON d.user_id = u.user_id ORDER BY d.doctor_id DESC"
                )
                doctors_rows = cursor.fetchall()
            except Exception:
                db.rollback()
                cursor.execute(
                    "SELECT d.doctor_id, u.name as name, d.specialization, COALESCE(d.phone, u.phone) as phone, d.availability, d.status "
                    "FROM doctors d JOIN users u ON d.user_id = u.user_id ORDER BY d.doctor_id DESC"
                )
                doctors_rows = cursor.fetchall()
    finally:
        cursor.close()
        db.close()
    return render_template("admin/doctors.html", doctors=doctors_rows)


@app.post("/admin/doctors/<int:doctor_id>/toggle")
@role_required("admin")
def toggle_doctor(doctor_id):
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            """UPDATE doctors
               SET status = CASE WHEN status = 'Active' THEN 'Inactive' ELSE 'Active' END
               WHERE doctor_id = %s""",
            (doctor_id,),
        )
        db.commit()
        flash("Doctor status updated.", "success")
    finally:
        cursor.close()
        db.close()
    return redirect(url_for("admin_doctors"))


@app.post("/admin/appointments/<int:appointment_id>/status")
@role_required("admin")
def update_appointment_status(appointment_id):
    status = request.form.get("status", "")
    allowed = {"Pending", "Confirmed", "Completed", "Cancelled"}
    if status not in allowed:
        flash("Invalid appointment status.", "danger")
        return redirect(url_for("admin_dashboard"))

    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(
            "UPDATE appointments SET status = %s WHERE appointment_id = %s",
            (status, appointment_id),
        )
        db.commit()
        flash("Appointment status updated.", "success")
    finally:
        cursor.close()
        db.close()
    return redirect(url_for("admin_dashboard"))


@app.route("/admin/patients")
@role_required("admin")
def admin_patients():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute(
            """SELECT u.user_id, u.name, u.email, p.phone, u.created_at
               FROM users u
               JOIN patients p ON p.user_id = u.user_id
               ORDER BY u.name"""
        )
        patients = cursor.fetchall()
    finally:
        cursor.close()
        db.close()
    return render_template("admin/patients.html", patients=patients)


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", title="Page not found", message="The requested page does not exist."), 404


@app.errorhandler(500)
def server_error(_error):
    return render_template("error.html", title="Server error", message="Something went wrong. Please try again."), 500

@app.route("/doctor/dashboard")
@login_required
@role_required("doctor")
def doctor_dashboard():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT a.appointment_id, a.appointment_date, a.status, u.full_name as patient_name
            FROM appointments a
            JOIN users u ON a.patient_id = u.user_id
            WHERE a.doctor_id = %s
            ORDER BY a.appointment_date DESC
        """, (session["user_id"],))
        appointments = cursor.fetchall()
    finally:
        cursor.close()
        db.close()

    return render_template("doctor/dashboard.html", appointments=appointments)

from werkzeug.security import check_password_hash, generate_password_hash

@app.route("/doctor/change-password", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def doctor_change_password():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        doctor_id = session.get('user_id')
        
        if request.method == "POST":
            current = request.form.get("current_password")
            new = request.form.get("new_password")
            confirm = request.form.get("confirm_password")

            if new != confirm:
                flash("New passwords do not match!", "danger")
                return redirect(url_for('doctor_change_password'))

            cursor.execute("SELECT password_hash FROM users WHERE user_id = %s", (doctor_id,))
            user = cursor.fetchone()
            
            if not user:
                flash("User not found!", "danger")
                return redirect(url_for('doctor_change_password'))

            stored_password = user['password_hash']
            password_is_correct = False
            
            
            try:
                from werkzeug.security import check_password_hash
                if check_password_hash(stored_password, current):
                    password_is_correct = True
            except:
                pass
            
            if stored_password == current:
                password_is_correct = True

            if not password_is_correct:
                flash("Current password is wrong!", "danger")
                return redirect(url_for('doctor_change_password'))

            
            from werkzeug.security import generate_password_hash
            new_hash = generate_password_hash(new)
            cursor.execute("UPDATE users SET password_hash = %s WHERE user_id = %s", (new_hash, doctor_id))
            db.commit()
            
            flash("Password changed! Now you can use new password.", "success")
            return redirect(url_for('doctor_dashboard'))

        return render_template("doctor/change-password.html")
    finally:
        cursor.close()
        db.close()

@app.route("/doctor/change-email", methods=["GET", "POST"])
@login_required
@role_required("doctor")
def doctor_change_email():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    try:
        doctor_id = session.get('user_id')
        cursor.execute("SELECT email FROM users WHERE user_id = %s", (doctor_id,))
        row = cursor.fetchone()
        current_email = row['email'] if row else ""

        if request.method == "POST":
            new_email = request.form.get("new_email", "").strip().lower()
            password = request.form.get("password", "")

            if not new_email or not password:
                flash("All fields required!", "danger")
                return redirect(url_for('doctor_change_email'))

            cursor.execute("SELECT password_hash FROM users WHERE user_id = %s", (doctor_id,))
            user = cursor.fetchone()

            if not user or not check_password_hash(user['password_hash'], password):
                flash("Wrong password! Email not changed.", "danger")
                return redirect(url_for('doctor_change_email'))

            cursor.execute("SELECT user_id FROM users WHERE email = %s AND user_id != %s", (new_email, doctor_id))
            if cursor.fetchone():
                flash("This email is already taken!", "danger")
                return redirect(url_for('doctor_change_email'))

            cursor.execute("UPDATE users SET email = %s WHERE user_id = %s", (new_email, doctor_id))
            db.commit()
            flash(f"Email changed to {new_email}. Use new email next login.", "success")
            return redirect(url_for('doctor_change_email'))

        return render_template("doctor/change-email.html", current_email=current_email)

    finally:
        cursor.close()
        db.close()

@app.route("/doctor/appointment/<int:appointment_id>/<string:action>")
@login_required
@role_required("doctor")
def doctor_action(appointment_id, action):
    new_status = "approved" if action == "approve" else "rejected"
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute("UPDATE appointments SET status = %s WHERE appointment_id = %s AND doctor_id = %s",
                       (new_status, appointment_id, session["user_id"]))
        db.commit()
    finally:
        cursor.close()
        db.close()
    flash(f"Appointment {new_status}.", "success")
    return redirect(url_for("doctor_dashboard"))

@app.route('/admin/add_doctor', methods=['GET', 'POST'])
def add_doctor():
    if 'email' not in session or session.get('role') != 'admin':
        return redirect('/login')

    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        spec = request.form['specialization']
        
        hash_pw = generate_password_hash(password)
        
        cur = mysql.connection.cursor() 
        
        cur.execute("INSERT INTO users (name, email, password_hash, role) VALUES (%s,%s,%s,'doctor')", (name, email, hash_pw))
        cur.execute("INSERT INTO doctors (name, email, specialization) VALUES (%s,%s,%s)", (name, email, spec))
        mysql.connection.commit()
        cur.close()
        
        flash('Doctor added successfully!')
        return redirect('/admin/doctors')

    return render_template('admin_add_doctor.html')

@app.route('/admin/deactivate_doctor/<int:doctor_id>')
def deactivate_doctor(doctor_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE doctors SET is_active = 0, availability = 'Transferred' WHERE doctor_id = %s", (doctor_id,))
    db.commit()
    cur.close()
    db.close()
    flash('Doctor deactivated - transferred')
    return redirect('/admin/doctors')

@app.route('/admin/activate_doctor/<int:doctor_id>')
def activate_doctor(doctor_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("UPDATE doctors SET is_active = 1, availability = 'Available' WHERE doctor_id = %s", (doctor_id,))
    db.commit()
    cur.close()
    db.close()
    flash('Doctor reactivated')
    return redirect('/admin/doctors')
@app.route('/admin/edit_doctor/<int:doctor_id>', methods=['GET','POST'])
def edit_doctor(doctor_id):
    db = get_db()
    cur = db.cursor(dictionary=True)
    if request.method == 'POST':
        new_time = request.form['availability']
        cur.execute("UPDATE doctors SET availability = %s WHERE doctor_id = %s", (new_time, doctor_id))
        db.commit()
        cur.close()
        db.close()
        return redirect('/admin/doctors')
    cur.execute("SELECT * FROM doctors WHERE doctor_id = %s", (doctor_id,))
    doctor = cur.fetchone()
    cur.close()
    db.close()
    return render_template('admin/edit_doctor.html', doctor=doctor)
# --- FORGOT PASSWORD ---
@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        db = get_db()
        cur = db.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cur.fetchone()
        cur.close()
        db.close()
        if user:
            token = serializer.dumps(email, salt='password-reset')
            link = url_for('reset_password', token=token, _external=True)
            flash(Markup(f'Reset link (demo): <a href="{link}" style="word-break:break-all; color:blue; text-decoration:underline;">CLICK HERE TO RESET</a>'), "info")
            flash("Link expires in 1 hour", "info")
        else:
            flash("If that email exists, a reset link was generated", "info")
        return redirect(url_for('forgot_password'))
    return render_template('forgot_password.html')

@app.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = serializer.loads(token, salt='password-reset', max_age=3600)
    except:
        flash("Link expired or invalid", "danger")
        return redirect(url_for('forgot_password'))
    if request.method == 'POST':
        pwd = request.form['password']
        confirm = request.form['confirm_password']
        if pwd != confirm:
            flash("Passwords don't match", "danger")
            return render_template('reset_password.html')
        hashed = generate_password_hash(pwd)
        db = get_db()
        cur = db.cursor()
        cur.execute("UPDATE users SET password_hash=%s WHERE email=%s", (hashed, email))
        db.commit()
        cur.close()
        db.close()
        flash("Password reset successful! Login now", "success")
        return redirect(url_for('login'))
    return render_template('reset_password.html')
if __name__ == '__main__':
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
