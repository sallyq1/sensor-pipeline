from datetime import datetime
from db import db

class Batch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=True)
    description = db.Column(db.String, nullable=True)
    created_at = db.Column(
        db.String,
        nullable=False,
        default=lambda: datetime.utcnow().isoformat(),
    )

    readings = db.relationship("Accelerometer", backref="batch", lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
        }


class Accelerometer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    x = db.Column(db.Float, nullable=False)
    y = db.Column(db.Float, nullable=False)
    z = db.Column(db.Float, nullable=False)
    created_at = db.Column(
        db.String,
        nullable=False,
        default=lambda: datetime.utcnow().isoformat(),
    )
    batch_id = db.Column(
        db.Integer,
        db.ForeignKey("batch.id"),
        nullable=False,
    )

    def to_dict(self):
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "z": self.z,
            "batch_id": self.batch_id,
            "created_at": self.created_at,
        }
