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
        # Step 1: Query raw logs for the given vehicle_id sorted chronologically
        logs_cursor = db["vehicle_logs"].find(
            {"vehicle_id": target_id},
            {"_id": 0}
        ).sort("time_stamp", 1)
        logs = list(logs_cursor)
        
        if not logs:
            return jsonify({"success": False, "message": f"No logs found for vehicle {target_id}"}), 404

        # Step 2: Extract unique camera IDs to fetch coordinates
        cam_ids = list(set(log["cam_id"] for log in logs if "cam_id" in log))
        cameras_cursor = db["cameras"].find(
            {"cam_id": {"$in": cam_ids}},
            {"_id": 0}
        )
        camera_map = {cam["cam_id"]: cam for cam in cameras_cursor}

        # Step 3: Reconstruct the trail path
        trail = []
        for log in logs:
            cam_id = log.get("cam_id")
            cam_info = camera_map.get(cam_id, {})
            trail.append({
                "cam_id": cam_id,
                "time_stamp": log.get("time_stamp"),
                "latitude": cam_info.get("latitude"),
                "longitude": cam_info.get("longitude")
            })

        # Step 4: Construct document and save/update in vehicle_trails collection
        trail_doc = {
            "vehicle_id": target_id,
            "generated_at": logs[-1].get("time_stamp"),
            "total_detections": len(trail),
            "trail": trail
        }

        db["vehicle_trails"].update_one(
            {"vehicle_id": target_id},
            {"$set": trail_doc},
            upsert=True
        )

        # Step 5: Check blacklist status for response payload
        blacklist_info = db["blacklisted_vehicles"].find_one({"vehicle_id": target_id}, {"_id": 0})

        response_payload = {
            "vehicle_id": target_id,
            "is_blacklisted": bool(blacklist_info),
            "blacklist_reason": blacklist_info.get("reason") if blacklist_info else None,
            "total_detections": len(trail),
            "trail": trail
        }
        
        return jsonify({"success": True, "data": response_payload}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
