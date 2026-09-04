import os
import certifi
from flask import Blueprint, jsonify
from pymongo import MongoClient

dashboard_bp = Blueprint('dashboard', __name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://user1:user12326@cluster0.rn7dha5.mongodb.net/?appName=Cluster0")
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["traffic_system"]

@dashboard_bp.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    try:
        # 1. Count active cameras
        total_cameras = db["cameras"].count_documents({})
        
        # 2. Count distinct vehicles detected
        unique_vehicles = len(db["vehicle_logs"].distinct("vehicle_id"))
        
        # 3. Count total ANPR reads
        total_anpr_reads = db["vehicle_logs"].count_documents({})
        
        # 4. Count active alerts (blacklisted vehicles detected)
        active_alerts_count = db["alerted_vehicles"].count_documents({"is_blacklisted": True})
        
        return jsonify({
            "success": True,
            "data": {
                "active_cameras": total_cameras,
                "vehicles_detected": unique_vehicles,
                "anpr_reads": total_anpr_reads,
                "active_alerts": active_alerts_count
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@dashboard_bp.route('/api/dashboard/recent-activity', methods=['GET'])
def get_recent_anpr_activity():
    try:
        # Pipeline to join vehicle logs with camera locations
        pipeline = [
            {"$sort": {"time_stamp": -1}},
            {"$limit": 10},
            {
                "$lookup": {
                    "from": "cameras",
                    "localField": "cam_id",
                    "foreignField": "cam_id",
                    "as": "cam_info"
                }
            },
            {"$unwind": {"path": "$cam_info", "preserveNullAndEmptyArrays": True}}
        ]
        
        logs = list(db["vehicle_logs"].aggregate(pipeline))
        
        formatted_activity = []
        for log in logs:
            cam_data = log.get("cam_info", {})
            formatted_activity.append({
                "vehicle_id": log.get("vehicle_id"),
                "cam_id": log.get("cam_id"),
                "time_stamp": log.get("time_stamp"),
                "latitude": cam_data.get("latitude"),
                "longitude": cam_data.get("longitude")
            })
            
        return jsonify({"success": True, "data": formatted_activity}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500