from django.contrib import admin, messages
from unfold.admin import ModelAdmin
from unfold.decorators import action

from .models import Appointment
from .services import set_status


@admin.register(Appointment)
class AppointmentAdmin(ModelAdmin):
    """Garage partners (staff users in the `garage_partner` group) only see their own garages."""

    list_display = ("slot_start", "garage", "order", "status")
    list_filter = ("status", "garage")
    search_fields = ("order__number", "garage__name")
    list_select_related = ("garage", "order")
    readonly_fields = ("garage", "order", "slot_start", "slot_end")
    date_hierarchy = "slot_start"
    actions = ("confirm_appointments", "complete_appointments")

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.is_superuser:
            return queryset
        return queryset.filter(garage__partner_users=request.user)

    def has_add_permission(self, request):
        return False

    @action(description="Confirm selected appointments")
    def confirm_appointments(self, request, queryset):
        count = 0
        for appointment in queryset.filter(status=Appointment.Status.BOOKED):
            set_status(appointment, Appointment.Status.CONFIRMED)
            count += 1
        self.message_user(request, f"{count} appointment(s) confirmed.", messages.SUCCESS)

    @action(description="Mark selected appointments as completed")
    def complete_appointments(self, request, queryset):
        count = 0
        for appointment in queryset.filter(
            status__in=(Appointment.Status.BOOKED, Appointment.Status.CONFIRMED)
        ):
            set_status(appointment, Appointment.Status.COMPLETED)
            count += 1
        self.message_user(request, f"{count} appointment(s) completed.", messages.SUCCESS)
