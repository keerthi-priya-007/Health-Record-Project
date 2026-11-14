"""Authentication, role checks, file validation and audit helpers."""
import os, secrets
from datetime import datetime, timedelta
from functools import wraps
from flask import session, jsonify, current_app, request
from werkzeug.utils import secure_filename
from .database import get_db

def logged_in_user():
    user_id = session.get("user_id")
    if not user_id:
        return None
    with get_db() as db:
        return db.execute(
            "SELECT id,name,email,role FROM users WHERE id=?", (user_id,)
        ).fetchone()

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if not logged_in_user():
            return jsonify({"error": "Please log in first."}), 401
        return function(*args, **kwargs)
    return wrapper

def roles_required(*allowed_roles):
    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            user = logged_in_user()
            if not user:
                return jsonify({"error": "Please log in first."}), 401
            if user["role"] not in allowed_roles:
                return jsonify({"error": "Your role is not allowed to do this."}), 403
            return function(*args, **kwargs)
        return wrapper
    return decorator

def save_audit(user_id, record_id, action, details=""):
    with get_db() as db:
        db.execute(
            "INSERT INTO access_logs(user_id,record_id,action,details,created_at) VALUES(?,?,?,?,?)",
            (user_id, record_id, action, details, datetime.now().isoformat(timespec="seconds")),
        )

def is_allowed_file(filename):
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]
    )

def store_uploaded_file(file_object):
    """Validate extension, generate a safe unique name, and save privately."""
    original = secure_filename(file_object.filename)
    if not original or not is_allowed_file(original):
        raise ValueError("Allowed file types: PDF, PNG, JPG, JPEG, DOC and DOCX.")
    stored = secrets.token_hex(16) + "_" + original
    path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored)
    file_object.save(path)
    return original, stored, os.path.getsize(path)

def get_record_permission(user, record_id):
    """Return (record, permission). A doctor only sees explicitly shared records."""
    with get_db() as db:
        record = db.execute("SELECT * FROM records WHERE id=?", (record_id,)).fetchone()
        if not record:
            return None, None
        if user["role"] == "admin" or record["patient_id"] == user["id"]:
            return record, "owner"
        now = datetime.now().isoformat(timespec="seconds")
        share = db.execute("""
            SELECT id FROM shares
            WHERE record_id=? AND active=1 AND expires_at>?
              AND (doctor_id=? OR doctor_id IS NULL)
            ORDER BY id DESC LIMIT 1
        """, (record_id, now, user["id"])).fetchone()
        return (record, "shared") if share else (record, None)

def make_share_token():
    return secrets.token_urlsafe(32)

def expiry_time(hours):
    hours = max(1, min(int(hours), 24 * 30))
    return (datetime.now() + timedelta(hours=hours)).isoformat(timespec="seconds")
