from flask import Blueprint, request, jsonify
from db import db
from models import Batch, Accelerometer

routes_blueprint = Blueprint("api", __name__)


@routes_blueprint.route("/batches", methods=["POST", "GET"])
def batches():
    if request.method == "POST":
        data = request.get_json() or {}

        batch = Batch(
            name=data.get("name"),
            description=data.get("description"),
        )
        db.session.add(batch)
        db.session.commit()

        return jsonify(batch.to_dict()), 201

    batches = Batch.query.order_by(Batch.id.desc()).all()
    return jsonify([b.to_dict() for b in batches])


@routes_blueprint.route("/accelerometers", methods=["POST", "GET"])
def accelerometers():
    if request.method == "POST":
        data = request.get_json() or {}

        if not all(k in data for k in ("x", "y", "z", "batch_id")):
            return jsonify({"error": "x, y, z, batch_id are required"}), 400

        batch = Batch.query.get(data["batch_id"])
        if batch is None:
            return jsonify({"error": "batch_id does not exist"}), 400

        reading = Accelerometer(
            x=data["x"],
            y=data["y"],
            z=data["z"],
            batch_id=data["batch_id"],
        )
        db.session.add(reading)
        db.session.commit()

        return jsonify(reading.to_dict()), 201

    batch_id = request.args.get("batch_id", type=int)
    limit = request.args.get("limit", default=100, type=int)

    query = Accelerometer.query

    if batch_id is not None:
        query = query.filter_by(batch_id=batch_id)

    readings = query.order_by(Accelerometer.id.desc()).limit(limit).all()

    return jsonify([r.to_dict() for r in readings])
