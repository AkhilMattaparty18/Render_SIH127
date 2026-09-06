from datetime import datetime, timedelta
from flask import Blueprint, jsonify, request

analytics_bp = Blueprint('analytics', __name__)

# Assuming you have access to your database collection (e.g., MongoDB or SQLAlchemy)
# from models import vehicle_logs_collection 


@analytics_bp.route('/api/analytics/cameras', methods=['GET'])
def get_analytics_cameras():
  """Returns a list of unique cameras with their latest coordinates."""
  try:
    # Fetch all logs or a distinct list of cameras from your database
    # Example using MongoDB aggregate or distinct lookup:
    # logs = list(vehicle_logs_collection.find({}, {"cam_id": 1, "latitude": 1, "longitude": 1}))
    
    # Placeholder query logic (adjust to your DB connection):
    logs = list(vehicle_logs_collection.find()) # or your query method
    
    camera_map = {}
    for log in logs:
      cam_id = log.get("cam_id")
      if cam_id and cam_id not in camera_map:
        camera_map[cam_id] = {
            "cam_id": cam_id,
            "latitude": log.get("latitude"),
            "longitude": log.get("longitude")
        }

    return jsonify({"success": True, "data": list(camera_map.values())}), 200

  except Exception as e:
    return jsonify({"success": False, "message": str(e)}), 500


@analytics_bp.route('/api/analytics/camera-metrics', methods=['GET'])
def get_camera_metrics():
  """
  Implements your algorithm:
  1. Filters by time_stamp (last hour) and cam_id, then counts vehicles.
  2. Sets traffic status variables based on the count.
  3. Returns metrics including total vehicle count for that camera in the last hour.
  """
  cam_id = request.args.get('cam_id')
  if not cam_id:
    return jsonify({"success": False, "message": "cam_id is required"}), 400

  try:
    # Define the time window for the last hour
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    # Step 1: Query database for logs matching this cam_id within the last hour
    # If your timestamps are stored as ISO strings, ensure proper query comparison:
    query = {
        "cam_id": cam_id,
        "time_stamp": {"$gte": one_hour_ago.isoformat()} 
    }
    
    camera_logs = list(vehicle_logs_collection.find(query))
    vehicle_count = len(camera_logs)

    # Step 2: Set traffic variables based on the vehicle count
    traffic_status = "Normal"
    status_class = "text-green-400 font-semibold"
    average_speed = 45
    capacity_percentage = min(round((vehicle_count / 25) * 100), 100)

    if vehicle_count > 15:
      traffic_status = "Heavy Congestion"
      status_class = "text-red-400 font-semibold"
      average_speed = 14
      capacity_percentage = 95
    elif vehicle_count > 8:
      traffic_status = "Moderate Traffic"
      status_class = "text-yellow-400 font-semibold"
      average_speed = 28
      capacity_percentage = 60

    # Also calculate total system-wide vehicles in the last hour if needed
    global_query = {"time_stamp": {"$gte": one_hour_ago.isoformat()}}
    total_system_vehicles_last_hour = vehicle_logs_collection.count_documents(global_query)

    response_data = {
        "cam_id": cam_id,
        "vehicle_count": vehicle_count,
        "average_speed": average_speed,
        "capacity_percentage": capacity_percentage,
        "status": traffic_status,
        "status_class": status_class,
        "total_system_vehicles_last_hour": total_system_vehicles_last_hour
    }

    return jsonify({"success": True, "data": response_data}), 200

  except Exception as e:
    print(f"Error in camera-metrics: {e}")
    return jsonify({"success": False, "message": str(e)}), 500
