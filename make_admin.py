from app import app
from extensions import db
from models import User

with app.app_context():
    user = User.query.filter_by(username="vazha").first()

    if user:
        user.role = "admin"
        db.session.commit()
        print("User is now admin!")
    else:
        print("User not found!")