import os
import jwt
import datetime
from flask import Blueprint, request, jsonify, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from models.db import query, execute
from utils.auth import token_required
from utils.email import generate_otp  # keep only OTP generator

ENV = os.getenv("ENV", "prod")

auth_bp = Blueprint('auth', __name__)


def make_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        'iat': datetime.datetime.utcnow()
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')


# ── SEND OTP ──────────────────────────────────────────────
@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    data = request.get_json()
    email = (data.get('email') or '').strip().lower()
    name = (data.get('name') or 'there').strip()

    if not email or '@' not in email:
        return jsonify({'error': 'Valid email required'}), 400

    # Check if email already registered
    existing = query("SELECT id FROM users WHERE email=%s", (email,), one=True)
    if existing:
        return jsonify({'error': 'Email already registered. Please sign in.'}), 409

    # Generate OTP
    otp = str(generate_otp())
    exp = datetime.datetime.utcnow() + datetime.timedelta(minutes=10)

    # Clean old OTPs
    execute("DELETE FROM otp_store WHERE email=%s", (email,))

    # Store new OTP
    execute(
        "INSERT INTO otp_store (email, otp_code, expires_at) VALUES (%s,%s,%s)",
        (email, otp, exp.strftime('%Y-%m-%d %H:%M:%S'))
    )

    print(f"LOG: OTP generated for {email}")

    # 🔥 SEND EMAIL USING ACS (ASYNC)
    try:
        current_app.send_email_async(
            email,
            "Your OTP Code",
            f"""
            <h3>Hello {name},</h3>
            <p>Your OTP is <b>{otp}</b></p>
            <p>This OTP is valid for 10 minutes.</p>
            """
        )
        print("📨 OTP email sent via ACS")

    except Exception as e:
        print("❌ Email error:", str(e))

    response = {'success': True, 'message': f'OTP sent to {email}'}

    # Dev mode OTP
    if ENV == "dev":
        response['dev_otp'] = otp

    return jsonify(response)


# ── REGISTER ──────────────────────────────────────────────
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    age = data.get('age')
    otp = (data.get('otp') or '').strip()

    if not all([name, email, password, otp]):
        return jsonify({'error': 'All fields are required'}), 400

    if len(password) < 8:
        return jsonify({'error': 'Password must be at least 8 characters'}), 400

    now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    otp_row = query(
        "SELECT * FROM otp_store WHERE email=%s AND otp_code=%s AND used=0 AND expires_at > %s",
        (email, otp, now), one=True
    )

    if not otp_row:
        return jsonify({'error': 'Invalid or expired OTP'}), 400

    # Mark OTP used
    execute("UPDATE otp_store SET used=1 WHERE id=%s", (otp_row['id'],))

    # Check duplicate
    if query("SELECT id FROM users WHERE email=%s", (email,), one=True):
        return jsonify({'error': 'Email already registered'}), 409

    import json
    hashed = generate_password_hash(password)
    metadata = json.dumps({"registered_via": "web", "otp_verified": True})

    user_id = execute(
        "INSERT INTO users (name, email, password, age, role, metadata) VALUES (%s,%s,%s,%s,%s,%s)",
        (name, email, hashed, age, 'user', metadata),
        get_id=True
    )

    print(f"LOG: User registered → {email}")

    token = make_token(user_id)

    return jsonify({
        'token': token,
        'user': {'id': user_id, 'name': name, 'email': email, 'role': 'user'}
    }), 201


# ── LOGIN ─────────────────────────────────────────────────
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''

    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400

    user = query("SELECT * FROM users WHERE email=%s", (email,), one=True)

    if not user or not check_password_hash(user['password'], password):
        return jsonify({'error': 'Invalid email or password'}), 401

    if not user['is_active']:
        return jsonify({'error': 'Account inactive'}), 403

    print(f"LOG: User logged in → {email}")

    token = make_token(user['id'])

    return jsonify({
        'token': token,
        'user': {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role']
        }
    })
