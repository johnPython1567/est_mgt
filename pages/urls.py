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
    path('realtors/', views.RealtorListView.as_view(), name='realtor-list'),
    path('realtors/<slug:slug>/', views.RealtorPublicDetailView.as_view(), name='realtor-detail'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('compare/', views.CompareView.as_view(), name='property-compare'),
    path('compare/clear/', views.clear_compare, name='clear-compare'),
    path('properties/<slug:slug>/compare/', views.toggle_compare, name='toggle-compare'),
    path('realtor/apply/', views.RealtorApplyView.as_view(), name='realtor-apply'),
    path('realtor/profile/edit/', views.RealtorProfileUpdateView.as_view(), name='realtor-profile-edit'),
    path('realtor/dashboard/', views.RealtorDashboardView.as_view(), name='realtor-dashboard'),
    path('realtor/properties/create/', views.PropertyCreateView.as_view(), name='property-create'),
    path('realtor/properties/<slug:slug>/edit/', views.PropertyUpdateView.as_view(), name='property-edit'),
    path('realtor/properties/<slug:slug>/images/', views.PropertyImageManageView.as_view(), name='property-images'),
    path('realtor/properties/<slug:slug>/images/<int:image_id>/delete/', views.delete_property_image, name='delete-property-image'),
    path('realtor/inquiries/', views.RealtorInquiryListView.as_view(), name='realtor-inquiries'),
    path('realtor/inquiries/<int:pk>/status/', views.update_inquiry_status, name='update-inquiry-status'),
]