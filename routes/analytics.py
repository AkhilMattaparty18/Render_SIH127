from flask import Blueprint, request, jsonify
from datetime import datetime, timedelta

analytics_bp = Blueprint('analytics', __name__)
from app import db

# 1. Camera list endpoint required by dropdown
@analytics_bp.route('/api/analytics/cameras', methods=['GET'])
def get_analytics_cameras():
    try:
        # Fetch directly from the 'cameras' collection instead of 'activity'
        cameras_cursor = db.cameras.find({}, {"_id": 0, "cam_id": 1, "latitude": 1, "longitude": 1})
        cameras = list(cameras_cursor)

        return jsonify({"success": True, "data": cameras}), 200
    except Exception as e:
        print("Cameras Fetch Error:", str(e))
        return jsonify({"success": False, "message": str(e)}), 500


# 2. Camera metrics endpoint
@analytics_bp.route('/api/analytics/camera-metrics', methods=['GET'])
def get_camera_metrics():
    cam_id = request.args.get('cam_id')
    if not cam_id:
        return jsonify({"success": False, "message": "cam_id is required"}), 400

    try:
        # Fetch metrics from the 'vehicle_logs' collection instead of 'activity'
        records = list(db.vehicle_logs.find({"cam_id": cam_id}))

        if not records:
            return jsonify({
                "success": True,
                "data": {
                    "average_speed": 0,
                    "status": "No Active Traffic",
                    "status_class": "text-yellow-400 font-semibold",
                    "vehicle_count": 0,
                    "capacity_percentage": 0
                }
            }), 200

        total_vehicles = len(records)
        avg_speed = 45  # Default or dynamic speed value

        return jsonify({
            "success": True,
            "data": {
                "average_speed": avg_speed,
                "status": "Optimal",
                "status_class": "text-green-400 font-semibold",
                "vehicle_count": total_vehicles,
                "capacity_percentage": min(int((total_vehicles / 100) * 100), 100)
            }
        }), 200

    except Exception as e:
        print("Analytics Error:", str(e))
        return jsonify({"success": False, "message": str(e)}), 500
