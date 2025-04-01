import os
import sys
import django
import bcrypt
from pymongo import MongoClient

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'news.settings')
django.setup()

# Connection string from your settings.py
connection_string = "mongodb+srv://amantaphelix:amantaphelix@cluster0.mmmiw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

# Connect to MongoDB
client = MongoClient(connection_string, tls=True)
db = client["news_database"]
users_collection = db["users"]

# Function to hash password
def hash_password(password):
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password

# Function to create an admin user
def create_admin_user():
    admin_data = {  # Use a fixed ID if required (or remove for auto-generated)
        "username": "admin",
        "password": hash_password("admin@123"),
        "login_id": "admin",
        "role": "admin",
        "email": "govmindnews@gmail.com"
    }

    # Check if admin already exists
    existing_admin = users_collection.find_one({"username": "admin"})
    if existing_admin:
        print("Admin user already exists. Skipping creation.")
    else:
        users_collection.insert_one(admin_data)
        print("Admin user created successfully!")

# Run the script
if __name__ == "__main__":
    create_admin_user()
