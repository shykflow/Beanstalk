from django.contrib import admin
from django.utils.safestring import SafeText

class AdminMentionsHtml:
    @admin.display(
        description='Mentions')
    def admin_mentions_html(self):
        if not hasattr(self, 'mentions'):
            return SafeText('No mentions on this object')
        mentions = self.mentions.all()
        if not mentions.exists():
            html = 'No mentions'
        else:
            html = "<br>".join([f'{u.id} - {u.username}' for u in mentions])
        return SafeText(html)
