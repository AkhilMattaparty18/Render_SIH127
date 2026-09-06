import os
from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient

# Import Blueprints
from routes.dashboard import dashboard_bp
from routes.alerts import alerts_bp
from routes.tracking import tracking_bp
from routes.analytics import analytics_bp

app = Flask(__name__)
CORS(app)

# Register Blueprints
app.register_blueprint(dashboard_bp)
app.register_blueprint(alerts_bp)
app.register_blueprint(tracking_bp)
app.register_blueprint(analytics_bp)

# MongoDB Connection
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://user1:user12326@cluster0.rn7dha5.mongodb.net/sirius_db?retryWrites=true&w=majority"
)

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.get_database("sirius_db")
    client.admin.command('ping')
    print("Connected successfully to MongoDB Atlas")
except Exception as e:
    print(f"MongoDB Connection Error: {e}")


# Health Check
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "online",
        "service": "SIRIUS Command Dashboard API"
    }), 200


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
