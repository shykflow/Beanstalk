from django.db import models

class PubliclyViewable(models.Model):
    class Meta:
        abstract = True

    publicly_viewable = models.BooleanField(default=True,
        help_text='If unchecked, ' + \
            'this content will be remove from being searched, queried, completed, etc.')
    not_publicly_viewable_reason = models.CharField(max_length=5000, null=True, blank=True,
        help_text="Be professional, the creator of this content may see this reason. " + \
                  "If they are able to fix the issue, we may enable publicly_viewable")
