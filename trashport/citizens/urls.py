"""
Citizen role URL route registrations.

Exposes URLs dedicated to citizen operations:
  - Dashboard: active pickups, eco-points balance, request history
  - Pickups: scheduling new pickups, viewing status tracking
  - Addresses: managing pickup delivery/collection locations
  - Complaints: submitting feedback and service dispute tickets
  - Wallet: viewing points balance and applying session discount coupons
"""

from django.urls import path
from trashport.core.waste_management.views import (
    DashboardView,
    PickupRequestCreateView,
    PickupRequestDetailView,
    AddressListView,
    AddressCreateView,
    ComplaintListView,
    ComplaintCreateView,
)
from trashport.citizens.views import (
    CitizenWalletView,
    CitizenRedeemCouponView,
    CitizenRemoveCouponView,
)

app_name = "citizens"

urlpatterns = [
    # Citizen central hub
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    # Pickup booking and tracking
    path("pickups/new/", PickupRequestCreateView.as_view(), name="pickup_create"),
    path("pickups/<int:pk>/", PickupRequestDetailView.as_view(), name="pickup_detail"),
    # Saved addresses
    path("addresses/", AddressListView.as_view(), name="address_list"),
    path("addresses/new/", AddressCreateView.as_view(), name="address_create"),
    # Complaints & feedback
    path("complaints/", ComplaintListView.as_view(), name="complaint_list"),
    path("complaints/new/", ComplaintCreateView.as_view(), name="complaint_create"),
    # Wallet points & coupon management
    path("wallet/", CitizenWalletView.as_view(), name="wallet"),
    path("wallet/redeem-coupon/", CitizenRedeemCouponView.as_view(), name="redeem_coupon"),
    path("wallet/remove-coupon/", CitizenRemoveCouponView.as_view(), name="remove_coupon"),
]
