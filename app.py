import os
import threading
import logging

from flask import Flask, jsonify
from flask_cors import CORS

from azure.communication.email import EmailClient

from config import Config
from models.db import init_db
from routes.auth import auth_bp
from routes.files import files_bp

# ✅ App Insights
from opencensus.ext.azure.log_exporter import AzureLogHandler
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.ext.flask.flask_middleware import FlaskMiddleware


# =========================================================
# ✅ APPLICATION INSIGHTS CONNECTION STRING
# =========================================================
APPINSIGHTS_CONNECTION_STRING = "something"


# =========================================================
# ✅ AZURE COMMUNICATION SERVICE (EMAIL)
# =========================================================
ACS_CONNECTION_STRING = "something"
SENDER_EMAIL = "DoNotReply@64c29b1c-cbd9-4615-afb8-4fa2185a3bfc.azurecomm.net"


# =========================================================
# ✅ LOGGING SETUP
# =========================================================
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

try:
    handler = AzureLogHandler(connection_string=APPINSIGHTS_CONNECTION_STRING)
    logger.addHandler(handler)
except Exception as e:
    print("App Insights logging failed:", e)

logger.warning("🚀 APP STARTED")


# =========================================================
# ✅ EMAIL FUNCTION
# =========================================================
def send_email(to_email, subject, body):
    try:
        client = EmailClient.from_connection_string(ACS_CONNECTION_STRING)

        message = {
            "senderAddress": SENDER_EMAIL,
            "recipients": {
                "to": [{"address": to_email}]
            },
            "content": {
                "subject": subject,
                "html": body
            }
        }

        poller = client.begin_send(message)
        poller.result()

        print("✅ Email sent successfully")

    except Exception as e:
        print("❌ Email error:", str(e))


def send_email_async(to_email, subject, body):
    thread = threading.Thread(
        target=send_email,
        args=(to_email, subject, body)
    )
    thread.start()


# =========================================================
# ✅ CREATE APP
# =========================================================
def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # App Insights middleware
    try:
        FlaskMiddleware(
            app,
            exporter=AzureExporter(connection_string=APPINSIGHTS_CONNECTION_STRING),
            sampler=ProbabilitySampler(1.0),
        )
    except Exception as e:
        print("❌ Middleware failed:", e)

    CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=True)

    with app.app_context():
        init_db()

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(files_bp, url_prefix='/api/files')

    app.send_email_async = send_email_async

    return app


# =========================================================
# ✅ APP INSTANCE
# =========================================================
app = create_app()


# =========================================================
# ✅ ROUTES
# =========================================================
@app.route('/')
def index():
    return jsonify({
        'service': 'Cloud Bridge API',
        'status': 'ok',
        'version': '1.0'
    })


@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'service': 'Cloud Bridge API'
    })


# =========================================================
# ✅ MAIN
# =========================================================
if __name__ == '__main__':
    env = os.environ.get('FLASK_ENV', 'development')

    if env == 'production':
        host = '0.0.0.0'
        port = 5000
        debug = False
        print(f"[Cloud Bridge] Running in PRODUCTION mode on {host}:{port}")
    else:
        host = '127.0.0.1'
        port = 5000
        debug = True
        print(f"[Cloud Bridge] Running in DEVELOPMENT mode on {host}:{port}")

    app.run(host=host, port=port, debug=debug)
