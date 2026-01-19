from django.db.models import (
    CASCADE,
    Model,
    OneToOneField,
)

class ManagedUser(Model):
    user = OneToOneField('api.User', unique=True, on_delete=CASCADE)

    def __str__(self):
        return str(self.user)
