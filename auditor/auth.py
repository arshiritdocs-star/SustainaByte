"""
Email OTP authentication for SustainaByte.
"""

import hashlib
import os
import secrets
import smtplib
import sqlite3
import time

from email.message import EmailMessage
from pathlib import Path


DB_PATH = (
    Path(__file__).resolve().parent
    / "auth.db"
)

OTP_EXPIRY_SECONDS = 300
MAX_OTP_ATTEMPTS = 5


def init_auth_db():
    """
    Create authentication tables if they do not exist.
    """

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS otp_requests (
            email TEXT PRIMARY KEY,
            otp_hash TEXT NOT NULL,
            expires_at REAL NOT NULL,
            attempts INTEGER DEFAULT 0
        )
        """
    )

    connection.commit()
    connection.close()


def register_user(email):
    """
    Register a verified email address.
    """

    email = email.strip().lower()

    if not email:
        return False

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO users (email)
            VALUES (?)
            """,
            (email,)
        )

        connection.commit()

        return True

    except sqlite3.IntegrityError:

        return False

    finally:

        connection.close()


def is_registered(email):
    """
    Check whether an email is registered.
    """

    email = email.strip().lower()

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT 1
        FROM users
        WHERE email = ?
        """,
        (email,)
    )

    result = cursor.fetchone()

    connection.close()

    return result is not None


def _hash_otp(otp):
    """
    Hash an OTP before storing it.
    """

    return hashlib.sha256(
        otp.encode("utf-8")
    ).hexdigest()


def generate_otp():
    """
    Generate a six-digit OTP.
    """

    return f"{secrets.randbelow(1_000_000):06d}"


def send_otp_email(email, otp):
    """
    Send OTP through SMTP.

    SMTP configuration is read from environment variables
    or Streamlit secrets if available.
    """

    try:

        import streamlit as st

        host = st.secrets.get(
            "SMTP_HOST",
            os.getenv(
                "SMTP_HOST",
                "smtp.gmail.com"
            )
        )

        port = int(
            st.secrets.get(
                "SMTP_PORT",
                os.getenv(
                    "SMTP_PORT",
                    "465"
                )
            )
        )

        username = st.secrets.get(
            "SMTP_USERNAME",
            os.getenv(
                "SMTP_USERNAME",
                ""
            )
        )

        password = st.secrets.get(
            "SMTP_PASSWORD",
            os.getenv(
                "SMTP_PASSWORD",
                ""
            )
        )

    except Exception:

        host = os.getenv(
            "SMTP_HOST",
            "smtp.gmail.com"
        )

        port = int(
            os.getenv(
                "SMTP_PORT",
                "465"
            )
        )

        username = os.getenv(
            "SMTP_USERNAME",
            ""
        )

        password = os.getenv(
            "SMTP_PASSWORD",
            ""
        )

    if not username or not password:

        raise RuntimeError(
            "SMTP username or password is missing."
        )

    message = EmailMessage()

    message["Subject"] = (
        "SustainaByte Verification Code"
    )

    message["From"] = username

    message["To"] = email

    message.set_content(
        f"""
Your SustainaByte verification code is:

{otp}

This OTP expires in 5 minutes.

If you did not request this code,
you can ignore this email.
"""
    )

    if port == 465:

        with smtplib.SMTP_SSL(
            host,
            port,
            timeout=20
        ) as server:

            server.login(
                username,
                password
            )

            server.send_message(
                message
            )

    else:

        with smtplib.SMTP(
            host,
            port,
            timeout=20
        ) as server:

            server.ehlo()

            server.starttls()

            server.ehlo()

            server.login(
                username,
                password
            )

            server.send_message(
                message
            )


def request_otp(email):
    """
    Send a login OTP to an existing user.
    """

    email = email.strip().lower()

    if not is_registered(email):

        return (
            False,
            "Email address is not registered."
        )

    otp = generate_otp()

    otp_hash = _hash_otp(otp)

    expires_at = (
        time.time()
        + OTP_EXPIRY_SECONDS
    )

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO otp_requests
        (email, otp_hash, expires_at, attempts)
        VALUES (?, ?, ?, 0)
        """,
        (
            email,
            otp_hash,
            expires_at
        )
    )

    connection.commit()

    connection.close()

    try:

        send_otp_email(
            email,
            otp
        )

    except Exception as e:

        return (
            False,
            f"Email sending failed: {e}"
        )

    return (
        True,
        "OTP sent successfully."
    )


def register_and_send_otp(email):
    """
    Send a registration OTP to a new email.
    """

    email = email.strip().lower()

    if is_registered(email):

        return (
            False,
            "This email is already registered."
        )

    otp = generate_otp()

    otp_hash = _hash_otp(otp)

    expires_at = (
        time.time()
        + OTP_EXPIRY_SECONDS
    )

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute(
        """
        INSERT OR REPLACE INTO otp_requests
        (email, otp_hash, expires_at, attempts)
        VALUES (?, ?, ?, 0)
        """,
        (
            email,
            otp_hash,
            expires_at
        )
    )

    connection.commit()

    connection.close()

    try:

        send_otp_email(
            email,
            otp
        )

    except Exception as e:

        return (
            False,
            f"Email sending failed: {e}"
        )

    return (
        True,
        "Registration OTP sent successfully."
    )


def verify_otp(email, entered_otp):
    """
    Verify a previously issued OTP.
    """

    email = email.strip().lower()

    entered_otp = (
        entered_otp.strip()
    )

    connection = sqlite3.connect(DB_PATH)

    cursor = connection.cursor()

    cursor.execute(
        """
        SELECT
            otp_hash,
            expires_at,
            attempts
        FROM otp_requests
        WHERE email = ?
        """,
        (email,)
    )

    result = cursor.fetchone()

    if result is None:

        connection.close()

        return (
            False,
            "No OTP request found."
        )

    otp_hash, expires_at, attempts = result

    if time.time() > expires_at:

        cursor.execute(
            """
            DELETE FROM otp_requests
            WHERE email = ?
            """,
            (email,)
        )

        connection.commit()

        connection.close()

        return (
            False,
            "OTP has expired."
        )

    if attempts >= MAX_OTP_ATTEMPTS:

        connection.close()

        return (
            False,
            "Too many incorrect attempts."
        )

    if _hash_otp(entered_otp) != otp_hash:

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

        return (
            False,
            "Incorrect OTP."
        )

    cursor.execute(
        """
        DELETE FROM otp_requests
        WHERE email = ?
        """,
        (email,)
    )

    connection.commit()

    connection.close()

    return (
        True,
        "OTP verified successfully."
    )
