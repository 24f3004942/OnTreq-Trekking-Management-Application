import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from models import db, cache, User, StaffProfile, Trek, Booking, TrekReview
from celery import Celery
from flask import send_from_directory

def create_app():
    # 1. Point Flask to the external 'frontend' folder
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
    
    # 2. Initialize Flask with the static folder configurations
    app = Flask(__name__, static_folder=frontend_dir, static_url_path='/')
    
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

    # --- NEW: REDIS CACHING CONFIGURATION ---
    app.config['CACHE_TYPE'] = 'RedisCache'
    app.config['CACHE_REDIS_URL'] = 'redis://localhost:6379/0'
    app.config['CACHE_DEFAULT_TIMEOUT'] = 300 # Default cache lives for 5 minutes
    # Fail-soft: if Redis is briefly unreachable, serve the request live
    # instead of returning a 500 from inside the caching decorator.
    app.config['CACHE_IGNORE_ERRORS'] = True
    cache.init_app(app)

    # --- NEW: CELERY CONFIGURATION ---
    # Tell Celery to use your local Redis server as the message broker
    # --- UI SERVING ROUTES (MAD-2 Evaluator Setup) ---
    @app.route('/')
    def serve_index():
        """Serves the public landing page as the app's entry point"""
        return send_from_directory(app.static_folder, 'landing.html')

    @app.route('/<path:path>')
    def serve_static_files(path):
        """Serves CSS, JS, and HTML files from the frontend folder"""
        if os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        else:
            # Fallback for unknown paths
            return send_from_directory(app.static_folder, 'landing.html')
            
    # ... your existing blueprint registrations stay below this ...
    
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

    from routes.public import public_bp
    app.register_blueprint(public_bp, url_prefix='/api/public')
    
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

import jobs.tasks

if __name__ == '__main__':
    app.run(debug=True, port=5000)
    
    