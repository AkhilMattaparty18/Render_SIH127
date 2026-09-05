import os
import random
from datetime import datetime, timedelta
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
import certifi

app = Flask(__name__)
CORS(app)  # Enable Cross-Origin Resource Sharing for your Render deployment

# MongoDB Atlas Connection
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://user1:user12326@cluster0.rn7dha5.mongodb.net/?appName=Cluster0"
)

# Initialize PyMongo Client with Certifi for SSL/TLS verification on Render
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())

# Replace 'sirius_db' and 'camera_logs' with your actual database and collection names
db = client["sirius_db"]
logs_collection = db["camera_logs"]


@app.route("/api/analytics/cameras", methods=["GET"])
def get_camera_junctions():
    """
    Fetches all unique camera IDs from MongoDB to dynamically populate the dropdown.
    """
    try:
        cameras = logs_collection.distinct("cam_id")
        camera_list = [{"cam_id": cam} for cam in cameras if cam]
        return jsonify({
            "success": True,
            "count": len(camera_list),
            "data": camera_list
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Database query failed: {str(e)}"
        }), 500


@app.route("/api/analytics/camera-metrics", methods=["GET"])
def get_camera_metrics():
    """
    Counts vehicles at a camera junction within the last 1 minute from MongoDB,
    computes average speed, status, and class distribution.
    """
    try:
        cam_id = request.args.get("cam_id")
        time_window_minutes = int(request.args.get("time_window_minutes", 1))

        if not cam_id:
            return jsonify({
                "success": False,
                "message": "cam_id query parameter is required"
            }), 400

        now = datetime.utcnow()
        time_threshold = now - timedelta(minutes=time_window_minutes)

        # MongoDB Query: Fetch camera logs within the 1-minute window
        query = {
            "cam_id": cam_id,
            "time_stamp": {"$gte": time_threshold}
        }

        filtered_logs = list(logs_collection.find(query))
        vehicle_count = len(filtered_logs)

        # Dynamic Speed & Traffic Status Algorithm (based on 1-minute volume)
        if vehicle_count == 0:
            speed_kmh = 60
            status = "Clear Road"
            status_class = "text-green-400"
            capacity_percentage = 0
        elif vehicle_count <= 5:
            speed_kmh = random.randint(48, 58)
            status = "Clear Road"
            status_class = "text-green-400"
            capacity_percentage = min(100, vehicle_count * 15)
        elif vehicle_count <= 15:
            speed_kmh = random.randint(30, 45)
            status = "Moderate Traffic"
            status_class = "text-yellow-400"
            capacity_percentage = min(100, vehicle_count * 6)
        else:
            speed_kmh = random.randint(10, 25)
            status = "Heavy Congestion"
            status_class = "text-red-400"
            capacity_percentage = min(100, int(vehicle_count * 4))

        # Vehicle Class Distribution Calculation
        distribution = {"Sedan/Hatchback": 0, "SUVs / Commercial": 0, "Two-Wheelers": 0}

        if vehicle_count > 0:
            for log in filtered_logs:
                v_type = log.get("vehicle_type", "Sedan")
                if v_type in ["Sedan", "Hatchback"]:
                    distribution["Sedan/Hatchback"] += 1
                elif v_type in ["SUV", "Commercial"]:
                    distribution["SUVs / Commercial"] += 1
                else:
                    distribution["Two-Wheelers"] += 1

            for key in distribution:
                distribution[key] = round((distribution[key] / vehicle_count) * 100)

        return jsonify({
            "success": True,
            "cam_id": cam_id,
            "time_window_minutes": time_window_minutes,
            "data": {
                "vehicle_count": vehicle_count,
                "average_speed": f"{speed_kmh} km/h",
                "status": status,
                "status_class": status_class,
                "capacity_percentage": f"{capacity_percentage}%",
                "class_distribution": distribution
            }
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Database query failed: {str(e)}"
        }), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
