import os
import uuid
import mimetypes
import threading
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from models.db import query, execute
from utils.auth import token_required
from utils.storage import get_storage

files_bp = Blueprint('files', __name__)


def allowed(filename):
    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    return ext in current_app.config['ALLOWED_EXTENSIONS']


def classify(filename):
    ext = filename.rsplit('.', 1)[-1].lower()
    if ext in {'jpg','jpeg','png','gif','webp','svg'}:  return 'image'
    if ext == 'pdf':                                     return 'pdf'
    if ext in {'doc','docx','txt','rtf'}:               return 'document'
    if ext in {'xls','xlsx','csv'}:                     return 'spreadsheet'
    return 'other'


def process_event(filename, user_email):
    """Simulates serverless function / Azure Function trigger."""
    print(f"process_event() → Processing upload: {filename} for {user_email}")
    print(f"EVENT: Downstream service notified → storage confirmed")


# 🔥 UPDATED EMAIL FUNCTION (ACS INTEGRATION)
def notify_upload(user_email, filename, user_name, app):
    """Runs in background thread — simulates async messaging."""
    with app.app_context():
        try:
            app.send_email_async(
                user_email,
                "File Upload Successful",
                f"""
                <h2>Hello {user_name},</h2>
                <p>Your file <b>{filename}</b> has been uploaded successfully.</p>
                <p>Thank you for using CloudBridge.</p>
                """
            )
            print("📨 Upload email sent via ACS")

        except Exception as e:
            print("❌ Upload email failed:", str(e))

        process_event(filename, user_email)


# ── UPLOAD ────────────────────────────────────────────────
@files_bp.route('/upload', methods=['POST'])
@token_required
def upload_file(current_user):
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    f = request.files['file']

    if not f.filename:
        return jsonify({'error': 'Empty filename'}), 400

    if not allowed(f.filename):
        return jsonify({'error': 'File type not allowed'}), 400

    original = secure_filename(f.filename)
    ext = original.rsplit('.', 1)[-1].lower() if '.' in original else ''
    stored = f"{uuid.uuid4().hex}.{ext}"

    mime = f.mimetype or mimetypes.guess_type(original)[0] or 'application/octet-stream'
    ftype = classify(original)
    is_public = request.form.get('is_public', 'false').lower() == 'true'

    f.seek(0, 2)
    size = f.tell()
    f.seek(0)

    storage = get_storage()
    path = storage.save(f, stored)

    import json
    meta = json.dumps({"original_ext": ext, "mime": mime, "uploaded_by": current_user['email']})

    file_id = execute(
        """INSERT INTO files
           (user_id, filename, stored_name, file_size, file_type, mime_type,
            storage_path, is_public, metadata)
           VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
        (current_user['id'], original, stored, size, ftype, mime,
         path, 1 if is_public else 0, meta),
        get_id=True
    )

    print(f"LOG: File uploaded → {original} ({size} bytes) by {current_user['email']}")
    print(f"EVENT: File uploaded → {original}")

    # 🔥 BACKGROUND THREAD (ASYNC EMAIL)
    flask_app = current_app._get_current_object()

    t = threading.Thread(
        target=notify_upload,
        args=(current_user['email'], original, current_user['name'], flask_app),
        daemon=True
    )

    t.start()

    row = query("SELECT * FROM files WHERE id=%s AND is_deleted=0", (file_id,), one=True)
    return jsonify({'file': row}), 201


# ── LIST ──────────────────────────────────────────────────
@files_bp.route('', methods=['GET'])
@token_required
def list_files(current_user):
    sort   = request.args.get('sort', 'newest')
    search = request.args.get('search', '').strip()
    ftype  = request.args.get('type', '').strip()
    limit  = min(int(request.args.get('limit', 100)), 500)

    order_map = {
        'newest': 'uploaded_at DESC', 'oldest': 'uploaded_at ASC',
        'name':   'filename ASC',     'size':   'file_size DESC'
    }
    order = order_map.get(sort, 'uploaded_at DESC')

    sql    = "SELECT * FROM files WHERE user_id=%s AND is_deleted=0"
    params = [current_user['id']]

    if search:
        sql += " AND filename LIKE %s"; params.append(f'%{search}%')
    if ftype:
        sql += " AND file_type=%s";     params.append(ftype)

    sql += f" ORDER BY {order} LIMIT {limit}"
    rows = query(sql, tuple(params))
    return jsonify({'files': rows, 'total': len(rows)})


# ── STATS ─────────────────────────────────────────────────
@files_bp.route('/stats', methods=['GET'])
@token_required
def stats(current_user):
    uid = current_user['id']

    total = query(
        "SELECT COUNT(*) as c, COALESCE(SUM(file_size),0) as s FROM files WHERE user_id=%s AND is_deleted=0",
        (uid,), one=True)

    images = query(
        "SELECT COUNT(*) as c FROM files WHERE user_id=%s AND file_type='image' AND is_deleted=0",
        (uid,), one=True)

    docs = query(
        "SELECT COUNT(*) as c FROM files WHERE user_id=%s AND file_type IN ('pdf','document','spreadsheet') AND is_deleted=0",
        (uid,), one=True)

    return jsonify({
        'total': total['c'],
        'total_size': total['s'],
        'images': images['c'],
        'documents': docs['c']
    })


# ── DOWNLOAD ──────────────────────────────────────────────
@files_bp.route('/<int:file_id>/download', methods=['GET'])
@token_required
def download(current_user, file_id):
    f = query(
        "SELECT * FROM files WHERE id=%s AND user_id=%s AND is_deleted=0",
        (file_id, current_user['id']), one=True)

    if not f:
        return jsonify({'error': 'File not found'}), 404

    print(f"LOG: File downloaded → {f['filename']} by {current_user['email']}")
    return get_storage().send(f['storage_path'], f['filename'])


# ── DELETE ────────────────────────────────────────────────
@files_bp.route('/<int:file_id>', methods=['DELETE'])
@token_required
def delete_file(current_user, file_id):
    f = query(
        "SELECT * FROM files WHERE id=%s AND user_id=%s AND is_deleted=0",
        (file_id, current_user['id']), one=True)

    if not f:
        return jsonify({'error': 'File not found'}), 404

    import datetime
    deleted_at = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    execute(
        "UPDATE files SET is_deleted=1, deleted_at=%s WHERE id=%s",
        (deleted_at, file_id)
    )

    print(f"LOG: File soft-deleted → {f['filename']} by {current_user['email']}")
    return jsonify({'message': 'File deleted successfully'})


# ── RESTORE ───────────────────────────────────────────────
@files_bp.route('/<int:file_id>/restore', methods=['POST'])
@token_required
def restore_file(current_user, file_id):
    f = query(
        "SELECT * FROM files WHERE id=%s AND user_id=%s AND is_deleted=1",
        (file_id, current_user['id']), one=True)

    if not f:
        return jsonify({'error': 'File not found or not deleted'}), 404

    execute(
        "UPDATE files SET is_deleted=0, deleted_at=NULL WHERE id=%s",
        (file_id,)
    )

    print(f"LOG: File restored → {f['filename']} by {current_user['email']}")
    return jsonify({'message': 'File restored successfully'})
