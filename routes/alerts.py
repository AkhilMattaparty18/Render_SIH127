import os
import certifi
import threading
import time
from datetime import datetime, timedelta
from flask import Blueprint, jsonify
from pymongo import MongoClient

alerts_bp = Blueprint('alerts', __name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://user1:user12326@cluster0.rn7dha5.mongodb.net/?appName=Cluster0")
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["traffic_system"]


def calculate_priority_and_reason(alert_type):
    """
    Returns (priority, blacklist_reason) based on threat levels:
    - HIGH: Stolen vehicles or explicit blacklists.
    - MEDIUM: Speeding or severe route deviations.
    - LOW: Pattern anomalies like looping within an hour.
    """
    mapping = {
        "STOLEN": ("HIGH", "Stolen Vehicle"),
        "BLACKLISTED": ("HIGH", "Blacklisted Vehicle"),
        "SPEEDING": ("MEDIUM", "Over Speeding Detected"),
        "LOOPING": ("LOW", "Repeated Traversal / Looping Pattern Detected")
    }
    return mapping.get(alert_type, ("LOW", "Suspicious Activity"))


def detect_looping_anomalies():
    """Background task running every minute to process telemetry into vehicle_alerts schema."""
    while True:
        try:
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            
            # Query recent telemetry logs from the last hour
            pipeline = [
                {"$match": {"time_stamp": {"$gte": one_hour_ago.isoformat() + "Z"}}},
                {"$sort": {"time_stamp": 1}},
                {"$group": {
                    "_id": "$vehicle_id",
                    "total_detections": {"$sum": 1},
                    "detections": {
                        "$push": {
                            "cam_id": "$cam_id",
                            "time_stamp": "$time_stamp",
                            "latitude": "$latitude",
                            "longitude": "$longitude"
                        }
                    }
                }},
                {"$match": {"total_detections": {"$gte": 3}}}  # Flag if detected 3+ times in an hour
            ]
            
            detected_anomalies = list(db["vehicle_telemetry"].aggregate(pipeline))
            
            for item in detected_anomalies:
                vehicle_id = item["_id"]
                trail = item["detections"]
                total_detections = item["total_detections"]
                
                first_occurrence = trail[0]
                last_occurrence = trail[-1]
                
                priority, reason = calculate_priority_and_reason("LOOPING")
                
                alert_doc = {
                    "vehicle_id": vehicle_id,
                    "first_occurrence": {
                        "cam_id": str(first_occurrence.get("cam_id", "")),
                        "time_stamp": first_occurrence.get("time_stamp", ""),
                        "latitude": float(first_occurrence.get("latitude", 0.0)),
                        "longitude": float(first_occurrence.get("longitude", 0.0))
                    },
                    "is_blacklisted": False,  # Set to False for low-priority looping
                    "last_occurrence": {
                        "cam_id": str(last_occurrence.get("cam_id", "")),
                        "time_stamp": last_occurrence.get("time_stamp", ""),
                        "latitude": float(last_occurrence.get("latitude", 0.0)),
                        "longitude": float(last_occurrence.get("longitude", 0.0))
                    },
                    "total_detections": int(total_detections),
                    "trail": [
                        {
                            "cam_id": str(point.get("cam_id", "")),
                            "time_stamp": point.get("time_stamp", ""),
                            "latitude": float(point.get("latitude", 0.0)),
                            "longitude": float(point.get("longitude", 0.0))
                        }
                        for point in trail
                    ],
                    "updated_at": datetime.utcnow().isoformat(),
                    "blacklist_reason": reason,
                    "priority": priority,  # Added to allow frontend priority rendering
                    "generated_at": datetime.utcnow().isoformat()
                }
                
                # Insert or update record in vehicle_alerts collection
                db["vehicle_alerts"].update_one(
                    {"vehicle_id": vehicle_id},
                    {"$set": alert_doc},
                    upsert=True
                )
                
        except Exception as e:
            print(f"Error in anomaly loop: {e}")
            
        time.sleep(60)


# Start anomaly detection loop in background
loop_thread = threading.Thread(target=detect_looping_anomalies, daemon=True)
loop_thread.start()


@alerts_bp.route('/api/alerts', methods=['GET'])
def get_all_alerts():
    try:
        alerts_cursor = db["vehicle_alerts"].find({}, {"_id": 0}).sort("generated_at", -1)
        alerts_list = list(alerts_cursor)
        return jsonify({"success": True, "count": len(alerts_list), "data": alerts_list}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@alerts_bp.route('/api/alerts/<vehicle_id>', methods=['GET'])
def get_alert_detail(vehicle_id):
    try:
        target_id = vehicle_id.upper()
        alert = db["vehicle_alerts"].find_one({"vehicle_id": target_id}, {"_id": 0})
        
        if not alert:
            return jsonify({"success": False, "message": f"No alert found for vehicle: {target_id}"}), 404
            
        return jsonify({"success": True, "data": alert}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
