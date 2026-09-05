import os
from datetime import datetime, timedelta, timezone
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient

# Import Blueprints
from routes.dashboard import dashboard_bp
from routes.alerts import alerts_bp
from routes.tracking import tracking_bp

app = Flask(__name__)
CORS(app)

# Register Existing Blueprints
app.register_blueprint(dashboard_bp)
app.register_blueprint(alerts_bp)
app.register_blueprint(tracking_bp)

# MongoDB Connection
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://user1:user12326@cluster0.rn7dha5.mongodb.net/sirius_db?retryWrites=true&w=majority"
)

try:
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = client.get_database("sirius_db")
    client.admin.command('ping')
    print("Connected successfully to MongoDB Atlas")
except Exception as e:
    print(f"MongoDB Connection Error: {e}")


# Health Check
@app.route('/', methods=['GET'])
def health_check():
    return jsonify({
        "status": "online",
        "service": "SIRIUS Command Dashboard API"
    }), 200


# ANALYTICS ENDPOINTS
@app.route('/api/analytics/cameras', methods=['GET'])
def get_analytics_cameras():
    try:
        if "vehicle_logs" not in db.list_collection_names():
            return jsonify({"success": True, "data": []}), 200

        raw_cam_ids = db.vehicle_logs.distinct("cam_id")
        cameras = []
        seen_ids = set()

        for cid in raw_cam_ids:
            if cid is None:
                continue
            
            str_id = str(cid).strip()
            if str_id in seen_ids:
                continue
            seen_ids.add(str_id)

            query_filter = {"cam_id": {"$in": [str_id, int(str_id) if str_id.isdigit() else str_id]}}
            sample_doc = db.vehicle_logs.find_one(
                query_filter,
                {"latitude": 1, "longitude": 1, "_id": 0},
                sort=[("_id", -1)]
            ) or {}

            default_lat = 17.4325 if str_id == "123" else (17.4483 if str_id == "124" else 17.4065)
            default_lng = 78.4071 if str_id == "123" else (78.3915 if str_id == "124" else 78.4772)

            cameras.append({
                "cam_id": str_id,
                "latitude": sample_doc.get("latitude") or default_lat,
                "longitude": sample_doc.get("longitude") or default_lng
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

        match_ids = [cam_id_param]
        if cam_id_param.isdigit():
            match_ids.append(int(cam_id_param))

        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

        query = {
            "cam_id": {"$in": match_ids},
            "$or": [
                {"timestamp": {"$gte": one_hour_ago}},
                {"timestamp": {"$gte": one_hour_ago.isoformat()}},
                {"timestamp": {"$gte": one_hour_ago.strftime("%Y-%m-%d %H:%M:%S")}}
            ]
        }

        logs = list(db.vehicle_logs.find(query))
        count = len(logs)

        speeds = [doc.get("speed", 0) for doc in logs if isinstance(doc.get("speed"), (int, float))]
        avg_speed = round(sum(speeds) / len(speeds), 1) if speeds else 0.0

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


if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
