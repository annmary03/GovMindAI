from django.contrib.auth.backends import BaseBackend
from pymongo import MongoClient
from django.contrib.auth.hashers import check_password

class MongoDBAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        # Connect to MongoDB
        client = MongoClient("mongodb+srv://amantaphelix:amantaphelix@cluster0.mmmiw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0", tls=True)
        db = client["news_database"]
        users_collection = db["users"]
        
        # Find user in MongoDB
        user_doc = users_collection.find_one({'username': username})
        
        if user_doc and check_password(password, user_doc['password']):
            # You might want to create a custom User object or use a dictionary
            return {
                'id': str(user_doc['_id']),
                'username': user_doc['username'],
                # Add other user attributes as needed
            }
        return None

    def get_user(self, user_id):
        # Implement user retrieval logic
        client = MongoClient("mongodb+srv://amantaphelix:amantaphelix@cluster0.mmmiw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0", tls=True)
        db = client["news_database"]
        users_collection = db["users"]
        
        user_doc = users_collection.find_one({'_id': ObjectId(user_id)})
        
        if user_doc:
            return {
                'id': str(user_doc['_id']),
                'username': user_doc['username'],
                # Add other user attributes
            }
        return None