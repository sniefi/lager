from datetime import datetime
from ..extensions import db


class Inventur(db.Model):
    __tablename__ = 'inventur'

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    positions = db.relationship('InventurPosition', backref='inventur', lazy=True)

    def __repr__(self):
        return f'<Inventur #{self.id} {self.created_at}>'


class InventurPosition(db.Model):
    __tablename__ = 'inventur_position'

    id = db.Column(db.Integer, primary_key=True)
    inventur_id = db.Column(db.Integer, db.ForeignKey('inventur.id'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=False)
    quantity_before = db.Column(db.Numeric(12, 4), nullable=False)
    quantity_after = db.Column(db.Numeric(12, 4), nullable=False)
    difference = db.Column(db.Numeric(12, 4), nullable=False)

    article = db.relationship('Article')
    warehouse = db.relationship('Warehouse')
