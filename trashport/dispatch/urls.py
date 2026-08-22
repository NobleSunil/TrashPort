from django.urls import path
from .views import DispatchBatchListView, trigger_dispatch_view

app_name = "dispatch"

urlpatterns = [
    path("batches/", DispatchBatchListView.as_view(), name="batch_list"),
    path("trigger/", trigger_dispatch_view, name="trigger_dispatch"),
]
