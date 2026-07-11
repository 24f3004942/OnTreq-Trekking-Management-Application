import os
from flask import Flask
from flask_cors import CORS
from models import db, User, StaffProfile

def create_app():
    app = Flask(__name__)
    
    # Allow frontend to communicate with backend
    CORS(app)
    
    # Configure SQLite Database (MAD-2 requirement)
    basedir = os.path.abspath(os.path.dirname(__file__))
    # This places the database file in the 'instance' folder at the root
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, '..', 'instance', 'database.sqlite')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    # Initialize the app with the database
    db.init_app(app)
    
    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)