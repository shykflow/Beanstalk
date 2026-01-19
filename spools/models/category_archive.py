from django.db.models import (
    Model,
    PositiveIntegerField,
)

class CategoryArchiveSpool(Model):
    category_id = PositiveIntegerField()
    change_to = PositiveIntegerField(blank=True, null=True)

    def __str__(self):
        return f"Category Archive {self.category_id} → {self.change_to}"
