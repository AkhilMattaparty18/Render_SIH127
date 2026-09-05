import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
# Enable CORS for all domains to prevent cross-origin fetch failures
CORS(app)

# Database Connection
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://user1:user12326@cluster0.rn7dha5.mongodb.net/sirius_db?retryWrites=true&w=majority"
)

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.get_database("sirius_db")
    # Ping database to verify connection on startup
    client.admin.command('ping')
    print("Connected successfully to MongoDB Atlas")
except Exception as e:
    print(f"MongoDB Connection Error: {e}")

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    try:
        total_cams = len(db.vehicle_logs.distinct("cam_id")) if "vehicle_logs" in db.list_collection_names() else 0
        total_vehicles = db.vehicle_logs.count_documents({}) if "vehicle_logs" in db.list_collection_names() else 0
        anpr_reads = db.vehicle_logs.count_documents({"vehicle_id": {"$ne": None}}) if "vehicle_logs" in db.list_collection_names() else 0
        active_alerts = db.blacklisted_vehicles.count_documents({}) if "blacklisted_vehicles" in db.list_collection_names() else 0

        return jsonify({
            "success": True,
            "data": {
                "active_cameras": total_cams,
                "vehicles_detected": total_vehicles,
                "anpr_reads": anpr_reads,
                "active_alerts": active_alerts
            }
        }), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/analytics/cameras', methods=['GET'])
def get_analytics_cameras():
    try:
        if "vehicle_logs" not in db.list_collection_names():
            return jsonify({"success": True, "data": []}), 200

        # Query distinct camera IDs across all logs
        raw_cam_ids = db.vehicle_logs.distinct("cam_id")
        cameras = []

        for cid in raw_cam_ids:
            if cid is None:
                continue
            
            str_id = str(cid)
            # Match either as string or int to find the latest lat/lng
            sample_doc = db.vehicle_logs.find_one(
                {"cam_id": {"$in": [str_id, int(str_id) if str_id.isdigit() else str_id]}},
                {"latitude": 1, "longitude": 1, "_id": 0}
            ) or {}

            cameras.append({
                "cam_id": str_id,
                "latitude": sample_doc.get("latitude", 17.4483),
                "longitude": sample_doc.get("longitude", 78.3915)
            })

        return jsonify({"success": True, "data": cameras}), 200
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/api/analytics/camera-metrics', methods=['GET'])
def get_camera_metrics():
    try:
        cam_id_param = request.args.get('cam_id', '')
        if not cam_id_param:
            return jsonify({"success": False, "message": "cam_id parameter is required"}), 400

        # Support both string and integer matching in MongoDB queries
        match_ids = [cam_id_param]
        if cam_id_param.isdigit():
            match_ids.append(int(cam_id_param))

        # Query logs matching this camera ID
        logs = list(db.vehicle_logs.find({"cam_id": {"$in": match_ids}}))
        count = len(logs)

        # Calculate metrics safely
        speeds = [doc.get("speed", 0) for doc in logs if isinstance(doc.get("speed"), (int, float))]
        avg_speed = round(sum(speeds) / len(speeds), 1) if speeds else 42.5

        capacity = min(100, int((count / 50.0) * 100)) if count > 0 else 15
        
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

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
