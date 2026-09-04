import os
import certifi
from flask import Flask, jsonify
from flask_cors import CORS
from pymongo import MongoClient

# Import Blueprints
from routes.dashboard import dashboard_bp
from routes.alerts import alerts_bp
from routes.tracking import tracking_bp

app = Flask(__name__)
CORS(app)  # Enables cross-origin requests from Vercel

# Register Blueprints
app.register_blueprint(dashboard_bp)
app.register_blueprint(alerts_bp)
app.register_blueprint(tracking_bp)

# Health Check Route
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "online",
        "service": "SIRIUS Command Dashboard API",
        "database": "traffic_system"
    }), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
