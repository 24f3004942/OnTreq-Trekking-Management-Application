import os
from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from models import db, User, StaffProfile, Trek, Booking, TrekReview

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
    app.config['JWT_SECRET_KEY'] = 'ontreq-super-secret-key-4942' # Security key for generating tokens
    from datetime import timedelta
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=1)
    jwt = JWTManager(app)

    
    
    db.init_app(app)
    
    # Register Blueprints
    from routes.auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/api/auth')

    from routes.admin import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/api/admin')

    from routes.trek import trek_bp
    app.register_blueprint(trek_bp, url_prefix='/api/treks')

    # Add this new Staff Blueprint
    from routes.staff import staff_bp
    app.register_blueprint(staff_bp, url_prefix='/api/staff')
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)