import jwt
from functools import wraps
from flask import request, jsonify, current_app
from models.db import query

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth = request.headers.get('Authorization','')
        if auth.startswith('Bearer '):
            token = auth.split(' ')[1]
        if not token:
            token = request.args.get('token')
        if not token:
            return jsonify({'error': 'Token required'}), 401
        try:
            payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
            user_id = payload['user_id']
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        user = query("SELECT * FROM users WHERE id=%s AND is_active=1", (user_id,), one=True)
        if not user:
            return jsonify({'error': 'User not found'}), 401
        return f(user, *args, **kwargs)
    return decorated
