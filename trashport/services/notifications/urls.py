# ==============================================================================
# TrashPort - Notification URL Routing
# ==============================================================================
# Defines the URL endpoints for the Notifications REST API.
# Namespace: "notifications"
# ==============================================================================

from django.urls import path

from .views import NotificationListView
from .views import clear_all_notifications_view
from .views import mark_all_notifications_read_view
from .views import mark_notification_read_view

app_name = "notifications"

# API Route Mapping:
# - GET        /api/notifications/          -> List all notifications for current user
# - POST       /api/notifications/<id>/read/ -> Mark single notification as read
# - POST/DEL   /api/notifications/read-all/ -> Mark all unread notifications as read
# - POST/DEL   /api/notifications/clear/    -> Delete all notifications for user
urlpatterns = [
    path("", NotificationListView.as_view(), name="notification_list"),
    path("<int:pk>/read/", mark_notification_read_view, name="mark_read"),
    path("read-all/", mark_all_notifications_read_view, name="mark_all_read"),
    path("clear/", clear_all_notifications_view, name="clear_all"),
]
