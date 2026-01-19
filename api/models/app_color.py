from django.contrib import admin
from django.db import models
from django.utils.safestring import mark_safe

class AppColor(models.Model):
    color = models.CharField(max_length=7)

    @admin.display(
        description='Preview')
    def admin_preview(self):
        styles = [
            f'background-color: {self.color};'
            'width: 100px;',
            'height: 80px;',
        ]
        html = f'''
            <div>
                <div style="{' '.join(styles)}"></div>
                <p>{self.color}</p>
            </div>
        '''
        return mark_safe(html)

    def __str__(self):
        return self.color
