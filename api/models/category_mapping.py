from django.db.models import (
    BooleanField,
    CharField,
    ForeignKey,
    IntegerField,
    ImageField,
    SET_NULL,
)
from django.contrib import admin
from django.utils import timezone
from django.utils.safestring import mark_safe

from api.models.abstract.discover_mapping import DiscoverMapping


class CategoryMapping(DiscoverMapping):
    category_id = IntegerField(unique=True)
    show_in_picker = BooleanField()
    picker_sequence = IntegerField(blank=True, null=True)
    image = ImageField(upload_to='category_mappings', max_length=1000, blank=True, null=True)
    sponsorship = ForeignKey('sponsorship.CategorySponsorship', blank=True, null=True, on_delete=SET_NULL)
    details = CharField(max_length=2000, blank=True, null=True,
        help_text='Shows on the category contents page in the app')

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


    @admin.display(
        description='Sponsorship status')
    def admin_sponsorship_status_small(self):
        return self._admin_sponsorship_status_html(small=True)

    @admin.display(
        description='Sponsorship status')
    def admin_sponsorship_status_large(self):
        return self._admin_sponsorship_status_html(small=False)

    def _admin_sponsorship_status_html(self, small: bool):
        sponsorship_status = self._sponsorship_status()
        html = ''
        if sponsorship_status['sponsorship_set']:
            issues = []
            if not sponsorship_status['category_ids_match']:
                issues.append('Category IDs do not match')
            if sponsorship_status['expired']:
                issues.append('Expired')
            if len(issues) == 0:
                html += 'Active'
            else:
                li_styles = [
                    'list-style: disc outside none;',
                    'display: list-item;',
                    'color: red;',
                    'font-weight: bold;',
                ]
                html += 'Issues:'
                html += '<ul style="padding: 0; margin: 0; list-style-type: disc;">'
                issues = [
                    f'<li style="{" ".join(li_styles)}">{x}</li>' for x in issues]
                html += ''.join(issues)
                html += '</ul>'
                html += '<br>This sponsorship will not show in the app!'
        else:
            html += "" if small else "Not Sponsored"
        if small:
            return mark_safe(html)
        return mark_safe(f'<h1 style="font-weight: bold;">{html}</h1>')

    def _sponsorship_status(self) -> dict[str, any]:
        from sponsorship.models import CategorySponsorship
        sponsorship: CategorySponsorship = self.sponsorship
        data = {
            'sponsorship_set': False,
            'category_ids_match': None,
            'expired': None,
        }
        if sponsorship is None:
            return data
        data['sponsorship_set'] = True
        data['category_ids_match'] = self.category_id == sponsorship.category_id
        now = timezone.datetime.now(tz=timezone.utc)
        expires_at = sponsorship.expires_at
        data['expired'] = expires_at is not None and expires_at < now
        return data


    @admin.display(
        description='Sponsorship details')
    def admin_sponsorship_info(self):
        from sponsorship.models import CategorySponsorship
        sponsorship: CategorySponsorship = self.sponsorship
        if sponsorship is None:
            return None
        html = ''
        image_html = 'No image'
        if bool(sponsorship.image):
            image_html = f'<img src="{sponsorship.image.url}" width="75">'
        experience_ids = sponsorship.experience_ids \
            if sponsorship.experience_ids is not None \
            else []
        experience_ids_html = 'No experiences'
        if len(experience_ids) > 0:
            experience_ids_html = ', '.join(map(str, experience_ids))
        cost_html = '(no cost)'
        if sponsorship.cost is not None and sponsorship.cost > 0:
            cost_html = f'{sponsorship.cost} (in pennies)'
        notes_html = '(no notes)'
        if sponsorship.notes is not None:
            notes_stripped = sponsorship.notes.strip()
            if notes_stripped != '':
                notes_html = notes_stripped
        html += f"""
            <table>
                <thead>
                    <tr>
                        <th>Attribute</th>
                        <th>Value</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>User</td>
                        <td>
                            @{sponsorship.user.username}<br>
                            {sponsorship.user.email}
                        </td>
                    </tr>
                    <tr>
                        <td>Category ID</td>
                        <td>{sponsorship.category_id}</td>
                    </tr>
                    <tr>
                        <td>Created at</td>
                        <td>{sponsorship.created_at}</td>
                    </tr>
                    <tr>
                        <td>Expires at</td>
                        <td>{sponsorship.expires_at}</td>
                    </tr>
                    <tr>
                        <td>Image</td>
                        <td>{image_html}</td>
                    </tr>
                    <tr>
                        <td>Details</td>
                        <td>{sponsorship.details}</td>
                    </tr>
                    <tr>
                        <td>Experience IDs</td>
                        <td>{experience_ids_html}</td>
                    </tr>
                    <tr>
                        <td>Cost</td>
                        <td>{cost_html}</td>
                    </tr>
                    <tr>
                        <td>Notes</td>
                        <td>{notes_html}</td>
                    </tr>
                </tbody>
            </table>
        """
        return mark_safe(html)

    @property
    def _admin_preview_text(self) -> str:
        return self.get_name() or ''

    def __str__(self):
        return str(self.category_id)
