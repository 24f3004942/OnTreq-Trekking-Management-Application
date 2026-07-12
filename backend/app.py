import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from models import db, User, StaffProfile, Trek, Booking, TrekReview
from celery import Celery

def create_app():
    app = Flask(__name__)
    CORS(app)
    
    # Configure SQLite Database
    basedir = os.path.abspath(os.path.dirname(__file__))
    instance_path = os.path.join(basedir, '..', 'instance')
    os.makedirs(instance_path, exist_ok=True)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(instance_path, 'database.sqlite')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Configure JWT for Authentication
    app.config['JWT_SECRET_KEY'] = 'ontreq-super-secret-key-4942-secure' # Security key for generating tokens
    from datetime import timedelta
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)
    jwt = JWTManager(app)

    
    
    db.init_app(app)

    # --- NEW: CELERY CONFIGURATION ---
    # Tell Celery to use your local Redis server as the message broker
    
    
    # Register Blueprints
    from routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    
    from routes.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    
    from routes.trek import trek_bp
    app.register_blueprint(trek_bp, url_prefix='/api/treks')
    
    from routes.staff import staff_bp
    app.register_blueprint(staff_bp, url_prefix='/api/staff')
    
    from routes.staff_ops import staff_ops_bp
    app.register_blueprint(staff_ops_bp, url_prefix='/api/staff-ops')
    
    from routes.user_ops import user_ops_bp
    app.register_blueprint(user_ops_bp, url_prefix='/api/user-ops')
    
    return app

from celery.schedules import crontab # <-- NEW IMPORT AT THE TOP OR HERE

# --- CELERY FACTORY ---
# --- CELERY FACTORY ---
def make_celery(app):
    celery = Celery(app.import_name)
    
    # Use modern lowercase keys directly in Celery's config
    celery.conf.update(
        broker_url='redis://localhost:6379/0',
        result_backend='redis://localhost:6379/0',
        timezone='UTC',
        beat_schedule={
            # Task 1: Send Reminders every morning at 8:00 AM
            'daily-trek-reminders': {
                'task': 'jobs.tasks.send_daily_reminders',
                'schedule': crontab(hour=8, minute=0), 
            },
            # Task 2: Generate Admin Report on the 1st of every month at midnight
            'monthly-admin-report': {
                'task': 'jobs.tasks.generate_monthly_report',
                'schedule': crontab(day_of_month='1', hour=0, minute=0), 
            },
            
            # ⚠️ FOR TESTING ONLY: UNCOMMENT THIS TO RUN THE REPORT EVERY 1 MINUTE
             'test-report-every-minute': {
                 'task': 'jobs.tasks.generate_monthly_report',
                 'schedule': crontab(minute='*'), 
             }
        }
    )
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
                
    celery.Task = ContextTask
    return celery

app = create_app()
celery_app = make_celery(app) # Instantiate the Celery app

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    
    