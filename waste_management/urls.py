from django.urls import path
from .views import (
    DashboardView,
    AddressListView, AddressCreateView, AddressUpdateView, AddressDeleteView,
    PickupRequestCreateView, PickupRequestDetailView, PickupStatusUpdateView,
    ComplaintListView, ComplaintCreateView, ComplaintDetailView,
    WasteCategoryListView, WasteCategoryCreateView, WasteCategoryUpdateView,
    SubscriptionTierListView, SubscriptionTierCreateView, SubscriptionTierUpdateView,
    SubscribeView
)

app_name = "waste_management"

urlpatterns = [
    # Dashboard
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    
    # Addresses CRUD
    path("addresses/", AddressListView.as_view(), name="address_list"),
    path("addresses/new/", AddressCreateView.as_view(), name="address_create"),
    path("addresses/<int:pk>/edit/", AddressUpdateView.as_view(), name="address_update"),
    path("addresses/<int:pk>/delete/", AddressDeleteView.as_view(), name="address_delete"),
    
    # Pickup Requests CRUD & actions
    path("pickups/new/", PickupRequestCreateView.as_view(), name="pickup_create"),
    path("pickups/<int:pk>/", PickupRequestDetailView.as_view(), name="pickup_detail"),
    path("pickups/<int:pk>/status/", PickupStatusUpdateView.as_view(), name="pickup_status_update"),
    
    # Complaints CRUD & actions
    path("complaints/", ComplaintListView.as_view(), name="complaint_list"),
    path("complaints/new/", ComplaintCreateView.as_view(), name="complaint_create"),
    path("complaints/<int:pk>/", ComplaintDetailView.as_view(), name="complaint_detail"),
    
    # Admin Master Entries - Categories
    path("admin/categories/", WasteCategoryListView.as_view(), name="category_list"),
    path("admin/categories/new/", WasteCategoryCreateView.as_view(), name="category_create"),
    path("admin/categories/<int:pk>/edit/", WasteCategoryUpdateView.as_view(), name="category_update"),
    
    # Admin Master Entries - Tiers
    path("admin/tiers/", SubscriptionTierListView.as_view(), name="tier_list"),
    path("admin/tiers/new/", SubscriptionTierCreateView.as_view(), name="tier_create"),
    path("admin/tiers/<int:pk>/edit/", SubscriptionTierUpdateView.as_view(), name="tier_update"),
    
    # Subscription action
    path("subscribe/<int:pk>/", SubscribeView.as_view(), name="subscribe"),
]
