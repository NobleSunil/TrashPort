# ==============================================================================
# TrashPort - Notification API Views
# ==============================================================================
# This module provides REST API endpoints for user notification management:
# 1. NotificationListView             - Fetches all notifications for the logged-in user
# 2. mark_notification_read_view      - Marks an individual notification as read
# 3. mark_all_notifications_read_view - Bulk marks all unread notifications as read
# 4. clear_all_notifications_view     - Clears/deletes all notifications for the user
#
# Authentication:
# All endpoints require an authenticated user session (IsAuthenticated permission).
# Users are strictly isolated so they can only view and modify their own alerts.
# ==============================================================================

from rest_framework import generics
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Notification
from .serializers import NotificationSerializer


# ==============================================================================
# 1. Notification List View (GET /api/notifications/)
# ==============================================================================
class NotificationListView(generics.ListAPIView):
    """
    Class-based view that lists all notifications for the authenticated user.
    Inherits from Django REST Framework's ListAPIView.
    - Serializer: NotificationSerializer formats records into JSON objects
    - Permissions: IsAuthenticated prevents unauthenticated access
    """
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filters notifications specifically for the requesting user.
        Orders by latest first (defined by Notification.Meta.ordering).
        """
        return Notification.objects.filter(user=self.request.user)


# ==============================================================================
# 2. Mark Single Notification as Read (POST /api/notifications/<id>/read/)
# ==============================================================================
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_notification_read_view(request, pk: int):
    """
    API endpoint to mark a specific notification as read.
    Parameters:
        pk (int): Primary key ID of the notification to update.
    Returns:
        JSON response with success status and notification ID, or 404 if not found.
    """
    # Look up notification matching ID and belonging strictly to the current user
    notification = Notification.objects.filter(pk=pk, user=request.user).first()
    if not notification:
        # Return HTTP 404 error if record does not exist or belongs to another user
        return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)

    # Mark the notification as read and save only the updated column for database efficiency
    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return Response({"status": "success", "id": notification.pk})


# ==============================================================================
# 3. Mark All Notifications as Read (POST /api/notifications/read-all/)
# ==============================================================================
@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read_view(request):
    """
    API endpoint to bulk-update all unread notifications to read status.
    Executes a single SQL UPDATE query for performance.
    """
    # Bulk update all unread notifications belonging to the current user
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({"status": "success"})


# ==============================================================================
# 4. Clear All Notifications (POST/DELETE /api/notifications/clear/)
# ==============================================================================
@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def clear_all_notifications_view(request):
    """
    API endpoint to clear (permanently delete) all notifications for the user.
    Returns:
        JSON response with count of deleted notification records.
    """
    # Delete all notification records belonging to the authenticated user
    count, _ = Notification.objects.filter(user=request.user).delete()
    return Response({"status": "success", "deleted_count": count})

