from django.shortcuts import render,redirect
from rest_framework.generics import ListAPIView,CreateAPIView
from .serializer import RequestLogSerializer
from .models import RequestLog,BlockedCountry
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login,logout,authenticate
from django.contrib.auth.forms import UserCreationForm,AuthenticationForm
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
from django.core.paginator import Paginator
from django.db import connection
import numpy as np
import requests

#API Views
class RequestLogsListView(ListAPIView):
    queryset = RequestLog.objects.all().order_by('-timestamp')
    serializer_class = RequestLogSerializer

class RequestLogsCreateView(CreateAPIView):
    serializer_class = RequestLogSerializer

@login_required(login_url='')
def logs_view(request):
    # Get all logs ordered by timestamp
    all_logs = RequestLog.objects.all().order_by('-timestamp')
    
    # Set up pagination - 10 logs per page
    page_number = request.GET.get('page', 1)
    paginator = Paginator(all_logs, 10)
    page_obj = paginator.get_page(page_number)
    
   
    context = {
        'page_obj': page_obj,
        'total_logs': all_logs.count(),
    }
    
    return render(request, 'analytics/logs.html', context)
# User Registration and Login Views
def register_view(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard')
    else:
        form = UserCreationForm()
    return render(request, 'analytics/register.html', {'form': form})

def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request,data=request.POST)
        if form.is_valid():
            uname = form.cleaned_data.get('username')
            pwd = form.cleaned_data.get('password')
            user = authenticate(username=uname, password=pwd)
            if user is not None:
                login(request, user)
                return redirect('dashboard')
            else:
                form.add_error(None, "Invalid username or password")
    else:
        form = AuthenticationForm()
    return render(request, 'analytics/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login')

@login_required(login_url='')
def dashboard_view(request):
    # Time ranges for filtering
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    
    with connection.cursor() as cursor:
        # Total requests count
        cursor.execute("SELECT COUNT(*) FROM analytics_requestlog")
        total_requests = cursor.fetchone()[0]
        
        # Last 24 hours count
        cursor.execute("SELECT COUNT(*) FROM analytics_requestlog WHERE timestamp >= %s", [last_24h])
        requests_24h = cursor.fetchone()[0]
        
        # Response time metrics
        cursor.execute("""
            SELECT 
                AVG(response_time) as avg_time,
                MIN(response_time) as min_time,
                MAX(response_time) as max_time
            FROM analytics_requestlog
        """)
        row = cursor.fetchone()
        avg_response_time = row[0] or 0
        min_response_time = row[1] or 0
        max_response_time = row[2] or 0
        
        # Get p95 response time (more complex)
        cursor.execute("SELECT response_time FROM analytics_requestlog ORDER BY response_time")
        response_times = [row[0] for row in cursor.fetchall()]
        p95_response_time = np.percentile(response_times, 95) if response_times else 0
        
        # Top countries
        cursor.execute("""
            SELECT country, COUNT(*) as count
            FROM analytics_requestlog
            GROUP BY country
            ORDER BY count DESC
            LIMIT 10
        """)
        top_countries = [{'country': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Top pages
        cursor.execute("""
            SELECT path, COUNT(*) as count
            FROM analytics_requestlog
            GROUP BY path
            ORDER BY count DESC
            LIMIT 10
        """)
        top_pages = [{'path': row[0], 'count': row[1]} for row in cursor.fetchall()]
        
        # Status code distribution
        cursor.execute("""
            SELECT http_status, COUNT(*) as count
            FROM analytics_requestlog
            GROUP BY http_status
            ORDER BY http_status
        """)
        status_codes = [{'http_status': row[0], 'count': row[1]} for row in cursor.fetchall()]
    
    context = {
        'total_requests': total_requests,
        'requests_24h': requests_24h,
        'avg_response_time': avg_response_time,
        'min_response_time': min_response_time,
        'max_response_time': max_response_time,
        'p95_response_time': p95_response_time,
        'top_countries': top_countries,
        'top_pages': top_pages,
        'status_codes': status_codes
    }
    
    return render(request, 'analytics/dashboard.html', context)


@login_required(login_url='')
def blocked_countries_view(request):
    if request.method == 'POST':
        country_name = request.POST.get('country_name')
        reason = request.POST.get('reason')
        BlockedCountry.objects.get_or_create(
            country_name=country_name,
            defaults={'reason': reason}
        )
        messages.success(request, f"{country_name} has been blocked successfully.")  
        requests.post(
            'http://localhost:9500/proxy/api/admin/refresh-blocked-countries'
        )
        return redirect('blocked-countries')
    
    blocked_countries = BlockedCountry.objects.all().order_by('country_name')
    available_countries = RequestLog.objects.values('country').distinct().order_by('country')

    context = {
        'blocked_countries': blocked_countries,
        'available_countries': available_countries
    }

    return render(request, 'analytics/blocked_countries.html', context)


@login_required(login_url='')
def unblock_country(request, country_name):
    if request.method == 'POST':
        try:
            country = BlockedCountry.objects.get(country_name=country_name)
            country.delete()
            messages.success(request, f"Country '{country_name}' has been unblocked")
            try:
                requests.post('http://localhost:9500/proxy/api/admin/refresh-blocked-countries')
            except:
                messages.warning(request, "Proxy cache refresh failed. Changes may take effect after proxy restart.")     
        except BlockedCountry.DoesNotExist:
            messages.error(request, f"Country '{country_name}' not found")
            
    return redirect('blocked-countries')