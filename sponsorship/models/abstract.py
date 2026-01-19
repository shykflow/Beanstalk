from django.db.models import (
    CASCADE,
    DateTimeField,
    ForeignKey,
    Model,
)

class Sponsorship(Model):
    class Meta:
        abstract = True
    user = ForeignKey('api.User', on_delete=CASCADE)
    created_at = DateTimeField(auto_now_add=True)
    expires_at = DateTimeField(null=True, blank=True)
