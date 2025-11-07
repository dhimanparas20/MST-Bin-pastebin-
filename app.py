import os
import random
import string
from datetime import datetime, timezone, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv
from flask import Flask, request, render_template, make_response
from flask_restful import Api, Resource
from pymongo import MongoClient
# from pytz import timezone

# Load environment variables
load_dotenv()

FLASK_ENV = os.getenv("FLASK_ENV", "dev")  # Default to "dev"
STATIC_BASE_URL = os.getenv("STATIC_BASE_URL", "/")  # Default to local "/"

# Configure Flask app
if FLASK_ENV == "prod":
    # In production, serve static files from S3
    print("Running in PRODUCTION environment")
    app = Flask(__name__, static_folder=None)  # Disable Flask's static file handling
else:
    print("Running in DEVELOPMENT environment")
    # In development, serve static files from the "public" directory
    app = Flask(__name__, static_folder="public", static_url_path="/")

app.secret_key = os.getenv("SECRET_KEY", "super_secret_key")  # For session handling
api = Api(app)
scheduler = BackgroundScheduler()

# Inject STATIC_BASE_URL into templates
@app.context_processor
def inject_static_base_url():
    if FLASK_ENV == "prod":
        # Use S3 bucket URL in production
        return {"static_base_url": STATIC_BASE_URL}
    else:
        # Dynamically determine the base domain for local development
        base_url = f"{request.scheme}://{request.host}"  # e.g., http://localhost:5000
        return {"static_base_url": base_url}

# MongoDB Configuration
MONGO_CONNECTION_STRING = os.getenv('MONGO_CONNECTION_STRING', 'mongodb://localhost:27017')
if not MONGO_CONNECTION_STRING:
    raise ValueError("MONGO_CONNECTION_STRING is not set in the environment variables")

client = MongoClient(MONGO_CONNECTION_STRING)
db = client[os.getenv('MONGO_DB_NAME', 'pastebin')]
pastes_collection = db[os.getenv('MONGO_COLLECTION_NAME', 'pastes')]

# Helper function to generate a random 6-digit key
def generate_key():
    key_length = int(os.getenv('KEY_LENGTH', '6'))
    return ''.join(random.choices(string.ascii_letters + string.digits, k=key_length))

# Resource for saving pastes
class SavePaste(Resource):
    def post(self):
        data = request.json.get('data', '')
        heading = request.json.get('heading', 'My Paste').strip() or 'My Paste'
        user_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
        if not data:
            return {'error': 'No data provided'}, 400

        key = generate_key()
        paste = {
            'key': key,
            'data': data,
            'heading': heading,
            'created_at': datetime.now(timezone.utc),
            'ip_address': user_ip,
            'open_count': 0
        }
        pastes_collection.insert_one(paste)
        return {'url': f'{request.host_url}{key}'}, 201


# Resource for retrieving pastes
class GetPaste(Resource):
    def get(self, key):
        paste = pastes_collection.find_one({'key': key})
        if not paste:
            return {'error': 'Paste not found or Deleted'}, 404
        pastes_collection.update_one({'key': key}, {'$inc': {'open_count': 1}})
        heading = paste.get('heading', 'My Paste')
        return make_response(render_template('paste.html', paste=paste['data'], open_count=paste['open_count'], heading=heading))


# Resource for rendering the homepage
class Index(Resource):
    def get(self):
        return make_response(render_template('index.html'))

# Register resources
api.add_resource(SavePaste, '/api/save')
api.add_resource(GetPaste, '/<string:key>')
api.add_resource(Index, '/')

# Delete the pastes if they have less than 2 click and older than 7 days
def delete_pastes():
    print(f"Running delete_pastes at {datetime.now()}")
    print(pastes_collection.delete_many({'open_count': {'$lt': 2}, 'created_at': {'$lt': datetime.now(timezone.utc) - timedelta(days=7)}}))


# Set the scheduler to run after every 7 days
scheduler.add_job(delete_pastes, 'interval', days=7)

if __name__ == '__main__':
    scheduler.start()
    app.run(
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true',
        port=int(os.getenv('FLASK_PORT', '5000')),
        threaded=True,
        host=os.getenv('FLASK_HOST', '0.0.0.0')
    )
