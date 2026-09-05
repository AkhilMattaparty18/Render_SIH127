from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
import traceback

app = Flask(__name__)
CORS(app)

# MongoDB Atlas Connection Configuration
MONGO_URI = "mongodb+srv://user1:user12326@cluster0.rn7dha5.mongodb.net/?appName=Cluster0"
client = MongoClient(MONGO_URI)
db = client["sirius_db"]

# Collections
logs_collection = db["vehicle_logs"]
cameras_collection = db["cameras"]
trails_collection = db["vehicle_trails"]
alerts_collection = db["alerted_vehicles"]

# --- ANALYTICS ENDPOINTS ---

@app.route('/api/analytics/cameras', methods=['GET'])
def get_cameras():
    """Returns the list of all registered cameras and their coordinates."""
    try:
        # Fetch cameras from the dedicated collection
        cameras = list(cameras_collection.find({}, {"_id": 0}))
        
        # Fallback query if 'cameras' collection is empty
        if not cameras:
            pipeline = [
                {"$group": {"_id": "$cam_id"}},
                {"$project": {"_id": 0, "cam_id": "$_id"}}
            ]
            cameras = list(logs_collection.aggregate(pipeline))

        return jsonify({"success": True, "data": cameras}), 200
    except Exception as e:
        print("Server Error in /api/analytics/cameras:", traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/analytics/camera-metrics', methods=['GET'])
def get_camera_metrics():
    """Calculates traffic metrics for a specific camera ID based on logs."""
    try:
        cam_id = request.args.get('cam_id')
        if not cam_id:
            return jsonify({"success": False, "message": "Missing camera ID"}), 400

        # Query vehicle count for the requested camera junction
        recent_count = logs_collection.count_documents({"cam_id": cam_id})
        
        # Calculate dynamic speed and capacity metrics
        avg_speed = max(18, 65 - (recent_count * 2))
        capacity = min(100, int((recent_count / 25) * 100))
        
        if avg_speed < 25:
            status = "Congested"
            status_class = "text-red-400 font-semibold"
        elif avg_speed < 45:
            status = "Moderate"
            status_class = "text-yellow-400 font-semibold"
        else:
            status = "Clear"
            status_class = "text-green-400 font-semibold"

        return jsonify({
            "success": True,
            "data": {
                "cam_id": cam_id,
                "average_speed": avg_speed,
                "status": status,
                "status_class": status_class,
                "vehicle_count": recent_count,
                "capacity_percentage": capacity
            }
        }), 200

    except Exception as e:
        print("Server Error in /api/analytics/camera-metrics:", traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


# --- DASHBOARD ENDPOINTS ---

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Fetches high-level system statistics."""
    try:
        active_cameras = len(cameras_collection.distinct("cam_id"))
        total_vehicles = len(logs_collection.distinct("vehicle_id"))
        anpr_reads = logs_collection.count_documents({})
        active_alerts = alerts_collection.count_documents({"is_blacklisted": True})

        return jsonify({
            "success": True,
            "data": {
                "active_cameras": active_cameras,
                "vehicles_detected": total_vehicles,
                "anpr_reads": anpr_reads,
                "active_alerts": active_alerts
            }
        }), 200
    except Exception as e:
        print("Server Error in /api/dashboard/stats:", traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/dashboard/recent-activity', methods=['GET'])
def get_recent_activity():
    """Fetches recent vehicle logs paired with camera coordinates."""
    try:
        logs = list(logs_collection.find({}, {"_id": 0}).sort("time_stamp", -1).limit(10))
        
        # Enrich logs with camera coordinates
        cameras = {c["cam_id"]: c for c in cameras_collection.find({}, {"_id": 0})}
        for log in logs:
            cam_info = cameras.get(log.get("cam_id"))
            if cam_info:
                log["latitude"] = cam_info.get("latitude")
                log["longitude"] = cam_info.get("longitude")

        return jsonify({"success": True, "data": logs}), 200
    except Exception as e:
        print("Server Error in /api/dashboard/recent-activity:", traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


# --- TRACKING & ALERTS ENDPOINTS ---

@app.route('/api/track', methods=['GET'])
def track_vehicle():
    """Tracks a specific vehicle path by vehicle ID."""
    try:
        vehicle_id = request.args.get('vehicle_id')
        if not vehicle_id:
            return jsonify({"success": False, "message": "Missing vehicle ID"}), 400

        doc = trails_collection.find_one({"vehicle_id": vehicle_id}, {"_id": 0})
        if not doc:
            return jsonify({"success": False, "message": f"No trail data found for plate: {vehicle_id}"}), 404

        return jsonify({"success": True, "data": doc}), 200
    except Exception as e:
        print("Server Error in /api/track:", traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Fetches blacklisted vehicle alert documents."""
    try:
        alerts = list(alerts_collection.find({"is_blacklisted": True}, {"_id": 0}))
        return jsonify({"success": True, "data": alerts}), 200
    except Exception as e:
        print("Server Error in /api/alerts:", traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
