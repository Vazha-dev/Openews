from flask import Flask
from extensions import db, login_manager
from models import User
from admin import admin_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'opennews-secret-key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///opennews.db'
app.register_blueprint(admin_bp)
db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

with app.app_context():
    db.create_all()

from translations import t, tc
app.jinja_env.globals.update(t=t, tc=tc)

from routes import *  # ბოლოში!

# Auto-refresh — ყოველ 2 საათში ახალი სიახლეები
from apscheduler.schedulers.background import BackgroundScheduler
from seed_news import fetch_and_seed

def auto_refresh():
    with app.app_context():
        fetch_and_seed()

scheduler = BackgroundScheduler()
scheduler.add_job(auto_refresh, 'interval', hours=2)
scheduler.start()

if __name__ == '__main__':
    app.run(debug=True)