import os
import json
import certifi
from flask import Blueprint, jsonify, request
from pymongo import MongoClient

tracking_bp = Blueprint('tracking', __name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://user1:user12326@cluster0.rn7dha5.mongodb.net/?appName=Cluster0")
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["traffic_system"]

# Ensure local directory for storing JSON trail files exists
TRAILS_DIR = "vehicle_trails"
os.makedirs(TRAILS_DIR, exist_ok=True)

@tracking_bp.route('/api/track', methods=['GET'])
def track_vehicle():
    vehicle_id = request.args.get('vehicle_id')
    if not vehicle_id:
        return jsonify({"success": False, "message": "Query parameter 'vehicle_id' is required"}), 400
        
    target_id = vehicle_id.strip().upper()
    
    try:
        # 1. Query vehicle_logs collection dynamically for matching vehicle_id
        logs_cursor = db["vehicle_logs"].find({"vehicle_id": target_id}).sort("timestamp", 1)
        
        trail = []
        for log in logs_cursor:
            # Strip MongoDB internal _id field and normalize timestamp
            log_data = {
                "camera_id": log.get("camera_id"),
                "location": log.get("location"),
                "timestamp": log.get("timestamp").isoformat() if hasattr(log.get("timestamp"), "isoformat") else log.get("timestamp"),
                "confidence": log.get("confidence")
            }
            trail.append(log_data)
            
        if not trail:
            return jsonify({"success": False, "message": f"No trail data found for vehicle {target_id}"}), 404

        # 2. Check if vehicle is blacklisted
        blacklist_info = db["blacklisted_vehicles"].find_one({"vehicle_id": target_id}, {"_id": 0})
        
        # 3. Construct response payload
        response_payload = {
            "vehicle_id": target_id,
            "is_blacklisted": bool(blacklist_info),
            "blacklist_reason": blacklist_info.get("reason") if blacklist_info else None,
            "total_detections": len(trail),
            "trail": trail
        }
        
        # 4. Save path data to local JSON file under vehicle_trails directory
        file_path = os.path.join(TRAILS_DIR, f"{target_id}.json")
        with open(file_path, "w") as f:
            json.dump(response_payload, f, indent=4)
        
        return jsonify({"success": True, "data": response_payload}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
