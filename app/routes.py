"""All page and REST API routes for the project."""
import os
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, current_app, send_from_directory, abort
from werkzeug.security import generate_password_hash, check_password_hash
from .database import get_db
from .security import (
    logged_in_user, login_required, roles_required, save_audit,
    store_uploaded_file, get_record_permission, make_share_token, expiry_time
)

main_bp = Blueprint("main", __name__)
api_bp = Blueprint("api", __name__)

@main_bp.get("/")
def home():
    return render_template("index.html")

# ------------------------- AUTHENTICATION -------------------------
@api_bp.post("/auth/register")
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    role = data.get("role") or "patient"

    if not name or not email or len(password) < 8:
        return jsonify({"error": "Enter your name, valid email and password (minimum 8 characters)."}), 400
    if role not in ("patient", "doctor"):
        return jsonify({"error": "Only Patient and Doctor self-registration is allowed."}), 400

    try:
        with get_db() as db:
            cursor = db.execute(
                "INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                (name, email, generate_password_hash(password), role, datetime.now().isoformat(timespec="seconds")),
            )
            user_id = cursor.lastrowid
        session.clear()
        session["user_id"] = user_id
        save_audit(user_id, None, "REGISTER", "New account created")
        return jsonify({"message": "Account created successfully."}), 201
    except Exception:
        return jsonify({"error": "This email may already be registered."}), 409

@api_bp.post("/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    with get_db() as db:
        user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Incorrect email or password."}), 401
    session.clear()
    session["user_id"] = user["id"]
    save_audit(user["id"], None, "LOGIN", "Successful login")
    return jsonify({"message": "Login successful."})

@api_bp.post("/auth/logout")
@login_required
def logout():
    user = logged_in_user()
    save_audit(user["id"], None, "LOGOUT", "User logged out")
    session.clear()
    return jsonify({"message": "Logged out."})

@api_bp.get("/auth/me")
@login_required
def me():
    user = logged_in_user()
    return jsonify(dict(user))

# ------------------------- RECORD UPLOAD / LIST / SEARCH -------------------------
@api_bp.post("/records/upload")
@roles_required("patient")
def upload_record():
    user = logged_in_user()
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        return jsonify({"error": "Choose a file to upload."}), 400
    try:
        original, stored, size = store_uploaded_file(uploaded)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    title = (request.form.get("title") or original).strip()
    category = (request.form.get("category") or "Other").strip()
    description = (request.form.get("description") or "").strip()
    record_date = (request.form.get("record_date") or "").strip()

    with get_db() as db:
        cursor = db.execute("""
            INSERT INTO records(patient_id,title,category,description,record_date,
                original_filename,stored_filename,mime_type,file_size,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,?)
        """, (user["id"], title, category, description, record_date, original, stored,
              uploaded.mimetype, size, datetime.now().isoformat(timespec="seconds")))
        record_id = cursor.lastrowid
    save_audit(user["id"], record_id, "UPLOAD", f"Uploaded {original}")
    return jsonify({"message": "Record uploaded.", "record_id": record_id}), 201

@api_bp.get("/records")
@login_required
def list_records():
    user = logged_in_user()
    keyword = (request.args.get("q") or "").strip()
    pattern = f"%{keyword}%"
    with get_db() as db:
        if user["role"] == "patient":
            rows = db.execute("""
                SELECT * FROM records WHERE patient_id=?
                AND (title LIKE ? OR category LIKE ? OR description LIKE ?)
                ORDER BY id DESC
            """, (user["id"], pattern, pattern, pattern)).fetchall()
        elif user["role"] == "doctor":
            rows = db.execute("""
                SELECT DISTINCT r.*,u.name AS patient_name FROM records r
                JOIN shares s ON s.record_id=r.id JOIN users u ON u.id=r.patient_id
                WHERE s.doctor_id=? AND s.active=1 AND s.expires_at>?
                ORDER BY r.id DESC
            """, (user["id"], datetime.now().isoformat(timespec="seconds"))).fetchall()
        else:
            rows = db.execute("""
                SELECT r.*,u.name AS patient_name FROM records r
                JOIN users u ON u.id=r.patient_id
                WHERE r.title LIKE ? OR u.name LIKE ? ORDER BY r.id DESC
            """, (pattern, pattern)).fetchall()
    return jsonify([dict(row) for row in rows])

@api_bp.get("/records/search")
@login_required
def search_records():
    # Search uses the same permission-aware listing logic.
    return list_records()

@api_bp.get("/records/<int:record_id>")
@login_required
def get_record(record_id):
    user = logged_in_user()
    record, permission = get_record_permission(user, record_id)
    if not record or not permission:
        return jsonify({"error": "Record not found or access denied."}), 404
    save_audit(user["id"], record_id, "VIEW", "Viewed record details")
    return jsonify(dict(record))

@api_bp.get("/records/<int:record_id>/download")
@login_required
def download_record(record_id):
    user = logged_in_user()
    record, permission = get_record_permission(user, record_id)
    if not record or not permission:
        abort(403)
    save_audit(user["id"], record_id, "DOWNLOAD", record["original_filename"])
    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        record["stored_filename"],
        as_attachment=True,
        download_name=record["original_filename"],
    )

@api_bp.delete("/records/<int:record_id>")
@login_required
def delete_record(record_id):
    user = logged_in_user()
    with get_db() as db:
        record = db.execute("SELECT * FROM records WHERE id=?", (record_id,)).fetchone()
        if not record:
            return jsonify({"error": "Record not found."}), 404
        if user["role"] != "admin" and record["patient_id"] != user["id"]:
            return jsonify({"error": "Only the owner or admin can delete this record."}), 403
        db.execute("DELETE FROM records WHERE id=?", (record_id,))
    try:
        os.remove(os.path.join(current_app.config["UPLOAD_FOLDER"], record["stored_filename"]))
    except FileNotFoundError:
        pass
    save_audit(user["id"], None, "DELETE", f"Deleted record #{record_id}")
    return jsonify({"message": "Record deleted."})

# ------------------------- SHARE / GRANT / REVOKE -------------------------
@api_bp.post("/records/<int:record_id>/share")
@roles_required("patient")
def share_record(record_id):
    user = logged_in_user()
    data = request.get_json(silent=True) or {}
    doctor_email = (data.get("doctor_email") or "").strip().lower()
    hours = data.get("expiry_hours", 24)
    with get_db() as db:
        record = db.execute(
            "SELECT id FROM records WHERE id=? AND patient_id=?", (record_id, user["id"])
        ).fetchone()
        if not record:
            return jsonify({"error": "Your record was not found."}), 404
        doctor = None
        if doctor_email:
            doctor = db.execute(
                "SELECT id FROM users WHERE email=? AND role='doctor'", (doctor_email,)
            ).fetchone()
            if not doctor:
                return jsonify({"error": "No registered doctor found with that email."}), 404
        token = make_share_token()
        expires = expiry_time(hours)
        db.execute("""
            INSERT INTO shares(record_id,doctor_id,share_token,expires_at,active,created_at)
            VALUES(?,?,?,?,1,?)
        """, (record_id, doctor["id"] if doctor else None, token, expires,
              datetime.now().isoformat(timespec="seconds")))
    save_audit(user["id"], record_id, "SHARE", f"Shared with {doctor_email or 'secure link'}")
    return jsonify({
        "message": "Temporary access created.",
        "share_url": request.host_url.rstrip("/") + "/api/records/shared/" + token,
        "expires_at": expires,
    }), 201

@api_bp.post("/records/<int:record_id>/grant")
@roles_required("patient")
def grant_doctor_access(record_id):
    user = logged_in_user()
    data = request.get_json(silent=True) or {}
    email = (data.get("doctor_email") or "").strip().lower()
    with get_db() as db:
        record = db.execute(
            "SELECT id FROM records WHERE id=? AND patient_id=?", (record_id, user["id"])
        ).fetchone()
        doctor = db.execute(
            "SELECT id FROM users WHERE email=? AND role='doctor'", (email,)
        ).fetchone()
        if not record:
            return jsonify({"error": "Record not found."}), 404
        if not doctor:
            return jsonify({"error": "Doctor account not found."}), 404
        expires = expiry_time(24 * 30)
        token = make_share_token()
        db.execute("""
            INSERT INTO shares(record_id,doctor_id,share_token,expires_at,active,created_at)
            VALUES(?,?,?,?,1,?)
        """, (record_id, doctor["id"], token, expires, datetime.now().isoformat(timespec="seconds")))
    save_audit(user["id"], record_id, "GRANT_ACCESS", f"Granted access to {email}")
    return jsonify({"message": "Doctor access granted for 30 days.", "expires_at": expires})

@api_bp.post("/records/<int:record_id>/revoke")
@roles_required("patient")
def revoke_access(record_id):
    user = logged_in_user()
    with get_db() as db:
        record = db.execute(
            "SELECT id FROM records WHERE id=? AND patient_id=?", (record_id, user["id"])
        ).fetchone()
        if not record:
            return jsonify({"error": "Record not found."}), 404
        db.execute("UPDATE shares SET active=0 WHERE record_id=?", (record_id,))
    save_audit(user["id"], record_id, "REVOKE", "All shared access revoked")
    return jsonify({"message": "All access to this record has been revoked."})

@api_bp.get("/records/shared/<token>")
@login_required
def open_shared_record(token):
    user = logged_in_user()
    with get_db() as db:
        share = db.execute("""
            SELECT s.*,r.id AS rid FROM shares s JOIN records r ON r.id=s.record_id
            WHERE s.share_token=? AND s.active=1 AND s.expires_at>?
        """, (token, datetime.now().isoformat(timespec="seconds"))).fetchone()
    if not share:
        return jsonify({"error": "This link is expired or revoked."}), 403
    if share["doctor_id"] is not None and user["id"] != share["doctor_id"] and user["role"] != "admin":
        return jsonify({"error": "This share link is assigned to another doctor."}), 403
    record, permission = get_record_permission(user, share["rid"])
    if not record or not permission:
        return jsonify({"error": "You are not authorized to open this record."}), 403
    save_audit(user["id"], share["rid"], "OPEN_SHARED", "Opened shared record")
    return jsonify(dict(record))

# ------------------------- AUDIT LOGS / ADMIN / DOCTOR NOTES -------------------------
@api_bp.get("/logs")
@login_required
def get_logs():
    user = logged_in_user()
    with get_db() as db:
        if user["role"] == "admin":
            rows = db.execute("""
                SELECT l.*,u.name AS user_name,r.title AS record_title
                FROM access_logs l LEFT JOIN users u ON u.id=l.user_id
                LEFT JOIN records r ON r.id=l.record_id ORDER BY l.id DESC LIMIT 200
            """).fetchall()
        else:
            rows = db.execute("""
                SELECT l.*,u.name AS user_name,r.title AS record_title
                FROM access_logs l LEFT JOIN users u ON u.id=l.user_id
                LEFT JOIN records r ON r.id=l.record_id
                WHERE l.user_id=? OR r.patient_id=? ORDER BY l.id DESC LIMIT 200
            """, (user["id"], user["id"])).fetchall()
    return jsonify([dict(row) for row in rows])

@api_bp.get("/admin/users")
@roles_required("admin")
def admin_users():
    with get_db() as db:
        rows = db.execute(
            "SELECT id,name,email,role,created_at FROM users ORDER BY id DESC"
        ).fetchall()
    return jsonify([dict(row) for row in rows])

@api_bp.post("/records/<int:record_id>/notes")
@roles_required("doctor")
def add_doctor_note(record_id):
    user = logged_in_user()
    record, permission = get_record_permission(user, record_id)
    if not record or permission != "shared":
        return jsonify({"error": "You can add notes only to records shared with you."}), 403
    note = ((request.get_json(silent=True) or {}).get("note") or "").strip()
    if not note:
        return jsonify({"error": "Note cannot be empty."}), 400
    with get_db() as db:
        db.execute(
            "INSERT INTO doctor_notes(record_id,doctor_id,note,created_at) VALUES(?,?,?,?)",
            (record_id, user["id"], note, datetime.now().isoformat(timespec="seconds")),
        )
    save_audit(user["id"], record_id, "ADD_NOTE", "Doctor added a note")
    return jsonify({"message": "Doctor note saved."}), 201
