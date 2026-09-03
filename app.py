import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
from pymongo import MongoClient
import certifi

app = Flask(__name__)

# Allow cross-origin requests for both REST API and WebSockets
CORS(app, resources={r"/*": {"origins": "*"}})
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Initialize MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client['anpr_db']
vehicles_col = db['vehicles']

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "online",
        "message": "ANPR Vehicle Tracking API with SocketIO is up and running!"
    }), 200

@app.route('/api/track', methods=['GET'])
def get_vehicle_track():
    vehicle_id = request.args.get('vehicle_id')
    if not vehicle_id:
        return jsonify({"success": False, "message": "vehicle_id parameter is required"}), 400

    vehicle_data = vehicles_col.find_one({"vehicle_id": vehicle_id}, {"_id": 0})
    if not vehicle_data:
        return jsonify({"success": False, "message": "Vehicle not found"}), 404

    return jsonify({"success": True, "data": vehicle_data}), 200

# Endpoint to simulate or ingest new camera hits
@app.route('/api/detect', methods=['POST'])
def handle_detection():
    payload = request.json or {}
    vehicle_id = payload.get("vehicle_id")
    cam_id = payload.get("cam_id")
    lat = payload.get("latitude")
    lng = payload.get("longitude")
    time_stamp = payload.get("time_stamp")

    if not vehicle_id:
        return jsonify({"success": False, "message": "Missing vehicle_id"}), 400

    hit_entry = {
        "cam_id": cam_id,
        "latitude": lat,
        "longitude": lng,
        "time_stamp": time_stamp
    }

    # Fetch vehicle record to inspect blacklist status
    record = vehicles_col.find_one({"vehicle_id": vehicle_id})
    is_blacklisted = record.get("is_blacklisted", False) if record else False
    reason = record.get("blacklist_reason", "None") if record else "None"

    # Push hit into MongoDB trail array
    vehicles_col.update_one(
        {"vehicle_id": vehicle_id},
        {
            "$push": {"trail": hit_entry},
            "$set": {
                "last_occurrence": hit_entry,
                "is_blacklisted": is_blacklisted,
                "blacklist_reason": reason
            },
            "$inc": {"total_detections": 1}
        },
        upsert=True
    )

    alert_data = {
        "vehicle_id": vehicle_id,
        "is_blacklisted": is_blacklisted,
        "reason": reason,
        "hit": hit_entry
    }

    # Broadcast real-time event to all connected frontend clients
    if is_blacklisted:
        socketio.emit('vehicle_alert', alert_data)

    return jsonify({"success": True, "data": alert_data}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port)
