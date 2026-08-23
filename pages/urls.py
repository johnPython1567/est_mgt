from django.urls import path

from . import views


urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('properties/', views.PropertyListView.as_view(), name='property-list'),
    path(
    "properties/<slug:slug>/favorite/",
    views.toggle_favorite,
    name="toggle-favorite",
    ),
    path('properties/<slug:slug>/', views.PropertyDetailView.as_view(), name='property-detail'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.UserLoginView.as_view(), name='login'),
    path('logout/', views.UserLogoutView.as_view(), name='logout'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('inquiries/create/', views.InquiryCreateView.as_view(), name='inquiry-create'),
]
