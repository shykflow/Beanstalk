from django.contrib import admin
from django.contrib.postgres.fields import ArrayField
from django.db.models import (
    CharField,
    ImageField,
    PositiveIntegerField,
    TextField,
)
from django.utils.safestring import mark_safe

from sponsorship.models.abstract import Sponsorship
from api.validators import non_zero_validator


class CategorySponsorship(Sponsorship):
    category_id = PositiveIntegerField()
    image = ImageField(max_length=1000, blank=True, null=True,
        upload_to='category_sponsorships',
        help_text='Image that will replace the category image in the app while this sponsorship is active')
    details = CharField(max_length=500, blank=True, null=True,
        help_text='Text that will show up above the category\'s details in the app while this sponsorship is active')
    experience_ids = ArrayField(
        PositiveIntegerField(validators=[non_zero_validator]),
        blank=True,
        null=True,
        help_text='Comma separated Challenge IDs, for example: 100,156,4954')
    cost = PositiveIntegerField(blank=True, null=True,
        help_text='In pennies, for example: $10.00 = 1000')
    notes = TextField(max_length=5000, blank=True, null=True,
        help_text='This field is for admin note taking, will not show in the app')

    def get_name(self) -> str | None:
        if self.category_id is None:
            return None
        # avoid circular import
        from api.utils.life_frame_category import CategoryGetter
        category = CategoryGetter().retrieve(self.category_id)
        return category.name

    @admin.display(
        description='Category Name')
    def admin_name(self):
        if self.category_id is None:
            return '(Set a Category ID and save to see the name)'
        name = self.get_name()
        html = f"""
            <p>{name}</p>
            <p style="font-size: 0.75em;">(cached for 15 min)</p>
        """
        return mark_safe(html)

    @admin.display(
        description='Image')
    def admin_image(self):
        if not bool(self.image):
            return mark_safe('<p>No image</p>')
        return mark_safe(f'<img src="{self.image.url}" width="75">')

    def __str__(self):
        return f'Category ID: {self.category_id} - {self.user}'
