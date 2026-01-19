from django.utils import timezone
from django.contrib.admin import SimpleListFilter


class CreatedRecentlyFilter(SimpleListFilter):
    """
    This class can be used on any model that inherits from Sponsorship
    """
    title = 'Created recently'
    parameter_name: str = 'recent'

    def lookups(self, request, model_admin):
        return (
            ('true', 'Created less than 24 hours ago'),
            ('false', 'Older'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        now = timezone.datetime.now(tz=timezone.utc)
        threshold = now - timezone.timedelta(days=1)
        if value == 'true':
            return queryset.filter(created_at__gte=threshold)
        elif value == 'false':
            return queryset.filter(created_at__lt=threshold)
        return queryset



class ExpiredFilter(SimpleListFilter):
    """
    This class can be used on any model that inherits from Sponsorship
    """
    title = 'Expired'
    parameter_name: str = 'expired'

    def lookups(self, request, model_admin):
        return (
            ('true', 'Expired'),
            ('false', 'Not expired'),
        )

    def queryset(self, request, queryset):
        value = self.value()
        now = timezone.datetime.now(tz=timezone.utc)
        if value == 'true':
            return queryset.filter(expires_at__lt=now)
        elif value == 'false':
            return queryset.filter(expires_at__gte=now)
        return queryset
