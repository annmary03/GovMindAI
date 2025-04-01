from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.decorators import login_required 
from django.core.paginator import Paginator, EmptyPage
from django.views.decorators.csrf import csrf_exempt
from reportlab.lib.styles import getSampleStyleSheet
from django.contrib.auth import authenticate, login
from django.shortcuts import get_object_or_404
from django.shortcuts import render, redirect
from django.utils.timezone import make_aware
from reportlab.lib.pagesizes import letter
from datetime import datetime, timedelta
from django.contrib.auth import logout
from django.http import JsonResponse
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from django.contrib import messages
from collections import defaultdict
from reportlab.lib import colors
from django.db import connection
from pymongo import MongoClient
from .models import News, User
from bson.binary import Binary
from django.views import View
from django.db import models
from io import BytesIO
import bcrypt
import logging
import base64
import json


logger = logging.getLogger(__name__)

client = MongoClient("mongodb+srv://amantaphelix:amantaphelix@cluster0.mmmiw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0", tls=True)
db = client["news_database"]
news_collection = db["articles"]  # Match your collection name from models.py
try:
    news_collection.find_one()
    print("Database connection successful")
except Exception as e:
    print(f"Database connection error: {e}")
def dashboard_view(request):
    # Add debugging right at the start of the view function
    def debug_news_retrieval(user_department):
        print("Session Information:")
        for key, value in request.session.items():
            print(f"{key}: {value}")
        unique_categories = news_collection.distinct('category')
        print("Unique Categories in Database:")
        for category in unique_categories:
            print(category)
        total_docs = news_collection.count_documents({})
        print(f"Total documents in collection: {total_docs}")
        
        dept_docs = list(news_collection.find({"category": user_department}))
        print(f"Documents in department '{user_department}': {len(dept_docs)}")
        
        print("\nSample Documents:")
        sample_docs = list(news_collection.find().limit(5))
        for doc in sample_docs:
            print(json.dumps({
            'title': doc.get('title'),
            'category': doc.get('category'),
            'sentiment': doc.get('sentiment')
            }, indent=2))
    
    # Check document structure
        if dept_docs:
            sample_doc = dept_docs[0]
            print("\nDocument Keys:")
            print(sample_doc.keys())
        
        # Verify sentiment field
            print("\nSentiment Field Check:")
            print(f"Sentiment: {sample_doc.get('sentiment', 'No sentiment field')}")
    
    # Alternative retrieval to verify collection access
        all_docs = list(news_collection.find())
        print(f"\nTotal documents when finding all: {len(all_docs)}")
    
    # Call the debugging function
        debug_news_retrieval(user_department)
    
    # Rest of your existing view function code...

def login_view(request):
    user = None
    if request.method == 'POST':
        print(f"Login attempt: {request.POST.get('username')}")
        client = MongoClient("mongodb+srv://amantaphelix:amantaphelix@cluster0.mmmiw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0", tls=True)
        db = client["news_database"]
        users_collection = db["users"]

        username = request.POST.get('username')
        password = request.POST.get('password')

        user = users_collection.find_one({
            '$or': [
                {'username': username},
                {'login_id': username}
            ]
        })

        if user:
            if isinstance(user['password'], Binary):
                # Decode from Base64 Binary
                try:
                    decoded_hash = base64.b64decode(user['password'])
                    password_valid = bcrypt.checkpw(password.encode('utf-8'), decoded_hash)
                except:
                    password_valid = False
            else:
                # Handle raw bcrypt hash
                stored_password = user['password']
                if isinstance(stored_password, str):
                    stored_password = stored_password.encode('utf-8')
                password_valid = bcrypt.checkpw(password.encode('utf-8'), stored_password)

            if password_valid:
                # Store session data
                request.session['user_id'] = str(user['_id'])
                request.session['username'] = user.get('username')
                request.session['role'] = user.get('role', 'user')
                request.session['department'] = user.get('department', '')
                
                # Make sure session is saved
                request.session.modified = True
                
                # Log successful login for debugging
                print(f"User logged in: {user.get('username')} with role {user.get('role')}")
                
                # Redirect based on role
                if user.get('role') == 'admin':
                    return redirect('admin_dashboard')
                else:
                    return redirect('dashboard')
        print(f"User found: {user is not None}")
    if user:
        print(f"User role: {user.get('role')}")

    return render(request, 'login.html')

def dashboard(request):
    if 'user_id' not in request.session:
        return redirect('login')
    
    # Use 'category' to match the field in your MongoDB document
    user_department = request.session.get('department', '')
    print(user_department)
    
    # Fetch news data for the user's department
    if user_department:
        department_news = list(news_collection.find({"category": user_department}))
    else:
    # If no department, try to get a reasonable default
        default_category = news_collection.distinct('category')[0] if news_collection.distinct('category') else None
    
        if default_category:
            department_news = list(news_collection.find({"category": default_category}))
        else:
            department_news = list(news_collection.find())
    
    # Process sentiment data
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    total_count = len(department_news)
    
    # Data structures for the line chart
    daily_data = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})
    
    # Data structure for news channels
    channels_data = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})
    
    # Process each news item
    for news in department_news:
        # Use 'sentiment' directly from the document
        sentiment = news.get('sentiment','').lower()
        
        # Handle potential None or missing sentiment
        if sentiment is None:
            sentiment = 'Neutral'
        
        # Use 'url' as the channel name if 'source' is not available
        channel_name = news.get('source', 'Unknown')
        
        # Get timestamp and convert to date string
        timestamp = news.get('last_updated')

        if isinstance(timestamp, dict) and "$date" in timestamp:
            timestamp = timestamp["$date"] / 1000  # Convert milliseconds to seconds
        elif isinstance(timestamp, datetime):
            timestamp = timestamp.timestamp()  # Convert datetime to timestamp (seconds)
        else:
            timestamp = datetime.now().timestamp()  # Default to current time

        news_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')
        
        # Categorize sentiment
        if sentiment == 'positive':
            positive_count += 1
            daily_data[news_date]["positive"] += 1
            channels_data[channel_name]["positive"] += 1
        elif sentiment == 'negative':
            negative_count += 1
            daily_data[news_date]["negative"] += 1
            channels_data[channel_name]["negative"] += 1
        else:  # Neutral
            neutral_count += 1
            daily_data[news_date]["neutral"] += 1
            channels_data[channel_name]["neutral"] += 1
    
    # Calculate percentages
    if total_count > 0:
        positive_percentage = round((positive_count / total_count) * 100, 1)
        negative_percentage = round((negative_count / total_count) * 100, 1)
        neutral_percentage = round((neutral_count / total_count) * 100, 1)
    else:
        positive_percentage = 0
        negative_percentage = 0
        neutral_percentage = 0 # Default to neutral if no data
    
    # Prepare data for line chart (last 7 days)
    today = datetime.now()
    dates = []
    daily_positive = []
    daily_negative = []
    daily_neutral = []
    
    for i in range(6, -1, -1):
        date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
        dates.append(date)
        
        if date in daily_data:
            daily_positive.append(daily_data[date]["positive"])
            daily_negative.append(daily_data[date]["negative"])
            daily_neutral.append(daily_data[date]["neutral"])
        else:
            daily_positive.append(0)
            daily_negative.append(0)
            daily_neutral.append(0)
    
    # Prepare news channels data
    news_channels = []
    for channel, data in channels_data.items():
        news_channels.append({
            "name": channel,
            "positive_count": data["positive"],
            "negative_count": data["negative"],
            "neutral_count": data["neutral"]
        })
    
    # Sort channels by total news count
    news_channels.sort(key=lambda x: x["positive_count"] + x["negative_count"] + x["neutral_count"], reverse=True)
    
    context = {
        'user_department': user_department,
        'positive_percentage': positive_percentage,
        'negative_percentage': negative_percentage,
        'neutral_percentage': neutral_percentage,
        'dates': json.dumps(dates),
        'daily_positive_counts': json.dumps(daily_positive),
        'daily_negative_counts': json.dumps(daily_negative),
        'daily_neutral_counts': json.dumps(daily_neutral),
        'news_channels': news_channels,
    }
    print(f"User Department: {user_department}")
    print(f"Total News Items: {len(department_news)}")
    print(f"Sentiment breakdown: Positive={positive_count}, Negative={negative_count}, Neutral={neutral_count}")
    for news in department_news[:3]:
        print("Document Details:")
        print(f"Title: {news.get('title')}")
        print(f"Category: {news.get('category')}")
        print(f"Sentiment: {news.get('sentiment')}")
        print(f"Timestamp: {news.get('last_updated')}")
        print("---")
    
    return render(request, 'dashboard.html', context)

def notifications(request):
    if 'user_id' not in request.session:
        return redirect('login')
    
    # Check if user has admin role
    if request.session.get('role') == 'admin':
        return redirect('dashboard')  # Or create an admin_notifications view
    
    return redirect('dashboard')

def logout_view(request):
    request.session.flush()
    return redirect('login')

def get_news(request):
    
    search_query = request.GET.get('search', '').strip()
    date_filter = request.GET.get('date', '').strip()
    sentiment_filter = request.GET.get('sentiment', '').strip()
    page_number = int(request.GET.get("page", 1))
    limit = int(request.GET.get("limit", 30))

    # Get news from MongoDB
    news_queryset = News.objects.all()

    if search_query:
        news_queryset = news_queryset.filter(title__icontains=search_query)

    if date_filter:
        try:
            parsed_date = datetime.strptime(date_filter, "%Y-%m-%d")
            start_date = make_aware(parsed_date)
            end_date = start_date + timedelta(days=1)
            news_queryset = news_queryset.filter(last_updated__gte=start_date, last_updated__lt=end_date)
        except ValueError:
            return JsonResponse({"error": "Invalid date format. Use YYYY-MM-DD"}, status=400)

    if sentiment_filter:
        news_queryset = news_queryset.filter(sentiment__iexact=sentiment_filter)

    paginator = Paginator(news_queryset, limit)
    try:
        page_obj = paginator.page(page_number)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    news_data = []
    for article in page_obj:
        sentiment = str(article.sentiment) if isinstance(article.sentiment, str) else article.sentiment.get("label", "unknown")

        news_data.append({
            "article_id": str(article.article_id),  # ✅ FIXED!
            "title": article.title,
            "department": article.department,
            "sentiment": sentiment,
            "source": article.source,
            "last_updated": article.last_updated.strftime("%Y-%m-%d %H:%M") if article.last_updated else "Unknown",
            "url": article.url or "#",
            "image_url": article.image_url
        })

    return JsonResponse({
        "news": news_data,
        "total_pages": paginator.num_pages,
        "current_page": page_obj.number
    })


def article_detail(request, article_id):
    if not article_id or article_id.lower() == "none":
        return JsonResponse({"error": "Invalid article ID"}, status=400)

    # ✅ Correctly retrieve the article using MongoDB's ObjectId
    article = get_object_or_404(News, article_id=article_id)

    # ✅ Fix: Ensure sentiment is correctly extracted
    if isinstance(article.sentiment, str):
        sentiment_label = article.sentiment.strip()  # Ensure it's a clean string
        positive = 0
        negative = 0
        neutral = 100 if sentiment_label.lower() == "neutral" else 0
    elif isinstance(article.sentiment, dict):
        sentiment_label = article.sentiment.get("label", "Unknown")
        positive = article.sentiment.get("positive", 0)
        negative = article.sentiment.get("negative", 0)
        neutral = article.sentiment.get("neutral", 0)
    else:
        sentiment_label = "Unknown"
        positive = negative = 0
        neutral = 100

    # ✅ Fix: Extract `last_updated` correctly from MongoDB
    last_updated = article.last_updated.strftime("%Y-%m-%d %H:%M") if article.last_updated else "Unknown Date"

    # ✅ Get related articles from the same department
    related_articles = News.objects.filter(department=article.department).exclude(article_id=article_id)[:5]

    return render(request, "article_detail.html", {
        "article": article,
        "last_updated": last_updated,
        "sentiment_label": sentiment_label,
        "positive_percentage": positive,
        "negative_percentage": negative,
        "neutral_percentage": neutral,
        "related_articles": related_articles
    })
def news(request):
    if 'user_id' not in request.session:
        return redirect('login')
    
    # Check if user has admin role
    if request.session.get('role') == 'admin':
        return redirect('admin_news')
    
    return render(request, 'news.html')
def get_notifications(request):
    if 'user_id' not in request.session:
        return redirect('login')
    
    # Get user's department from session
    user_department = request.session.get('department', '')
    
    # Fetch all news for the department first
    if user_department:
        department_news = list(news_collection.find({"category": user_department}).sort("last_updated", -1))
    else:
        department_news = list(news_collection.find().sort("last_updated", -1))
    
    # Filter for negative sentiment manually
    negative_news = []
    for news in department_news:
        sentiment = news.get('sentiment')
        
        # Handle different formats of sentiment storage
        if isinstance(sentiment, str) and sentiment.lower() == 'negative':
            negative_news.append(news)
        elif isinstance(sentiment, dict) and sentiment.get('label', '').lower() == 'negative':
            negative_news.append(news)
        # For debugging, print information about items we're processing
        if len(negative_news) < 3:  # Just log a few for debugging
            print(f"News item: {news.get('title')}, Sentiment: {sentiment}, Type: {type(sentiment)}")
    
    # Limit to 10 notifications
    notifications = negative_news[:10]
    
    # For debugging
    print(f"Found {len(negative_news)} negative news items out of {len(department_news)} total")
    
    return render(request, 'notifications.html', {'notifications': notifications})
def export_pdf(request):
    if 'user_id' not in request.session:
        return redirect('login')
    
    # Create a file-like buffer to receive PDF data
    buffer = BytesIO()
    
    # Create the PDF object, using the buffer as its "file"
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Define styles
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    subtitle_style = styles['Heading2']
    normal_style = styles['Normal']
    
    # Add title
    elements.append(Paragraph("News Sentiment Dashboard Report", title_style))
    elements.append(Spacer(1, 12))
    
    # Add department info
    user_department = request.session.get('department', '')
    elements.append(Paragraph(f"Department: {user_department}", subtitle_style))
    elements.append(Spacer(1, 12))
    
    # Get dashboard data (reuse the dashboard view logic)
    user_department = request.session.get('department', '')
    
    if user_department:
        department_news = list(news_collection.find({"category": user_department}))
    else:
        default_category = news_collection.distinct('category')[0] if news_collection.distinct('category') else None
        
        if default_category:
            department_news = list(news_collection.find({"category": default_category}))
        else:
            department_news = list(news_collection.find())
    
    # Process sentiment data
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    total_count = len(department_news)
    
    # Data structure for news channels
    channels_data = defaultdict(lambda: {"positive": 0, "negative": 0, "neutral": 0})
    
    # Process each news item
    for news in department_news:
        sentiment = news.get('sentiment', '').lower()
        
        if sentiment is None:
            sentiment = 'neutral'
        
        channel_name = news.get('source', 'Unknown')
        
        # Categorize sentiment
        if sentiment == 'positive':
            positive_count += 1
            channels_data[channel_name]["positive"] += 1
        elif sentiment == 'negative':
            negative_count += 1
            channels_data[channel_name]["negative"] += 1
        else:  # Neutral
            neutral_count += 1
            channels_data[channel_name]["neutral"] += 1
    
    # Calculate percentages
    if total_count > 0:
        positive_percentage = round((positive_count / total_count) * 100, 1)
        negative_percentage = round((negative_count / total_count) * 100, 1)
        neutral_percentage = round((neutral_count / total_count) * 100, 1)
    else:
        positive_percentage = 0
        negative_percentage = 0
        neutral_percentage = 0
    
    # Add sentiment overview
    elements.append(Paragraph("Sentiment Overview", subtitle_style))
    elements.append(Spacer(1, 12))
    
    data = [
        ["Sentiment", "Count", "Percentage"],
        ["Positive", str(positive_count), f"{positive_percentage}%"],
        ["Negative", str(negative_count), f"{negative_percentage}%"],
        ["Neutral", str(neutral_count), f"{neutral_percentage}%"],
        ["Total", str(total_count), "100%"]
    ]
    
    # Create table for sentiment overview
    table = Table(data, colWidths=[200, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgreen),
        ('BACKGROUND', (0, 2), (-1, 2), colors.lightcoral),
        ('BACKGROUND', (0, 3), (-1, 3), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    elements.append(table)
    elements.append(Spacer(1, 24))
    
    # Add news channels overview
    elements.append(Paragraph("News Channels Overview", subtitle_style))
    elements.append(Spacer(1, 12))
    
    # Prepare news channels data
    news_channels = []
    for channel, data in channels_data.items():
        news_channels.append({
            "name": channel,
            "positive_count": data["positive"],
            "negative_count": data["negative"],
            "neutral_count": data["neutral"]
        })
    
    # Sort channels by total news count
    news_channels.sort(key=lambda x: x["positive_count"] + x["negative_count"] + x["neutral_count"], reverse=True)
    
    # Create table for news channels
    channel_data = [["Channel", "Positive", "Negative", "Neutral", "Total"]]
    
    for channel in news_channels[:10]:  # Limit to top 10 channels
        total = channel["positive_count"] + channel["negative_count"] + channel["neutral_count"]
        channel_data.append([
            channel["name"],
            str(channel["positive_count"]),
            str(channel["negative_count"]),
            str(channel["neutral_count"]),
            str(total)
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
    
    # Add timestamp
    elements.append(Spacer(1, 36))
    report_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    elements.append(Paragraph(f"Report generated on: {report_date}", normal_style))
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()
    
    # Create HTTP response with PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="dashboard_report.pdf"'
    response.write(pdf)
    
    return response
