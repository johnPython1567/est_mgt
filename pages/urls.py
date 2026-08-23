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
        path('realtor/apply/', views.RealtorApplyView.as_view(), name='realtor-apply'),
    path('realtor/dashboard/', views.RealtorDashboardView.as_view(), name='realtor-dashboard'),
    path('realtor/properties/create/', views.PropertyCreateView.as_view(), name='property-create'),
    path('realtor/properties/<slug:slug>/edit/', views.PropertyUpdateView.as_view(), name='property-edit'),
]
