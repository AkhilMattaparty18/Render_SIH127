from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
import os

app = Flask(__name__)
CORS(app)

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*")

# Database setup
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client['anpr_db']
vehicles_col = db['vehicles']

@app.route('/api/detect', methods=['POST'])
def process_detection():
    data = request.json
    vehicle_id = data.get("vehicle_id")
    cam_id = data.get("cam_id")
    lat = data.get("latitude")
    lng = data.get("longitude")
    timestamp = data.get("time_stamp")

    # Fetch or update vehicle profile in Atlas
    vehicle = vehicles_col.find_one({"vehicle_id": vehicle_id})
    is_blacklisted = vehicle.get("is_blacklisted", False) if vehicle else False
    reason = vehicle.get("blacklist_reason", "N/A") if vehicle else "N/A"

    new_spot = {"cam_id": cam_id, "latitude": lat, "longitude": lng, "time_stamp": timestamp}

    # Save tracking history to MongoDB
    vehicles_col.update_one(
        {"vehicle_id": vehicle_id},
        {
            "$push": {"trail": new_spot},
            "$set": {
                "last_occurrence": new_spot,
                "is_blacklisted": is_blacklisted,
                "blacklist_reason": reason
            },
            "$inc": {"total_detections": 1}
        },
        upsert=True
    )

    # Payload to send via Socket
    alert_payload = {
        "vehicle_id": vehicle_id,
        "is_blacklisted": is_blacklisted,
        "reason": reason,
        "location": new_spot,
        "timestamp": timestamp
    }

    # Emit real-time alert to all connected dashboards
    if is_blacklisted:
        socketio.emit('new_blacklist_alert', alert_payload) # Live alert feed

    return jsonify({"success": True, "data": alert_payload})

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
