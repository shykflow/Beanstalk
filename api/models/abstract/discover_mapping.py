from uuid import uuid4
from django.contrib import admin
from django.db import models
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.safestring import mark_safe

from api.validators import is_uuid4
from api.utils.file_handling import split_file_url

class DiscoverMapping(models.Model):
    class Meta:
        abstract = True
    overlay_opacity = models.FloatField(
        default=0.2,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
        help_text=" ".join([
            'White panel between the background image/color and the text.',
            '(Must be a number between 0 and 1)',
        ]))
    text_color = models.CharField(
        max_length=7,
        default="#FFFFFF",
         help_text=" ".join([
            'Hex color - Defaults black if blank and no background image,'
            'white if blank and has background image',
        ]))
    background_color = models.CharField(
        max_length=7,
        null=True,
        blank=True,
        help_text=" ".join([
            'Hex color - Defaults white if blank or invalid color',
        ]))

    @admin.display(
        description='Text color')
    def admin_text_color(self):
       return self._color_text_and_dot(self.text_color)


    @admin.display(
        description='Background color')
    def admin_background_color(self):
       return self._color_text_and_dot(self.background_color)

    @property
    def _admin_preview_text(self) -> str:
        raise NotImplementedError('Must be implemented in subclasses')


    @admin.display(
        description='Preview')
    def admin_preview(self):
        container_background_color = 'white'
        image_background = 'none'
        image_display = 'none'
        text_color = 'black'
        width = 100
        height = width * 0.7

        if bool(self.image):
            image_display = "initial"
            image_background = f"url('{self.image.url}')"
            text_color = "white"
        elif self.background_color is not None:
            container_background_color = self.background_color
            text_color = "white"
        if self.text_color is not None:
            text_color = self.text_color
        container_styles = [
            'position: relative;'
            f'width: {width}px;',
            f'height: {height}px;',
            'border-radius: 6px;',
            'overflow: hidden;',
            'box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.6);',
            f"background-color: {container_background_color}"
        ]
        image_styles = [
            'position: absolute;',
            'top: 0;',
            'left: 0;',
            f'display: {image_display};',
            'width: 100%;',
            'height: 100%;',
            'background-size: cover;',
            'background-position: center;',
            f"background-image: {image_background};",
        ]
        overlay_styles = [
            'position: absolute;',
            'top: 0;',
            'left: 0;',
            'width: 100%;',
            'height: 100%;',
            f'background-color: rgba(160, 160, 160, {self.overlay_opacity})'
        ]
        text_styles = [
            'position: absolute;',
            f'color: {text_color};'
            'font-weight: bolder;',
            'text-align: center;',
            'margin: 0;',
            'padding: 0;',
            'opacity: 1;',
            'top: 50%;',
            'left: 50%;',
            'transform: translate(-50%,-50%);',
            'text-shadow: 1px 1px 1px #000000;',
        ]
        html = f'''
            <div style="{''.join(container_styles)}">
                <div style="{''.join(image_styles)}"></div>
                <div style="{''.join(overlay_styles)}"></div>
                <p style="{''.join(text_styles)}">
                    {self._admin_preview_text}
                </p>
            </div>
        '''
        return mark_safe(html)

    def _color_text_and_dot(self, color):
        div_styles = [
            'display: flex;',
            'flex-direction: row;',
            'justify-content: flex-start;',
        ]
        dot_styles = [
            'border: 1px solid #b5b5b5;',
            'border-radius: 20px;',
            'width: 20px;',
            'height: 20px;',
        ]
        if not bool(color):
            dot_styles.append('background-color: white;')
        else:
            dot_styles.append(f'background-color: {color};')
        text = 'Not Set'
        if color is not None:
            text = color
        html = f"""
            <div style="{''.join(div_styles)}">
                <div style="{''.join(dot_styles)}">&nbsp;</div>
                <p>{text}</p>
            </div>
        """
        return mark_safe(html)

    # override
    def save(self, *args, **kwargs):
        """Enforce a unique name for `image`."""
        if bool(self.image):
            image_url = split_file_url(self.image.name)
            if image_url is None or not is_uuid4(image_url['name']):
                self.image.name = f"{uuid4()}.{image_url['extension']}"
        super().save(*args, **kwargs)
