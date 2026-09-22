import hashlib
import secrets
import smtplib
import sqlite3
import time
from email.message import EmailMessage
from pathlib import Path

import streamlit as st


DB_PATH = Path(__file__).resolve().parent / "users.db"

OTP_EXPIRY_SECONDS = 300
MAX_OTP_ATTEMPTS = 5


def init_auth_db():
    """Create authentication tables."""

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            created_at REAL NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS otp_requests (
            email TEXT PRIMARY KEY,
            otp_hash TEXT NOT NULL,
            expires_at REAL NOT NULL,
            attempts INTEGER DEFAULT 0
        )
    """)

    connection.commit()
    connection.close()


def register_user(email):
    """Register an email address."""

    email = email.strip().lower()

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR IGNORE INTO users (email, created_at)
        VALUES (?, ?)
        """,
        (email, time.time())
    )

    connection.commit()
    connection.close()


def is_registered(email):
    """Check whether an email is registered."""

    email = email.strip().lower()

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        "SELECT email FROM users WHERE email = ?",
        (email,)
    )

    result = cursor.fetchone()

    connection.close()

    return result is not None


def _hash_otp(otp):
    """Hash OTP before storing it."""

    return hashlib.sha256(
        otp.encode("utf-8")
    ).hexdigest()


def generate_otp():
    """Generate a cryptographically secure 6-digit OTP."""

    return f"{secrets.randbelow(1_000_000):06d}"


def send_otp_email(email, otp):
    """Send OTP through SMTP."""

    smtp_host = st.secrets["SMTP_HOST"]
    smtp_port = int(st.secrets["SMTP_PORT"])
    smtp_username = st.secrets["SMTP_USERNAME"]
    smtp_password = st.secrets["SMTP_PASSWORD"]

    message = EmailMessage()

    message["Subject"] = "SustainaByte Login OTP"
    message["From"] = smtp_username
    message["To"] = email

    message.set_content(
        f"""
Hello,

Your SustainaByte login verification code is:

{otp}

This OTP is valid for 5 minutes.

If you did not request this login, you can ignore this email.

SustainaByte
Sustainable AI Lifecycle Auditor
"""
    )

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(message)


def request_otp(email):
    """Generate, store and send an OTP."""

    email = email.strip().lower()

    if not is_registered(email):
        return False, "Email address is not registered."

    otp = generate_otp()

    otp_hash = _hash_otp(otp)
    expires_at = time.time() + OTP_EXPIRY_SECONDS

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO otp_requests
        (email, otp_hash, expires_at, attempts)
        VALUES (?, ?, ?, 0)
        """,
        (email, otp_hash, expires_at)
    )

    connection.commit()
    connection.close()

    try:
        send_otp_email(email, otp)

    except Exception:
        return False, "Unable to send OTP email. Check SMTP configuration."

    return True, "OTP sent successfully."


def verify_otp(email, entered_otp):
    """Verify the supplied OTP."""

    email = email.strip().lower()
    entered_otp = entered_otp.strip()

    connection = sqlite3.connect(DB_PATH)
    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT otp_hash, expires_at, attempts
        FROM otp_requests
        WHERE email = ?
        """,
        (email,)
    )

    record = cursor.fetchone()

    if record is None:
        connection.close()
        return False, "No OTP request found."

    stored_hash, expires_at, attempts = record

    if time.time() > expires_at:
        cursor.execute(
            "DELETE FROM otp_requests WHERE email = ?",
            (email,)
        )

        connection.commit()
        connection.close()

        return False, "OTP has expired. Please request a new one."

    if attempts >= MAX_OTP_ATTEMPTS:
        connection.close()
        return False, "Too many incorrect attempts. Request a new OTP."

    if not secrets.compare_digest(
        stored_hash,
        _hash_otp(entered_otp)
    ):
        cursor.execute(
            """
            UPDATE otp_requests
            SET attempts = attempts + 1
            WHERE email = ?
            """,
            (email,)
        )

        connection.commit()
        connection.close()

        return False, "Incorrect OTP."

    cursor.execute(
        "DELETE FROM otp_requests WHERE email = ?",
        (email,)
    )

    connection.commit()
    connection.close()

    return True, "OTP verified successfully."
