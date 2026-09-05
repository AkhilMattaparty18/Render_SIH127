from flask import Flask, jsonify, request
from flask_cors import CORS  # Prevent CORS errors on Render
from pymongo import MongoClient
import traceback

app = Flask(__name__)
CORS(app)  # Enable CORS across all endpoints

client = MongoClient("YOUR_MONGODB_CONNECTION_STRING")
db = client["sirius_db"]
logs_collection = db["vehicle_logs"]

@app.route('/api/analytics/camera-metrics', methods=['GET'])
def get_camera_metrics():
    try:
        cam_id = request.args.get('cam_id')
        if not cam_id:
            return jsonify({"success": False, "message": "Missing camera ID"}), 400

        # Query total logs for specified camera
        recent_count = logs_collection.count_documents({"cam_id": cam_id})
        
        # Calculate dynamic metrics
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
        print("Server Error:", traceback.format_exc())
        return jsonify({"success": False, "error": str(e)}), 500
