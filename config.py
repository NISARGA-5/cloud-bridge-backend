import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

class Config:
    SECRET_KEY        = os.environ.get('SECRET_KEY', 'cloudbridge-dev-secret-2025')
    DATABASE_URL      = os.environ.get('DATABASE_URL', os.path.join(BASE_DIR, 'cloudbridge.db'))
    UPLOAD_FOLDER     = os.environ.get('UPLOAD_FOLDER', os.path.join(BASE_DIR, 'uploads'))
    MAX_CONTENT_LENGTH= 50 * 1024 * 1024  # 50 MB
    STORAGE_TYPE      = os.environ.get('STORAGE_TYPE', 'local')

    # Azure Blob
    AZURE_CONNECTION_STRING = os.environ.get('AZURE_CONNECTION_STRING', '')
    AZURE_CONTAINER         = os.environ.get('AZURE_CONTAINER', 'cloudbridge-files')

    # GCP
    GCP_BUCKET_NAME = os.environ.get('GCP_BUCKET_NAME', 'cloudbridge-files')

    # Email (Gmail SMTP)
    MAIL_SERVER   = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT     = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME', '')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD', '')   # Gmail App Password
    MAIL_FROM     = os.environ.get('MAIL_FROM', 'cloudbridge@gmail.com')

    # Dev mode — show OTP on screen instead of emailing
    DEV_MODE = os.environ.get('FLASK_ENV', 'development') != 'production'

    ALLOWED_EXTENSIONS = {
        'pdf','doc','docx','xls','xlsx','csv','txt',
        'jpg','jpeg','png','gif','webp','svg',
        'zip','json','xml'
    }
