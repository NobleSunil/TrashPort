from django.urls import path
from .views import (
    NotificationListView,
    mark_notification_read_view,
    mark_all_notifications_read_view,
    clear_all_notifications_view,
)

app_name = "notifications"

urlpatterns = [
    path("", NotificationListView.as_view(), name="notification_list"),
    path("<int:pk>/read/", mark_notification_read_view, name="mark_read"),
    path("read-all/", mark_all_notifications_read_view, name="mark_all_read"),
    path("clear/", clear_all_notifications_view, name="clear_all"),
]
