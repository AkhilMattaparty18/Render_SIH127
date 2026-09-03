from datetime import datetime
import os
import certifi
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient

app = Flask(__name__)
CORS(app)

# MongoDB Atlas Connection
MONGO_URI = os.getenv(
    "MONGO_URI",
    "mongodb+srv://user1:user12326@cluster0.rn7dha5.mongodb.net/?appName=Cluster0&tlsAllowInvalidCertificates=true",
)

client = MongoClient(MONGO_URI, tlsCAFile=certifi.where())
db = client["traffic_system"]

logs_col = db["vehicle_logs"]
cameras_col = db["cameras"]
blacklist_col = db["blacklisted_vehicles"]
alerted_col = db["alerted_vehicles"]


def parse_iso_time(time_str):
    """Parse ISO 8601 timestamps for chronological sorting."""
    return datetime.fromisoformat(time_str.replace("Z", "+00:00"))


def generate_and_store_trail(target_vehicle):
    """Processes raw logs for a queried vehicle, checks blacklist status,
    stores the formatted trail in MongoDB Atlas, and returns the document.
    """
    vehicle_id_upper = target_vehicle.strip().upper()

    # 1. Fetch raw logs for the queried vehicle
    raw_logs = list(
        logs_col.find({"vehicle_id": vehicle_id_upper}, {"_id": 0})
    )

    if not raw_logs:
        return None

    # 2. Cache cameras into a lookup map
    cameras = {
        str(doc["cam_id"]): doc for doc in cameras_col.find({}, {"_id": 0})
    }

    # 3. Check if vehicle is blacklisted
    blacklisted_doc = blacklist_col.find_one(
        {"vehicle_id": vehicle_id_upper}, {"_id": 0}
    )
    is_blacklisted = blacklisted_doc is not None
    blacklist_reason = (
        blacklisted_doc.get("reason", "No reason provided")
        if is_blacklisted
        else None
    )

    # 4. Enrich detection entries with spatial metadata
    trail_points = []
    for entry in raw_logs:
        cam_id = str(entry["cam_id"])
        cam_info = cameras.get(cam_id, {"latitude": None, "longitude": None})

        trail_points.append(
            {
                "cam_id": cam_id,
                "time_stamp": entry["time_stamp"],
                "latitude": cam_info.get("latitude"),
                "longitude": cam_info.get("longitude"),
            }
        )

    # 5. Sort detection points chronologically
    ordered_trail = sorted(
        trail_points, key=lambda x: parse_iso_time(x["time_stamp"])
    )

    # 6. Build full trail document payload
    trail_document = {
        "vehicle_id": vehicle_id_upper,
        "is_blacklisted": is_blacklisted,
        "blacklist_reason": blacklist_reason,
        "total_detections": len(ordered_trail),
        "first_occurrence": ordered_trail[0],
        "last_occurrence": ordered_trail[-1],
        "trail": ordered_trail,
        "generated_at": datetime.now().isoformat(),
    }

    # 7. Store / Update the document directly into MongoDB Atlas
    alerted_col.update_one(
        {"vehicle_id": vehicle_id_upper},
        {"$set": trail_document},
        upsert=True,
    )

    return trail_document


@app.route("/")
def index():
    return jsonify({
        "status": "online",
        "message": "ANPR Vehicle Tracking API is up and running!"
    }), 200


@app.route("/api/track", methods=["GET"])
def track_vehicle_api():
    vehicle_query = request.args.get("vehicle_id", "").strip()

    if not vehicle_query:
        return jsonify(
            {"success": False, "message": "Please enter a Vehicle ID."}
        ), 400

    # Execute search, storage, and retrieval
    trail_data = generate_and_store_trail(target_vehicle=vehicle_query)

    if not trail_data:
        return jsonify(
            {
                "success": False,
                "message": f"No logs found in database for Vehicle ID: '{vehicle_query.upper()}'",
            }
        ), 404

    return jsonify({"success": True, "data": trail_data})


if __name__ == "__main__":
    print("🚀 Script status: Running on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)