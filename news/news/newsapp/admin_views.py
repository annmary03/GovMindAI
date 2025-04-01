from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.csrf import csrf_protect
from pymongo import MongoClient
from django.contrib import messages
import json
from collections import defaultdict
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
from datetime import datetime
import math
from bson import ObjectId
import bcrypt
from django.middleware.csrf import get_token
import logging
from django.contrib.auth import get_user_model
logger = logging.getLogger(__name__)
User = get_user_model() 
from .models import News
from bson.binary import Binary
import base64


client = MongoClient("mongodb+srv://amantaphelix:amantaphelix@cluster0.mmmiw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0", tls=True)
db = client["news_database"]
news_collection = db["articles"]
sample_doc = news_collection.find_one()
print("Sample document from database:", sample_doc)  # Match your collection name from models.py
try:
    news_collection.find_one()
    print("Database connection successful")
except Exception as e:
    print(f"Database connection error: {e}")
# Helper function to check if user is admin
def is_admin(user):
    return user.is_authenticated and user.role == 'admin'


def admin_dashboard(request):
    
    print("Session contents:")
    for key, value in request.session.items():
        print(f"{key}: {value}")

    if 'user_id' not in request.session:
        return redirect('login')
    
    # Check if user has admin role
    if request.session.get('role') != 'admin':
        messages.error(request, 'You do not have admin privileges')
        return redirect('dashboard')
    
    # Get sentiment counts from all articles
    positive_count = news_collection.count_documents({"sentiment": "Positive"})
    negative_count = news_collection.count_documents({"sentiment": "Negative"})
    neutral_count = news_collection.count_documents({"sentiment": "Neutral"})

    total_count = positive_count + negative_count + neutral_count

    # Calculate percentages (handle case when total_count is 0)
    if total_count > 0:
        positive_percentage = round((positive_count / total_count) * 100)
        negative_percentage = round((negative_count / total_count) * 100)
        # Ensure the percentages sum to 100% by calculating the last one differently
        neutral_percentage = 100 - positive_percentage - negative_percentage
    else:
        positive_percentage = 0
        negative_percentage = 0
        neutral_percentage = 0
    
    # Get news channels data with sentiment counts
    pipeline = [
        {"$group": {
            "_id": "$source",
            "positive": {"$sum": {"$cond": [{"$eq": ["$sentiment", "Positive"]}, 1, 0]}},
            "negative": {"$sum": {"$cond": [{"$eq": ["$sentiment", "Negative"]}, 1, 0]}},
            "neutral": {"$sum": {"$cond": [{"$eq": ["$sentiment", "Neutral"]}, 1, 0]}},
            "total": {"$sum": 1}
        }}
    ]
    
    news_channels = [
    {
        "channel_name": channel.pop("_id", "Unknown"),  # Rename _id to channel_name
        "positive": channel["positive"],
        "negative": channel["negative"],
        "neutral": channel["neutral"],
        "total": channel["total"]
    }
        for channel in news_collection.aggregate(pipeline)
    ]

    
    # Get total users count
    total_users = db["users"].count_documents({})
    
    # Get recent news
    recent_news = list(news_collection.find().sort("date", -1).limit(5))
    
    # Get dates and daily sentiment counts for the line chart
    date_pipeline = [
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$last_updated"}},
                "count": {"$sum": 1},
                "positive": {"$sum": {"$cond": [{"$eq": ["$sentiment", "Positive"]}, 1, 0]}},
                "negative": {"$sum": {"$cond": [{"$eq": ["$sentiment", "Negative"]}, 1, 0]}},
                "neutral": {"$sum": {"$cond": [{"$eq": ["$sentiment", "Neutral"]}, 1, 0]}}
            }
        },
        {"$sort": {"_id": 1}}
    ]

    # Aggregate data
    daily_counts = list(news_collection.aggregate(date_pipeline))
    # After your aggregation, add this:
    print("Daily counts data:", daily_counts)

# Rename '_id' key before passing it to the template
    for item in daily_counts:
        item["date"] = item.pop("_id")  # Rename _id to date

    
    context = {
        'positive_percentage': positive_percentage,
        'negative_percentage': negative_percentage,
        'neutral_percentage': neutral_percentage,
        'news_channels': news_channels,
        'daily_counts': daily_counts,
        'total_news': total_count,
        'total_users': total_users,
        'recent_news': recent_news,
        'is_admin': True
    }
    print("Context data:", context)

    return render(request, 'admin_dashboard.html', context)

# Export PDF function
def admin_export_pdf(request):
    if 'user_id' not in request.session:
        return redirect('login')
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()
    
    title = Paragraph("News Sentiment Dashboard Report", styles['Heading1'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Fetch all news data (Admin report should contain all users' data)
    all_news = list(news_collection.find({"sentiment": {"$exists": True}}))
    total_count = len(all_news)
    
    if total_count == 0:
        elements.append(Paragraph("No data available.", styles['Normal']))
        doc.build(elements)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="dashboard_report.pdf"'
        response.write(buffer.getvalue())
        buffer.close()
        return response
    
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    
    channels_data = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0, "total": 0})
    
    for news in all_news:
        sentiment = news.get('sentiment', 'neutral').lower()
        channel_name = news.get('source', 'Unknown')
        
        if sentiment == 'positive':
            positive_count += 1
            channels_data[channel_name]["positive"] += 1
        elif sentiment == 'negative':
            negative_count += 1
            channels_data[channel_name]["negative"] += 1
        else:
            neutral_count += 1
            channels_data[channel_name]["neutral"] += 1
        
        channels_data[channel_name]["total"] += 1
    
    positive_percentage = round((positive_count / total_count) * 100, 1) if total_count else 0
    negative_percentage = round((negative_count / total_count) * 100, 1) if total_count else 0
    neutral_percentage = round((neutral_count / total_count) * 100, 1) if total_count else 0
    
    elements.append(Paragraph("Sentiment Overview", styles['Heading2']))
    elements.append(Spacer(1, 12))
    
    data = [["Sentiment", "Count", "Percentage"],
            ["Positive", str(positive_count), f"{positive_percentage}%"],
            ["Negative", str(negative_count), f"{negative_percentage}%"],
            ["Neutral", str(neutral_count), f"{neutral_percentage}%"],
            ["Total", str(total_count), "100%"]]
    
    table = Table(data, colWidths=[200, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 24))
    
    elements.append(Paragraph("News Channels Overview", styles['Heading2']))
    elements.append(Spacer(1, 12))
    
    news_channels = sorted(channels_data.items(), key=lambda x: x[1]["total"], reverse=True)
    
    channel_data = [["Channel", "Total", "Positive", "Negative", "Neutral"]]
    
    for channel, data in news_channels:
        channel_data.append([
            channel,
            str(data["total"]),
            f"{data['positive']} ({round((data['positive'] / data['total'] * 100), 1)}%)" if data["total"] else "0%",
            f"{data['negative']} ({round((data['negative'] / data['total'] * 100), 1)}%)" if data["total"] else "0%",
            f"{data['neutral']} ({round((data['neutral'] / data['total'] * 100), 1)}%)" if data["total"] else "0%"
        ])
    
    channel_table = Table(channel_data, colWidths=[150, 85, 85, 85, 85])
    channel_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(channel_table)
    
    elements.append(Spacer(1, 36))
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elements.append(Paragraph(f"Report generated on: {report_date}", styles['Normal']))
    
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="dashboard_report.pdf"'
    response.write(pdf)
    
    return response


def admin_news(request):
    if 'user_id' not in request.session:
        return redirect('login')
    
    # Check if user has admin role
    if request.session.get('role') != 'admin':
        messages.error(request, 'You do not have admin privileges')
        return redirect('dashboard')
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
    context = {
        'is_admin': True,
        'departments': departments,
    }
    return render(request, 'admin_news.html', context)

# Admin User Management View

def admin_users(request):
    if 'user_id' not in request.session:
        return redirect('login')
    
    # Check if user has admin role
    if request.session.get('role') != 'admin':
        messages.error(request, 'You do not have admin privileges')
        return redirect('dashboard')
        
    # Use MongoDB collection instead of Django User model
    users = list(db["users"].find({"username": {"$ne": "admin"}}, 
                                  {"_id": 1, "username": 1, "email": 1, "department": 1}))
    
    # Convert ObjectId to string for rendering
    for user in users:
        user["_id"] = str(user["_id"])  

    context = {
        'users': users,
        'is_admin': True,
    }
    return render(request, 'admin_users.html', context)

# API for user management


from django.views.decorators.http import require_http_methods
from django.http import JsonResponse
import json
from bson import ObjectId
from django.views.decorators.csrf import csrf_exempt

@csrf_exempt  # Temporarily add this for debugging
@require_http_methods(["GET", "POST", "PUT", "DELETE"])
def user_api(request):
        if request.method == 'GET':
            # Get users from MongoDB
            users = list(db["users"].find({}, {"_id": 1, "username": 1, "email": 1, "department": 1}))
            
            # Convert ObjectId to string
            user_list = []
            for user in users:
                user['id'] = str(user['_id'])
                del user['_id']
                user_list.append(user)
            
            return JsonResponse({"users": user_list}, safe=False)
            
        elif request.method in ['POST', 'PUT']:
            try:
                data = json.loads(request.body)
                
                # Common validation
                if not data.get('username') or not data.get('email'):
                    return JsonResponse({"error": "Username and email are required"}, status=400)

                if request.method == 'POST':
                    # CREATE NEW USER
                    if not data.get('password'):
                        return JsonResponse({"error": "Password is required for new users"}, status=400)
                    
                    # Check for existing user
                    if db["users"].find_one({"$or": [{"username": data['username']}, {"email": data['email']}]}):
                        return JsonResponse({"error": "Username or email already exists"}, status=400)
                    
                    # Insert new user
                    user_data = {
                        "username": data['username'],
                        "email": data['email'],
                        "password": hash_password(data['password']),
                        "department": data.get('department', ''),
                        "created_at": datetime.now()
                    }
                    result = db["users"].insert_one(user_data)
                    return JsonResponse({
                        "success": True,
                        "message": "User created successfully",
                        "user_id": str(result.inserted_id)
                    })
                
                else:  # PUT - UPDATE USER
                    if not data.get('id'):
                        return JsonResponse({"error": "User ID is required for updates"}, status=400)
                
                # Prepare update - only include provided fields
                    update_data = {
                        "username": data['username'],
                        "email": data['email']
                    }
                    if 'department' in data:
                        update_data['department'] = data['department']
                    if 'password' in data:
                        update_data['password'] = hash_password(data['password'])
                    
                    # Perform update
                    result = db["users"].update_one(
                        {"_id": ObjectId(data['id'])},
                        {"$set": update_data}
                    )
                    
                    if result.matched_count == 0:
                        return JsonResponse({"error": "User not found"}, status=404)
                    
                    return JsonResponse({
                        "success": True,
                        "message": "User updated successfully"
                    })
                
            except Exception as e:
                logger.error(f"Error in user_api: {str(e)}")
                return JsonResponse({"error": str(e)}, status=500)
    
            
        return JsonResponse({"error": "Method not allowed"}, status=405)
def hash_password(password):
    """Hash password using bcrypt"""
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(pwd_bytes, salt)
    return hashed_password.decode('utf-8')

@csrf_protect
def save_user(request):
    if request.method in ["POST", "PUT"]:
        try:
            # Print raw request body for debugging
            print("Request body:", request.body)
            
            # Try parsing JSON with different methods
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                data = json.loads(request.body.decode('utf-8'))
            
            # Log parsed data for debugging
            print("Parsed data:", data)

            user_id = data.get('id')
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')
            department = data.get('department', '')
            is_staff = data.get('is_staff', False)
            role = "user"
            login_id = username

            if not username or not email:
                return JsonResponse({"error": "Username and Email are required"}, status=400)

            # Use MongoDB for user management
            users_collection = db["users"]

            if user_id:  # Update existing user
                update_data = {
                    "username": username,
                    "email": email,
                    "department": department,
                    "is_staff": is_staff,
                    "role": role,
                    "login_id": login_id
                }
                
                # Only update password if a new one is provided
                if password:
                    update_data["password"] = hash_password(password)
                
                result = users_collection.update_one(
                    {"_id": ObjectId(user_id)}, 
                    {"$set": update_data}
                )
                
                if result.modified_count == 0:
                    return JsonResponse({'success': False, 'error': 'User not found or no changes made'}, status=404)

            else:  # Create new user
                if not password:
                    return JsonResponse({'success': False, 'error': 'Password is required for new users'}, status=400)
                
                new_user = {
                    "username": username,
                    "email": email,
                    "password": hash_password(password),
                    "role": role,
                    "login_id": login_id,
                    "department": department,
                    "is_staff": is_staff
                }
                
                result = users_collection.insert_one(new_user)
                user_id = str(result.inserted_id)
                print("Inserted user ID:", result.inserted_id)


            return JsonResponse({
                'success': True, 
                'message': 'User saved successfully', 
                'user_id': user_id
            })

        except Exception as e:
            print(f"Error saving user: {e}")
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)
def get_csrf_token(request):
    return JsonResponse({'csrfToken': get_token(request)})


    

def news_get_view(request):
    # Extensive logging
    print("DEBUG: Entering news_get_view")
    
    # Log all GET parameters
    print("DEBUG: GET Parameters:")
    for key, value in request.GET.items():
        print(f"{key}: {value}")
    
    # Collect filter parameters
    search = request.GET.get('search', '')
    date = request.GET.get('date', '')
    sentiment = request.GET.get('sentiment', '')
    department = request.GET.get('department', '')
    page = int(request.GET.get('page', 1))
    
    # Detailed filter logging
    print(f"DEBUG: Filters - Search: '{search}', Date: '{date}', Sentiment: '{sentiment}', Department: '{department}', Page: {page}")
    
    # Construct query
    query = {}
    if search:
        query['$or'] = [
            {'title': {'$regex': search, '$options': 'i'}},
            {'content': {'$regex': search, '$options': 'i'}}
        ]
    if date:
        query['published_date'] = date
    if sentiment:
        query['sentiment'] = sentiment
    if department:
        query['department'] = department
    
    # Pagination
    per_page = 9  # Matches grid layout
    skip = (page - 1) * per_page
    
    # Log the constructed query
    print("DEBUG: Constructed Query:", query)
    
    # Fetch news
    try:
        total_news = news_collection.count_documents(query)
        total_pages = math.ceil(total_news / per_page)
        news = list(news_collection.find(query).skip(skip).limit(per_page))
        print(news)
        print(f"DEBUG: Total News: {total_news}, Total Pages: {total_pages}")
        
        # Convert MongoDB documents to JSON serializable format
        news_list = []
        for article in news:
            # Ensure all required fields exist
            article['_id'] = str(article['_id'])  # Convert ObjectId to string
            
            # Add logging for each article
            print(f"DEBUG: Article Found - ID: {article['_id']}, Title: {article.get('title', 'No Title')}")
            
            news_list.append(article)
        
        print(f"DEBUG: Processed {len(news_list)} news articles")
        
        # Detailed response logging
        response_data = {
            'news': news_list,
            'total_pages': total_pages
        }
        print("DEBUG: Response Data:", json.dumps(response_data, indent=2))
        
        return JsonResponse(response_data)
    
    except Exception as e:
        # Comprehensive error logging
        print(f"ERROR in news_get_view: {str(e)}")
        print(f"Error Type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        
    return JsonResponse({
        'news': news_list if news_list else [],  # Ensure it's always an array
        'total_pages': total_pages
    })


@csrf_exempt
def updateNews(request, article_id):
    if request.method == 'PUT':
        try:
            news_article = News.objects.get(article_id=article_id)

            # Parse JSON data
            data = json.loads(request.body)

            # Update fields safely
            news_article.title = data.get('title', news_article.title)
            news_article.content = data.get('content', news_article.content)
            news_article.source = data.get('source', news_article.source)
            news_article.sentiment = data.get('sentiment', news_article.sentiment)

            # Handle last_updated
            last_updated_str = data.get('last_updated')
            if last_updated_str:
                try:
                    naive_datetime = datetime.strptime(last_updated_str, "%Y-%m-%dT%H:%M:%S.%fZ")
                    news_article.last_updated = make_aware(naive_datetime)  # Converts to timezone-aware
                except ValueError:
                    return JsonResponse({'error': 'Invalid date format. Use ISO 8601 (YYYY-MM-DDTHH:MM:SS.sssZ)'}, status=400)

            news_article.save()
            return JsonResponse({'message': 'News updated successfully!'}, status=200)
        except News.DoesNotExist:
            return JsonResponse({'error': 'News article not found'}, status=404)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)

@csrf_exempt
def deleteNews(request, article_id):
    if request.method == 'DELETE':
        try:
            news_article = News.objects.get(article_id=article_id)
            news_article.delete()
            return JsonResponse({'message': 'News deleted successfully'}, status=200)
        except News.DoesNotExist:
            return JsonResponse({'error': 'News article not found'}, status=404)
    else:
        return JsonResponse({'error': 'Invalid request method'}, status=405)
    
def verify_password(stored_password, input_password):
    """
    Verify password against both storage formats:
    - Binary.createFromBase64 (manual entries)
    - Raw bcrypt hash (create_users.py)
    """
    # Handle Base64 Binary format
    if isinstance(stored_password, Binary):
        try:
            # Decode from Base64 Binary
            decoded_hash = base64.b64decode(stored_password)
            return bcrypt.checkpw(input_password.encode('utf-8'), decoded_hash)
        except:
            pass
    
    # Handle raw bcrypt hash (from create_users.py)
    try:
        if isinstance(stored_password, bytes):
            return bcrypt.checkpw(input_password.encode('utf-8'), stored_password)
        elif isinstance(stored_password, str):
            return bcrypt.checkpw(input_password.encode('utf-8'), stored_password.encode('utf-8'))
    except:
        pass
    
    return False
