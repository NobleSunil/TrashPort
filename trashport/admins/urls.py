from django.urls import path
from waste_management.views import (
    WasteCategoryListView,
    WasteCategoryCreateView,
    SubscriptionTierListView,
    SubscriptionTierCreateView,
    UserListView,
    AutoAssignPickupsView,
    SubscriptionOverviewView,
    ExportPickupsCSVView,
    ExportRevenueCSVView,
)

app_name = "admins"

urlpatterns = [
    path("categories/", WasteCategoryListView.as_view(), name="category_list"),
    path("categories/new/", WasteCategoryCreateView.as_view(), name="category_create"),
    path("tiers/", SubscriptionTierListView.as_view(), name="tier_list"),
    path("tiers/new/", SubscriptionTierCreateView.as_view(), name="tier_create"),
    path("users/", UserListView.as_view(), name="user_list"),
    path("auto-assign/", AutoAssignPickupsView.as_view(), name="auto_assign"),
    path("subscriptions/", SubscriptionOverviewView.as_view(), name="subscription_overview"),
    path("export/pickups/", ExportPickupsCSVView.as_view(), name="export_pickups"),
    path("export/revenue/", ExportRevenueCSVView.as_view(), name="export_revenue"),
]
