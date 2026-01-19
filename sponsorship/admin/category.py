from django.contrib import admin
from django.utils import timezone
from django.utils.safestring import mark_safe

from api.admin.admin_site import AppAdminSite
from sponsorship.models import (
    CategorySponsorship,
)
from sponsorship.admin.list_filters import (
    CreatedRecentlyFilter,
    ExpiredFilter,
)

class CategorySponsorshipAdmin(admin.ModelAdmin):
    fields = (
        'user',
        'category_id',
        'expires_at',
        'image',
        'details',
        'experience_ids',
        'cost',
        'notes',
    )
    search_fields = (
        'user__username',
        'user__email',
        'category_id',
    )
    list_display = (
        'category_id',
        'admin_name',
        'details',
        'admin_image',
        'user',
        'created_at',
        'expires_at',
        'experience_ids',
        'cost',
        'notes',
        '_expired',
    )
    raw_id_fields = (
        'user',
    )
    list_filter = (
        CreatedRecentlyFilter,
        ExpiredFilter,
    )

    def _expired(self, sponsorship: CategorySponsorship):
        now = timezone.datetime.now(tz=timezone.utc)
        expires_at = sponsorship.expires_at
        expired = expires_at is not None and expires_at < now
        if expired:
            return mark_safe('<span style="color: red;">Expired</span>')
        return None
    _expired.admin_order_field = 'expires_at'

admin.site.register(CategorySponsorship, CategorySponsorshipAdmin, site=AppAdminSite)
