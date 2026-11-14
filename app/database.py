"""SQLite database setup and small helper functions."""
import sqlite3
from datetime import datetime
from flask import current_app
from werkzeug.security import generate_password_hash

def get_db():
    """Open a database connection for the current request."""
    connection = sqlite3.connect(current_app.config["DATABASE"])
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection

def init_db(app):
    """Create tables and insert demo accounts once."""
    schema = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('patient','doctor','admin')),
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT DEFAULT '',
        record_date TEXT DEFAULT '',
        original_filename TEXT NOT NULL,
        stored_filename TEXT NOT NULL UNIQUE,
        mime_type TEXT,
        file_size INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(patient_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS shares (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id INTEGER NOT NULL,
        doctor_id INTEGER,
        share_token TEXT NOT NULL UNIQUE,
        expires_at TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        FOREIGN KEY(record_id) REFERENCES records(id) ON DELETE CASCADE,
        FOREIGN KEY(doctor_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS access_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        record_id INTEGER,
        action TEXT NOT NULL,
        details TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL,
        FOREIGN KEY(record_id) REFERENCES records(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS doctor_notes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        record_id INTEGER NOT NULL,
        doctor_id INTEGER NOT NULL,
        note TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(record_id) REFERENCES records(id) ON DELETE CASCADE,
        FOREIGN KEY(doctor_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """
    with app.app_context():
        connection = sqlite3.connect(app.config["DATABASE"])
        connection.executescript(schema)
        count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            now = datetime.now().isoformat(timespec="seconds")
            demo_users = [
                ("Demo Patient", "patient@demo.com", "Patient@123", "patient"),
                ("Demo Doctor", "doctor@demo.com", "Doctor@123", "doctor"),
                ("Demo Admin", "admin@demo.com", "Admin@123", "admin"),
            ]
            for name, email, password, role in demo_users:
                connection.execute(
                    "INSERT INTO users(name,email,password_hash,role,created_at) VALUES(?,?,?,?,?)",
                    (name, email, generate_password_hash(password), role, now),
                )
        connection.commit()
        connection.close()
