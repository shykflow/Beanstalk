from django.db.models import (
    DateTimeField,
    Model,
)

class Schedule(Model):
    class Meta:
        abstract = True
    publish_at = DateTimeField(db_index=True,
        help_text="Treat this like the user's local time. If set to 1pm, will " + \
            "go live at 1pm for every user no matter where they are in the world")
