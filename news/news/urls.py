"""
URL configuration for news project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from newsapp import views,admin_views
from django.urls import path

urlpatterns = [
    path('admin/', admin_views.admin_dashboard, name='admin_dashboard'),
    path('admin/news/', admin_views.admin_news, name='admin_news'),

    path('news/delete/<str:article_id>/', admin_views.deleteNews, name='deleteNews'),
    path('admin/news/news_get/', admin_views.news_get_view, name='news_get'),
    path('admin/users/', admin_views.admin_users, name='admin_users'),
    
    path('admin/export-pdf/', admin_views.export_pdf, name='export_pdf'),  
    path('admin/user_api/', admin_views.user_api, name='user_api'),
    path('',views.login_view, name='login'),
    path('login/',views.login_view, name='login'),
    path('dashboard/',views.dashboard,name='dashboard'),
    path('news/',views.news,name='news'),
    path('news/news_get/',views.get_news, name='get_news'),
    path('news/news_get/<str:article_id>/',views.article_detail, name="article_detail"),
    path('notifications/',views.get_notifications,name='notifications'),
    path('logout/', views.logout_view, name='logout'),
    path('export-pdf/', views.export_pdf, name='export_pdf'),
    

]
