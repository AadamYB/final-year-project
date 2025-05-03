""" RAN ONCE? """

from app import app
from models import database

with app.app_context():
    database.create_all()
    print("✅ Tables created successfully!")