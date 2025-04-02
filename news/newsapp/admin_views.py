from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.models import User
from django.views.decorators.csrf import csrf_exempt
from pymongo import MongoClient
from django.contrib import messages
import json
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io
from django.utils.timezone import make_aware
from datetime import datetime
import math
from .models import News
from django.contrib.auth.decorators import login_required

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
def export_pdf(request):
    if 'user_id' not in request.session:
        return redirect('login')
    
    # Check if user has admin role
    if request.session.get('role') != 'admin':
        messages.error(request, 'You do not have admin privileges')
        return redirect('dashboard')
    
    # Get channels data with sentiment counts
    pipeline = [
        {"$group": {
            "_id": "$source",
            "positive": {"$sum": {"$cond": [{"$eq": ["$sentiment", "Positive"]}, 1, 0]}},
            "negative": {"$sum": {"$cond": [{"$eq": ["$sentiment", "Negative"]}, 1, 0]}},
            "neutral": {"$sum": {"$cond": [{"$eq": ["$sentiment", "Neutral"]}, 1, 0]}},
            "total": {"$sum": 1}
        }}
    ]
    
    channels_data = list(news_collection.aggregate(pipeline))
    
    # Create PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []
    
    # Add title
    styles = getSampleStyleSheet()
    title = Paragraph("News Sentiment Analysis Report", styles['Heading1'])
    elements.append(title)
    elements.append(Spacer(1, 12))
    
    # Add date
    date_text = Paragraph(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal'])
    elements.append(date_text)
    elements.append(Spacer(1, 24))
    
    # Add overall summary
    positive_count = sum(channel["positive"] for channel in channels_data)
    negative_count = sum(channel["negative"] for channel in channels_data)
    neutral_count = sum(channel["neutral"] for channel in channels_data)
    total_count = sum(channel["total"] for channel in channels_data)
    
    summary_text = Paragraph("Overall Sentiment Summary:", styles['Heading2'])
    elements.append(summary_text)
    elements.append(Spacer(1, 12))
    
    overall_data = [
        ["Total Articles", "Positive", "Negative", "Neutral"],
        [str(total_count), 
         f"{positive_count} ({round((positive_count/total_count)*100) if total_count > 0 else 0}%)", 
         f"{negative_count} ({round((negative_count/total_count)*100) if total_count > 0 else 0}%)", 
         f"{neutral_count} ({round((neutral_count/total_count)*100) if total_count > 0 else 0}%)"]
    ]
    
    overall_table = Table(overall_data, colWidths=[120, 120, 120, 120])
    overall_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, 1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(overall_table)
    elements.append(Spacer(1, 24))
    
    # Add channel-wise breakdown
    channel_text = Paragraph("Channel-wise Sentiment Breakdown:", styles['Heading2'])
    elements.append(channel_text)
    elements.append(Spacer(1, 12))
    
    # Prepare data for table
    channel_table_data = [["Channel", "Total", "Positive", "Negative", "Neutral"]]
    
    for channel in channels_data:
        channel_name = channel["_id"] if channel["_id"] else "Unknown"
        total = channel["total"]
        positive = channel["positive"]
        negative = channel["negative"]
        neutral = channel["neutral"]
        
        pos_pct = round((positive/total)*100) if total > 0 else 0
        neg_pct = round((negative/total)*100) if total > 0 else 0
        neu_pct = round((neutral/total)*100) if total > 0 else 0
        
        channel_table_data.append([
            channel_name,
            str(total),
            f"{positive} ({pos_pct}%)",
            f"{negative} ({neg_pct}%)",
            f"{neutral} ({neu_pct}%)"
        ])
    
    channel_table = Table(channel_table_data, colWidths=[100, 80, 100, 100, 100])
    channel_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.beige, colors.white])
    ]))
    
    elements.append(channel_table)
    
    # Build PDF
    doc.build(elements)
    
    # Return PDF as response
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="news_sentiment_report.pdf"'
    
    return response

# Admin News Management View

def admin_news(request):
    if 'user_id' not in request.session:
        return redirect('login')
    if request.session.get('role') != 'admin':
        messages.error(request, 'You do not have admin privileges')
        return redirect('dashboard')
    
    departments = [
        'Ministry of Home Affairs', 'Ministry of Finance', 'Ministry of Social Justice and Empowerment',
        'Ministry of Culture', 'Ministry of Health and Family Welfare', 'Ministry of Information and Broadcasting',
        'Ministry of Education', 'Ministry of Environment, Forest and Climate Change', 'Ministry of Science and Technology',
        'Ministry of Tourism', 'Ministry of External Affairs', 'Ministry of Women and Child Development',
        'Ministry of Youth Affairs and Sports'
    ]
    
    return render(request, 'admin_news.html', {'is_admin': True, 'departments': departments})

# Admin User Management View

def admin_users(request):
    if 'user_id' not in request.session:
        return redirect('login')
    
    # Check if user has admin role
    if request.session.get('role') != 'admin':
        messages.error(request, 'You do not have admin privileges')
        return redirect('dashboard')
        
    # Use MongoDB collection instead of Django User model
    users = list(db["users"].find())
    
    context = {
        'users': users,
        'is_admin': True,
    }
    return render(request, 'admin_users.html', context)

# API for user management
@csrf_exempt
@login_required  # Allow only logged-in users
def user_api(request):
    if request.method == 'GET':
        users = list(db["users"].find({}, {"_id": 0, "id": 1, "username": 1, "email": 1, "is_staff": 1, "is_active": 1}))
        print("Fetched Users:", users)  # Debugging Line
        return JsonResponse({'success': True, 'users': users})
                
    elif request.method == 'POST':
        data = json.loads(request.body)
        # Create a new user
        try:
            user = User.objects.create_user(
                username=data['username'],
                email=data['email'],
                password=data['password'],
                is_staff=data.get('is_staff', False)
            )
            return JsonResponse({'success': True, 'id': user.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    elif request.method == 'PUT':
        data = json.loads(request.body)
        try:
            user = User.objects.get(id=data['id'])
            user.username = data.get('username', user.username)
            user.email = data.get('email', user.email)
            user.is_staff = data.get('is_staff', user.is_staff)
            
            if 'password' in data and data['password']:
                user.set_password(data['password'])
                
            user.save()
            return JsonResponse({'success': True})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})
    
    elif request.method == 'DELETE':
        data = json.loads(request.body)
        try:
            user = User.objects.get(id=data['id'])
            user.delete()
            return JsonResponse({'success': True})
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'User not found'})

def news_get_view(request):
    print("DEBUG: Entering news_get_view")
    print("DEBUG: GET Parameters:", request.GET)

    # Collect filter parameters
    search = request.GET.get('search', '').strip()
    date = request.GET.get('date', '').strip()
    sentiment = request.GET.get('sentiment', '').strip()
    department = request.GET.get('department', '').strip()
    page = int(request.GET.get('page', 1))

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
        query['department'] = department.strip()  # Exact match, no regex

    per_page = 9
    skip = (page - 1) * per_page

    print("DEBUG: Constructed Query:", query)  # Debugging log

    try:
        total_news = news_collection.count_documents(query)
        total_pages = math.ceil(total_news / per_page)
        news = list(news_collection.find(query).skip(skip).limit(per_page))

        print(f"DEBUG: Total News: {total_news}, Total Pages: {total_pages}")

        # Convert MongoDB documents to JSON serializable format
        news_list = []
        for article in news:
            article['_id'] = str(article['_id'])  # Convert ObjectId to string
            news_list.append(article)

        return JsonResponse({'news': news_list, 'total_pages': total_pages})

    except Exception as e:
        print(f"ERROR in news_get_view: {str(e)}")
        return JsonResponse({'error': 'Internal Server Error'}, status=500)

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