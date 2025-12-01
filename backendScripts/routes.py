from flask import Blueprint, request, jsonify
import token_routes

api_routes_bp = Blueprint("api_routes_bp", __name__)

LATEST_TOKEN = None

@api_routes_bp.route("/register-rn-token", methods=["POST"])
def register_token_endpoint():
    data = request.get_json() or {}

    token = data.get("token")

    if not token:
        return jsonify({"error": "token is required"}), 400

    global LATEST_TOKEN

    LATEST_TOKEN = token
    print(LATEST_TOKEN)

    return jsonify({"status": "ok"})

latest_from_1 = None
latest_from_2 = None

@api_routes_bp.route("/decision", methods=["POST"])
def decision_endpoint():
    data = request.get_json() or {}
    result = data.get("result")
    confidence = data.get("confidence")
    from_id = data.get("fromId")

    if not result:
        return jsonify({"error": "result is required"}), 400

    if not confidence:
        return jsonify({"error": "confidence is required"}), 400

    if not from_id:
        return jsonify({"error": "fromId is required"}), 400

    if from_id not in (1, 2):
        return jsonify({"error": "fromId must be 1 or 2"}), 400

    global latest_from_1, latest_from_2

    if from_id == 1:
        latest_from_1 = {
            "result": result,
            "confidence": confidence
        }
    else:
        latest_from_2 = {
            "result": result,
            "confidence": confidence
        }
    
    if (latest_from_1 is not None) and (latest_from_2 is not None):
        final_result = latest_from_1["result"] if latest_from_1["confidence"] > latest_from_2["confidence"] else latest_from_2["result"]
        final_confidence = latest_from_1["confidence"] if latest_from_1["confidence"] > latest_from_2["confidence"] else latest_from_2["confidence"]

        if final_result == "distracted":
            send_push_notification(LATEST_TOKEN, "Stay Focused", "It seems you're getting distracted. Let's refocus!")

        latest_from_1 = None
        latest_from_2 = None

    return jsonify({"status": "ok"})

import requests

EXPO_PUSH_URL = "https://exp.host/--/api/v2/push/send"

def send_push_notification(to_token: str, title: str, body: str, data: dict | None = None):
    payload = {
        "to": to_token,
        "title": title,
        "body": body,
        "sound": "default",
    }

    if data is not None:
        payload["data"] = data

    response = requests.post(EXPO_PUSH_URL, json=payload, timeout=5)

    print("Expo push status code:", response.status_code)
    print("Expo push response body:", response.text)

    return response