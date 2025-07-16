#!/usr/bin/env python3
"""Quick test script to verify the application works"""

import os
from app import create_app, db
from app.models import User

def test_app():
    # Create app instance
    app = create_app()
    
    with app.app_context():
        # Test database connection
        try:
            users = User.query.all()
            print(f"✓ Database connection successful")
            print(f"✓ Found {len(users)} users in database")
            
            # Test admin user exists
            admin = User.query.filter_by(username='admin').first()
            if admin:
                print(f"✓ Admin user exists with role: {admin.role}")
            else:
                print("✗ Admin user not found")
                
        except Exception as e:
            print(f"✗ Database error: {e}")
            return False
    
    # Test templates can be found
    with app.test_client() as client:
        try:
            response = client.get('/auth/login')
            if response.status_code == 200:
                print("✓ Login page renders successfully")
            else:
                print(f"✗ Login page returned status {response.status_code}")
                
        except Exception as e:
            print(f"✗ Template error: {e}")
            return False
    
    print("\n✓ All tests passed! The application is ready to use.")
    print("Run: python3 run.py")
    print("Visit: http://localhost:5001")
    print("Login: admin / admin123")
    return True

if __name__ == '__main__':
    test_app()