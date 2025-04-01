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

# Departments with their names
departments = [
    'Ministry of Home Affairs',
    'Ministry of Finance',
    'Ministry of Social Justice and Empowerment',
    'Ministry of Culture',
    'Ministry of Health and Family Welfare',
    'Ministry of Information and Broadcasting',
    'Ministry of Education',
    'Ministry of Environment, Forest and Climate Change',
    'Ministry of Science and Technology',
    'Ministry of Tourism',
    'Ministry of External Affairs',
    'Ministry of Women and Child Development',
    'Ministry of Youth Affairs and Sports'
]

# Function to create a login ID from department name
def create_login_id(department):
    # Remove 'Ministry of' and convert to lowercase
    login_id = department.replace('Ministry of ', '').replace(' ', '_').lower()
    return f"{login_id}_user"

# Create users for departments
def create_department_users():
    users = []
    for department in departments:
        # Create login ID
        login_id = create_login_id(department)
        
        # Create a simple password (in production, use a more secure method)
        password = f"{login_id}_pass123"
        
        user = {
            "username": login_id,
            "password": hash_password(password),
            "login_id": login_id,
            "role": "user",
            "department": department,
            "email": f"{login_id}@government.in"
        }
        users.append(user)
    
    # Insert users
    if users_collection.count_documents({}) > 0:
        print("Users already exist in the database. Skipping insertion.")
        return
    
    result = users_collection.insert_many(users)
    print("Inserted user IDs:", result.inserted_ids)
    
    # Print login credentials
    print("\nLogin Credentials:")
    for user in users:
        print(f"Department: {user['department']}")
        print(f"Login ID: {user['login_id']}")
        print(f"Password: {user['login_id']}_pass123\n")

# Run the script
if __name__ == "__main__":
    create_department_users()