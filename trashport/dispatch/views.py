from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from .models import DispatchBatch
from .serializers import DispatchBatchSerializer, TriggerDispatchSerializer
from .scheduler import DispatchScheduler


class DispatchBatchListView(generics.ListAPIView):
    queryset = DispatchBatch.objects.all()
    serializer_class = DispatchBatchSerializer
    permission_classes = [IsAdminUser]


@api_view(["POST"])
@permission_classes([IsAdminUser])
def trigger_dispatch_view(request):
    """Admin endpoint to trigger automatic dispatch algorithm."""
    serializer = TriggerDispatchSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    algorithm = serializer.validated_data.get("algorithm", "NEAREST")
    batch = DispatchScheduler.run_auto_dispatch(algorithm=algorithm, user=request.user)

    return Response(DispatchBatchSerializer(batch).data, status=status.HTTP_201_CREATED)
