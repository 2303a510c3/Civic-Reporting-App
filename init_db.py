#!/usr/bin/env python3
"""
Database initialization script for Civic Reporting App
Run this script to create the database and initial admin user
"""

import os
import sys
from app import app, db, User
from werkzeug.security import generate_password_hash

def init_database():
    """Initialize the database with tables and admin user"""
    
    with app.app_context():
        try:
            # Create all tables
            print("Creating database tables...")
            db.create_all()
            print("✓ Database tables created successfully")
            
            # Check if admin user exists
            admin = User.query.filter_by(username='admin').first()
            if not admin:
                # Create admin user
                admin = User(
                    username='admin',
                    password_hash=generate_password_hash('admin123'),
                    role='admin'
                )
                db.session.add(admin)
                db.session.commit()
                print("✓ Admin user created successfully")
                print("  Username: admin")
                print("  Password: admin123")
            else:
                print("✓ Admin user already exists")
            
            print("\n" + "="*50)
            print("Database initialization completed successfully!")
            print("="*50)
            print("\nNext steps:")
            print("1. Start the Flask application: python app.py")
            print("2. Open your browser to: http://localhost:5000")
            print("3. Login with admin credentials to access the dashboard")
            print("\nFor public users:")
            print("- Visit http://localhost:5000 to report issues")
            print("- No login required for issue submission")
            
        except Exception as e:
            print(f"❌ Error initializing database: {e}")
            print("\nTroubleshooting:")
            print("1. Make sure MySQL server is running")
            print("2. Check database connection settings in app.py")
            print("3. Ensure the 'civic_reporting' database exists")
            print("4. Verify MySQL credentials are correct")
            sys.exit(1)

if __name__ == '__main__':
    print("Civic Reporting App - Database Initialization")
    print("=" * 50)
    init_database()
