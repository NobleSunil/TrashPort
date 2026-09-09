from django.urls import path
from waste_management.views import (
    DashboardView,
    PickupRequestCreateView,
    PickupRequestDetailView,
    AddressListView,
    AddressCreateView,
    ComplaintListView,
    ComplaintCreateView,
)
from trashport.citizens.views import CitizenWalletView, CitizenRedeemCouponView, CitizenRemoveCouponView

app_name = "citizens"

urlpatterns = [
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path("pickups/new/", PickupRequestCreateView.as_view(), name="pickup_create"),
    path("pickups/<int:pk>/", PickupRequestDetailView.as_view(), name="pickup_detail"),
    path("addresses/", AddressListView.as_view(), name="address_list"),
    path("addresses/new/", AddressCreateView.as_view(), name="address_create"),
    path("complaints/", ComplaintListView.as_view(), name="complaint_list"),
    path("complaints/new/", ComplaintCreateView.as_view(), name="complaint_create"),
    path("wallet/", CitizenWalletView.as_view(), name="wallet"),
    path("wallet/redeem-coupon/", CitizenRedeemCouponView.as_view(), name="redeem_coupon"),
    path("wallet/remove-coupon/", CitizenRemoveCouponView.as_view(), name="remove_coupon"),
]
