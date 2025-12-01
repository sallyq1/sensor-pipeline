from flask import Blueprint, request, jsonify

decision_bp = Blueprint("decision_bp", __name__)

latest_from_1 = None
latest_from_2 = None

@decision_bp.route("/decision", methods=["POST"])
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
        return jsonify({"error": "from_id is required"}), 400

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
        
        print(f"[DECISION] result={final_result}, confidence={final_confidence}")

    return jsonify({"status": "ok"})
