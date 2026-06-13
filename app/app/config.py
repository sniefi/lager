import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'mysql+pymysql://lager:lagerpassword@localhost:3306/lager'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    REMEMBER_COOKIE_DURATION = 60 * 60 * 24 * 30  # 30 Tage
    APP_PASSWORD_HASH = os.environ.get('APP_PASSWORD_HASH', '')
    WOO_URL = os.environ.get('WOO_URL', '')
    WOO_CONSUMER_KEY = os.environ.get('WOO_CONSUMER_KEY', '')
    WOO_CONSUMER_SECRET = os.environ.get('WOO_CONSUMER_SECRET', '')
