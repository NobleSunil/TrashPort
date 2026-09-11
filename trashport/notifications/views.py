from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Notification
from .serializers import NotificationSerializer


class NotificationListView(generics.ListAPIView):
    serializer_class = NotificationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Notification.objects.filter(user=self.request.user)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_notification_read_view(request, pk: int):
    notification = Notification.objects.filter(pk=pk, user=request.user).first()
    if not notification:
        return Response({"error": "Notification not found"}, status=status.HTTP_404_NOT_FOUND)

    notification.is_read = True
    notification.save(update_fields=["is_read"])
    return Response({"status": "success", "id": notification.pk})


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read_view(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({"status": "success"})


@api_view(["POST", "DELETE"])
@permission_classes([IsAuthenticated])
def clear_all_notifications_view(request):
    """
    Clears (deletes) all notifications for the authenticated user.
    """
    count, _ = Notification.objects.filter(user=request.user).delete()
    return Response({"status": "success", "deleted_count": count})

