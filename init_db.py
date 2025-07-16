import os
from app import create_app, db
from app.models import User

app = create_app()

# Ensure instance directory exists
os.makedirs('instance', exist_ok=True)

with app.app_context():
    # Create all tables
    db.create_all()
    
    # Create admin user if it doesn't exist
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@example.com',
            role='admin'
        )
        admin.set_password('admin123')  # Change this password!
        db.session.add(admin)
        db.session.commit()
        print("Admin user created successfully!")
        print("Username: admin")
        print("Password: admin123")
        print("Please change this password after first login!")
    else:
        print("Admin user already exists.")
    
    print("Database initialized successfully!")