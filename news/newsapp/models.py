from django.contrib.auth.models import AbstractUser
from django.db import models  # SQLite for authentication
from djongo import models as djongo_models  # MongoDB for news storage
from djongo.models import Manager
class News(djongo_models.Model):
    article_id = djongo_models.CharField(max_length=100, primary_key=True)
    title = djongo_models.CharField(max_length=500)
    content = djongo_models.TextField()
    source = djongo_models.CharField(max_length=200, default="Unknown")
    category = djongo_models.CharField(max_length=100, default="General")
    sentiment = djongo_models.CharField(max_length=20, choices=[
        ('Positive', 'Positive'),
        ('Negative', 'Negative'),
        ('Neutral', 'Neutral')
    ])
    timestamp = djongo_models.DateTimeField(auto_now_add=True)
    last_updated = djongo_models.DateTimeField(auto_now_add=True, blank=True, null=True)  
    url = djongo_models.CharField(max_length=500, blank=True, null=True)
    image_url = djongo_models.CharField(max_length=500, blank=True, null=True) 

    class Meta:
        db_table = "articles"  # Make sure this matches your MongoDB collection name
        managed = False  # Ensures Django doesn't try to migrate this table
        ordering = ['-last_updated']

# ✅ SQLite Model for Authentication
class User(AbstractUser):
    department = models.CharField(max_length=255, blank=True, null=True)
    login_id = models.CharField(max_length=100, unique=True)  # Custom Login ID field
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=[('admin', 'Admin'), ('user', 'User')])

    REQUIRED_FIELDS = ['email', 'login_id']  # Ensure login_id is required

    def _str_(self):
        return self.username