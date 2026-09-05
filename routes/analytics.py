import os
import certifi
from flask import Blueprint, jsonify
from pymongo import MongoClient

alerts_bp = Blueprint('alerts', __name__)

MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://user1:user12326@cluster0.rn7dha5.mongodb.net/?appName=Cluster0")
client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["traffic_system"]

@alerts_bp.route('/api/alerts', methods=['GET'])
def get_all_alerts():
    try:
        # Fetch all blacklisted alerts sorted by newest detection
        alerts_cursor = db["alerted_vehicles"].find(
            {"is_blacklisted": True},
            {"_id": 0}
        ).sort("generated_at", -1)
        
        alerts_list = list(alerts_cursor)
        return jsonify({"success": True, "count": len(alerts_list), "data": alerts_list}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@alerts_bp.route('/api/alerts/<vehicle_id>', methods=['GET'])
def get_alert_detail(vehicle_id):
    try:
        target_id = vehicle_id.upper()
        alert = db["alerted_vehicles"].find_one({"vehicle_id": target_id}, {"_id": 0})
        
        if not alert:
            return jsonify({"success": False, "message": f"No alert found for vehicle: {target_id}"}), 404
            
        return jsonify({"success": True, "data": alert}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
