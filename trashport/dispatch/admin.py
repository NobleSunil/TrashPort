from django.contrib import admin
from .models import DispatchBatch


@admin.register(DispatchBatch)
class DispatchBatchAdmin(admin.ModelAdmin):
    list_display = ("id", "algorithm_used", "assigned_count", "unassigned_count", "executed_by", "created_at")
    list_filter = ("algorithm_used", "created_at")
