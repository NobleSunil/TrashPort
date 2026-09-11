from django.urls import path
from trashport.admins.views import AdminLiveMapView
from .views import (
    DashboardView,
    AddressListView, AddressCreateView, AddressUpdateView, AddressDeleteView,
    PickupRequestCreateView, PickupRequestDetailView, PickupStatusUpdateView,
    ComplaintListView, ComplaintCreateView, ComplaintDetailView,
    WasteCategoryListView, WasteCategoryCreateView, WasteCategoryUpdateView,
    SubscribeView,
    SubscriptionTierListView, SubscriptionTierCreateView, SubscriptionTierUpdateView,
    UserListView, CollectorCreateView, UserDetailView, UserToggleActiveView, CollectorVerificationView, WalletAdjustView, CollectorRedeemUPIView,
    AutoAssignPickupsView, SubscriptionOverviewView, ExportPickupsCSVView, ExportRevenueCSVView,
    OperationsReportView,
    PaymentCheckoutView, PaymentSuccessView, PickupInvoiceView,
    CollectorPayoutSettingUpdateView,
    SubmitAnonymousFeedbackView,
    AdminAnonymousFeedbackListView,
)
from trashport.citizens.views import CitizenWalletView

app_name = "waste_management"

urlpatterns = [
    # Dashboard & Wallet
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("wallet/", CitizenWalletView.as_view(), name="wallet"),
    path("wallet/redeem-upi/", CollectorRedeemUPIView.as_view(), name="collector_redeem_upi"),
    
    # Subscriptions
    path("subscriptions/<int:pk>/subscribe/", SubscribeView.as_view(), name="subscribe"),
    
    # Addresses CRUD
    path("addresses/", AddressListView.as_view(), name="address_list"),
    path("addresses/new/", AddressCreateView.as_view(), name="address_create"),
    path("addresses/<int:pk>/edit/", AddressUpdateView.as_view(), name="address_update"),
    path("addresses/<int:pk>/delete/", AddressDeleteView.as_view(), name="address_delete"),
    
    # Pickup Requests CRUD & actions
    path("pickups/new/", PickupRequestCreateView.as_view(), name="pickup_create"),
    path("pickups/<int:pk>/", PickupRequestDetailView.as_view(), name="pickup_detail"),
    path("pickups/<int:pk>/status/", PickupStatusUpdateView.as_view(), name="pickup_status_update"),
    path("pickups/<int:pk>/pay/", PaymentCheckoutView.as_view(), name="payment_checkout"),
    path("pickups/<int:pk>/pay/success/", PaymentSuccessView.as_view(), name="payment_success"),
    path("pickups/<int:pk>/invoice/", PickupInvoiceView.as_view(), name="payment_invoice"),
    path("admin/pickups/auto-assign/", AutoAssignPickupsView.as_view(), name="pickup_auto_assign"),
    
    # Complaints & Anonymous Feedback
    path("complaints/", ComplaintListView.as_view(), name="complaint_list"),
    path("complaints/new/", ComplaintCreateView.as_view(), name="complaint_create"),
    path("complaints/<int:pk>/", ComplaintDetailView.as_view(), name="complaint_detail"),
    path("feedback/anonymous/", SubmitAnonymousFeedbackView.as_view(), name="submit_anonymous_feedback"),
    path("manage/feedback/", AdminAnonymousFeedbackListView.as_view(), name="anonymous_feedback_list"),
    
    # Admin Master Entries - Categories
    path("manage/categories/", WasteCategoryListView.as_view(), name="category_list"),
    path("manage/categories/new/", WasteCategoryCreateView.as_view(), name="category_create"),
    path("manage/categories/<int:pk>/edit/", WasteCategoryUpdateView.as_view(), name="category_update"),

    # Admin Master Entries - Tiers
    path("manage/tiers/", SubscriptionTierListView.as_view(), name="tier_list"),
    path("manage/tiers/new/", SubscriptionTierCreateView.as_view(), name="tier_create"),
    path("manage/tiers/<int:pk>/edit/", SubscriptionTierUpdateView.as_view(), name="tier_update"),

    # Admin Master Entries - Collector Payout Calculation Settings
    path("manage/payout-settings/", CollectorPayoutSettingUpdateView.as_view(), name="collector_payout_settings"),

    # Admin User Administration
    path("manage/users/", UserListView.as_view(), name="user_list"),
    path("manage/users/collectors/new/", CollectorCreateView.as_view(), name="collector_create"),
    path("manage/users/<int:pk>/", UserDetailView.as_view(), name="user_detail"),
    path("manage/users/<int:pk>/toggle/", UserToggleActiveView.as_view(), name="user_toggle_active"),
    path("manage/users/<int:pk>/verify/", CollectorVerificationView.as_view(), name="collector_verify"),
    path("manage/users/<int:pk>/wallet/", WalletAdjustView.as_view(), name="user_wallet_adjust"),

    # Admin Subscriptions, Auto-Assign & Exports
    path("manage/live-map/", AdminLiveMapView.as_view(), name="live_map"),
    path("manage/pickups/auto-assign/", AutoAssignPickupsView.as_view(), name="pickup_auto_assign"),
    path("manage/subscriptions/", SubscriptionOverviewView.as_view(), name="subscription_overview"),
    path("manage/reports/operations/", OperationsReportView.as_view(), name="operations_report"),
    path("manage/export/pickups/", ExportPickupsCSVView.as_view(), name="export_pickups_csv"),
    path("manage/export/revenue/", ExportRevenueCSVView.as_view(), name="export_revenue_csv"),
]



