from datetime import datetime
from ..extensions import db


class Warehouse(db.Model):
    __tablename__ = 'warehouse'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), unique=True, nullable=False)
    type = db.Column(db.Enum('main', 'employee'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Warehouse {self.name}>'
