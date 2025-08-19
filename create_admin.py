from app import app, db
from models import User
from werkzeug.security import generate_password_hash

admin_data = {
    "full_name": "Admin User",
    "email": "carleytrump7@gmail.com",
    "phone_number": "1111111112",
    "password": "Admin123c",
    "role": "admin"
}

with app.app_context():
    # Check if user already exists by email or phone
    user = User.query.filter(
        (User.email == admin_data["email"]) | 
        (User.phone_number == admin_data["phone_number"])
    ).first()

    if user:
        print(f"User with email {admin_data['email']} or phone {admin_data['phone_number']} already exists.")
        # Optionally update info
        user.full_name = admin_data["full_name"]
        user.role = admin_data["role"]
        user.password_hash = generate_password_hash(admin_data["password"])
        db.session.add(user)
        db.session.commit()
        print("Existing user updated.")
    else:
        # Create new admin
        new_admin = User(
            full_name=admin_data["full_name"],
            email=admin_data["email"],
            phone_number=admin_data["phone_number"],
            role=admin_data["role"]
        )
        new_admin.password_hash = generate_password_hash(admin_data["password"])
        db.session.add(new_admin)
        db.session.commit()
        print(f"Admin {admin_data['full_name']} created successfully.")
