from datetime import datetime
from ..extensions import db


class Article(db.Model):
    __tablename__ = 'article'

    id = db.Column(db.Integer, primary_key=True)
    article_id = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(255), nullable=False)
    unit = db.Column(db.String(32), default='Liter')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    bookings = db.relationship('Booking', backref='article', lazy=True)

    def __repr__(self):
        return f'<Article {self.article_id}: {self.name}>'
