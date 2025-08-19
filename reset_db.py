# reset_db.py
from app import app
from models import db

with app.app_context():
    # Drop all tables (WARNING: deletes all existing data)
    db.drop_all()
    print("All tables dropped.")

    # Create all tables according to your current models.py
    db.create_all()
    print("All tables recreated with current schema.")
