from django.urls import path
from .views import RequestLogsListView,RequestLogsCreateView
from .views import register_view, login_view, dashboard_view, logs_view,logout_view, blocked_countries_view,unblock_country

urlpatterns = [
    path('api/logs/', RequestLogsListView.as_view(), name='logs-list'),
    path('api/create/',RequestLogsCreateView.as_view(),name='logs-create'),
    path('',login_view,name='login' ),  
    path('register/', register_view, name='register'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('raw-logs/', logs_view, name='logs'),
    path('logout/', logout_view, name='logout'),
    path('blocked-countries/', blocked_countries_view, name='blocked-countries'),
    path('unblock-country/<str:country_name>/', unblock_country, name='unblock-country'),
]
