from datetime import datetime
from ..extensions import db


class Booking(db.Model):
    __tablename__ = 'booking'

    id = db.Column(db.Integer, primary_key=True)
    booking_type = db.Column(db.Enum('Einkauf', 'Abgang', 'Umlagerung'), nullable=False)
    article_id = db.Column(db.Integer, db.ForeignKey('article.id'), nullable=False)
    quantity = db.Column(db.Numeric(12, 4), nullable=False)
    purchase_price = db.Column(db.Numeric(10, 4), nullable=True)
    source_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=True)
    target_warehouse_id = db.Column(db.Integer, db.ForeignKey('warehouse.id'), nullable=True)
    abgang_destination = db.Column(db.Enum('Eigenbedarf', 'Kunde'), nullable=True)
    customer_name = db.Column(db.String(255), nullable=True)
    is_billed = db.Column(db.SmallInteger, default=0)
    billed_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    source_warehouse = db.relationship('Warehouse', foreign_keys=[source_warehouse_id])
    target_warehouse = db.relationship('Warehouse', foreign_keys=[target_warehouse_id])

    def __repr__(self):
        return f'<Booking {self.booking_type} #{self.id}>'
