from django.urls import path
from . import views

urlpatterns = [
    path('login', views.login, name='oauth_login'),
    path('logout', views.logout, name='oauth_logout'),
    path('authorize', views.authorize, name='oauth_authorize'),
]
