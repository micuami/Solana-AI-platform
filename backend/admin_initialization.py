from werkzeug.security import generate_password_hash
from backend.models import User
from backend.externals import db

def create_admin_user():
    admin_user = User.query.filter_by(email='admin@admin.com').first()
    
    if not admin_user:
        admin_user = User(
            username='admin',
            email='admin@admin.com',
            password=generate_password_hash('admin'),
            is_admin=True
        )
        
        try:
            admin_user.save()
            print("Admin user created successfully")
        except Exception as e:
            print(f"Error creating admin user: {e}")
            db.session.rollback()
    else:
        if not admin_user.is_admin:
            admin_user.is_admin = True
            try:
                db.session.commit()
            except Exception as e:
                print(f"Error updating admin user: {e}")
                db.session.rollback()
        else:
            print("Admin user already exists and is properly configured")

def ensure_admin_exists():
    try:
        create_admin_user()
    except Exception as e:
        print(f"Error during admin user initialization: {e}")