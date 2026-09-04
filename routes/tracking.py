import os
import certifi
from flask import Blueprint, jsonify, request
from pymongo import MongoClient

tracking_bp = Blueprint('tracking', __name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://user1:user12326@cluster0.rn7dha5.mongodb.net/?appName=Cluster0")
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["traffic_system"]

@tracking_bp.route('/api/track', methods=['GET'])
def track_vehicle():
    vehicle_id = request.args.get('vehicle_id')
    if not vehicle_id:
        return jsonify({"success": False, "message": "Query parameter 'vehicle_id' is required"}), 400
        
    target_id = vehicle_id.strip().upper()
    
    try:
        # 1. Fetch trail directly from vehicle_trails collection
        trail_doc = db["vehicle_trails"].find_one({"vehicle_id": target_id}, {"_id": 0})
        
        # 2. Check if vehicle is blacklisted
        blacklist_info = db["blacklisted_vehicles"].find_one({"vehicle_id": target_id}, {"_id": 0})
        
        if not trail_doc:
            return jsonify({"success": False, "message": f"No trail data found for vehicle {target_id}"}), 404
            
        response_payload = {
            "vehicle_id": target_id,
            "is_blacklisted": bool(blacklist_info),
            "blacklist_reason": blacklist_info.get("reason") if blacklist_info else None,
            "total_detections": trail_doc.get("total_detections", 0),
            "trail": trail_doc.get("trail", [])
        }
        
        return jsonify({"success": True, "data": response_payload}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500