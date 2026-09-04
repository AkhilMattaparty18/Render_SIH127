import os
import json
import re
import certifi
from flask import Blueprint, jsonify, request
from pymongo import MongoClient

tracking_bp = Blueprint('tracking', __name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://user1:user12326@cluster0.rn7dha5.mongodb.net/?appName=Cluster0")
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["traffic_system"]

TRAILS_DIR = "vehicle_trails"
os.makedirs(TRAILS_DIR, exist_ok=True)

@tracking_bp.route('/api/track', methods=['GET'])
def track_vehicle():
    vehicle_id = request.args.get('vehicle_id')
    if not vehicle_id:
        return jsonify({"success": False, "message": "Query parameter 'vehicle_id' is required"}), 400
        
    raw_id = vehicle_id.strip()
    
    # Case-insensitive regex match (handles upper/lower case variations)
    regex_query = re.compile(f"^{re.escape(raw_id)}$", re.IGNORECASE)
    
    try:
        # Search vehicle_logs using common field names
        query = {
            "$or": [
                {"vehicle_id": regex_query},
                {"plate_number": regex_query},
                {"license_plate": regex_query}
            ]
        }
        
        logs_cursor = db["vehicle_logs"].find(query).sort("timestamp", 1)
        
        trail = []
        for log in logs_cursor:
            log_data = {
                "camera_id": log.get("camera_id"),
                "location": log.get("location"),
                "timestamp": log.get("timestamp").isoformat() if hasattr(log.get("timestamp"), "isoformat") else log.get("timestamp"),
                "confidence": log.get("confidence")
            }
            trail.append(log_data)
            
        if not trail:
            return jsonify({
                "success": False, 
                "message": f"No trail data found in 'vehicle_logs' for vehicle '{raw_id}'"
            }), 404

        # Check blacklist status
        blacklist_info = db["blacklisted_vehicles"].find_one({
            "$or": [
                {"vehicle_id": regex_query},
                {"plate_number": regex_query}
            ]
        }, {"_id": 0})
        
        response_payload = {
            "vehicle_id": raw_id.upper(),
            "is_blacklisted": bool(blacklist_info),
            "blacklist_reason": blacklist_info.get("reason") if blacklist_info else None,
            "total_detections": len(trail),
            "trail": trail
        }
        
        # Save to local JSON file under vehicle_trails directory
        file_path = os.path.join(TRAILS_DIR, f"{raw_id.upper()}.json")
        with open(file_path, "w") as f:
            json.dump(response_payload, f, indent=4)
        
        return jsonify({"success": True, "data": response_payload}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
