import os
from app import create_app
from models import db, User
from werkzeug.security import generate_password_hash

app = create_app()

def setup_database():
    with app.app_context():
        # PERMANENT FIX: Ensure the 'instance' directory exists before creating the DB
        instance_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), '..', 'instance')
        os.makedirs(instance_path, exist_ok=True)

        # Create all tables
        db.create_all()
        print("Database tables created successfully.")

        # Check if admin already exists
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            # Create the default admin user
            hashed_password = generate_password_hash('ontreq4942')
            new_admin = User(
                email='admin@ontreq.com',
                password_hash=hashed_password,
                role='admin'
            )
            db.session.add(new_admin)
            db.session.commit()
            print("Default Admin user created successfully. (Email: admin@ontreq.com | Password: ontreq4942)")
        else:
            print("Admin user already exists.")

if __name__ == '__main__':
    setup_database()