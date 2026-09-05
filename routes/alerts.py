import os
from datetime import datetime, timedelta, timezone
from flask import Blueprint, jsonify, request
from pymongo import MongoClient

analytics_bp = Blueprint('analytics_bp', __name__)

MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://user1:user12326@cluster0.rn7dha5.mongodb.net/sirius_db?retryWrites=true&w=majority"
)

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.get_database("sirius_db")
    client.admin.command('ping')
    print("Connected successfully to MongoDB Atlas from Analytics")
except Exception as e:
    print(f"MongoDB Connection Error: {e}")

@analytics_bp.route('/api/analytics/cameras', methods=['GET'])
def get_analytics_cameras():
    try:
        if "vehicle_logs" not in db.list_collection_names():
            return jsonify({"success": True, "data": []}), 200

        raw_cam_ids = db.vehicle_logs.distinct("cam_id")
        cameras = []

        for cid in raw_cam_ids:
            if cid is None:
                continue
            
            str_id = str(cid)
            query_filter = {"cam_id": {"$in": [str_id, int(str_id) if str_id.isdigit() else str_id]}}
            
            sample_doc = db.vehicle_logs.find_one(
                query_filter,
                {"latitude": 1, "longitude": 1, "_id": 0},
                sort=[("_id", -1)]
            ) or {}

            cameras.append({
                "cam_id": str_id,
                "latitude": sample_doc.get("latitude", 17.4483),
                "longitude": sample_doc.get("longitude", 78.3915)
            })

        return jsonify({"success": True, "data": cameras}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@analytics_bp.route('/api/analytics/camera-metrics', methods=['GET'])
def get_camera_metrics():
    try:
        cam_id_param = request.args.get('cam_id', '')
        if not cam_id_param:
            return jsonify({"success": False, "message": "cam_id parameter is required"}), 400

        match_ids = [cam_id_param]
        if cam_id_param.isdigit():
            match_ids.append(int(cam_id_param))

        # Calculate time threshold for exactly 1 hour ago
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

        # Strictly query logs created in the past 1 hour across common timestamp formats
        query = {
            "cam_id": {"$in": match_ids},
            "$or": [
                {"timestamp": {"$gte": one_hour_ago}},                              # Native Mongo Date
                {"timestamp": {"$gte": one_hour_ago.isoformat()}},                  # ISO String (e.g. 2026-09-05T21:00:00Z)
                {"timestamp": {"$gte": one_hour_ago.strftime("%Y-%m-%d %H:%M:%S")}} # Standard String (e.g. 2026-09-05 21:00:00)
            ]
        }

        logs = list(db.vehicle_logs.find(query))
        count = len(logs)

        # Calculate average speed safely for the past hour
        speeds = [doc.get("speed", 0) for doc in logs if isinstance(doc.get("speed"), (int, float))]
        avg_speed = round(sum(speeds) / len(speeds), 1) if speeds else 0.0

        # Capacity based on vehicles logged in the last hour
        capacity = min(100, int((count / 50.0) * 100)) if count > 0 else 0
        
        status = "Normal"
        status_class = "text-green-400 font-semibold"
        if capacity > 80:
            status = "Heavy Traffic"
            status_class = "text-red-400 font-semibold"
        elif capacity > 50:
            status = "Moderate Traffic"
            status_class = "text-yellow-400 font-semibold"

        return jsonify({
            "success": True,
            "data": {
                "cam_id": str(cam_id_param),
                "average_speed": avg_speed,
                "vehicle_count": count,
                "capacity_percentage": capacity,
                "status": status,
                "status_class": status_class
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500
