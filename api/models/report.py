from django.forms import ValidationError
from django.db.models import (
    BooleanField,
    CASCADE,
    CharField,
    DateTimeField,
    ForeignKey,
    Model,
    PositiveSmallIntegerField,
)

from api.enums import ReportType

class Report(Model):
    created_by = ForeignKey('User', blank=True, null=True, on_delete=CASCADE, related_name='created_reports')
    offender = ForeignKey('User', on_delete=CASCADE, related_name='offending_reports')
    created_at = DateTimeField(auto_now_add=True)
    type = PositiveSmallIntegerField(choices=ReportType.choices)
    details = CharField(max_length=5000, blank=True, null=True)
    cron_emailed = BooleanField(default=False)
    acknowledged = BooleanField(default=False)

    # Content Types - if all blank this report is about the offender directly.
    playlist = ForeignKey('Playlist', on_delete=CASCADE, null=True, blank=True)
    experience = ForeignKey('Experience', on_delete=CASCADE, null=True, blank=True)
    post = ForeignKey('Post', on_delete=CASCADE, null=True, blank=True)
    comment = ForeignKey('Comment', on_delete=CASCADE, null=True, blank=True)

    def __str__(self):
        return f'{self.created_by} → {self.offender}'

    def clean(self):
        super().clean()
        Report.validate(self.__dict__)

    @staticmethod
    def validate(data: dict):
        from api.models import (
            Playlist,
            Experience,
            Comment,
            Post,
            User,
        )
        """
        expects a dictionary like this:
        {
            'offender': 123,
            'type': ReportType.ABUSIVE_CONTENT,
            'details': None,
            'playlist': None,
            'experience': None,
            'post': None,
            'comment': 456,
        }
        """
        _type = data.get('type')
        details = data.get('details')
        if _type == ReportType.OTHER and (details is None or details.strip() == ''):
            raise ValidationError(f'If report type is OTHER details must be provided')

        # Can only report on 0 or 1 content ids
        # (0 content ids means this report is on the offender directly)
        content = [
            data.get('playlist'),
            data.get('experience'),
            data.get('post'),
            data.get('comment'),
        ]
        content = [x for x in content if x is not None]
        if len(content) > 1:
            msg = 'Cannot report on more than 1 type of content'
            raise ValidationError(msg)

        # Fallback to _id because admin forms return the raw ids
        _created_by = data.get('created_by', data.get('created_by_id'))
        created_by: User
        if type(_created_by) is User:
            created_by = _created_by
        elif type(_created_by) is int:
            created_by = User.objects.get(id=_created_by)
        elif type(_created_by) is str:
            created_by = User.objects.get(id=int(_created_by))
        else:
            raise ValidationError('Cannot identify the created_by from provided attributes')

        # Fallback to _id because admin forms return the raw ids
        _offender = data.get('offender', data.get('offender_id'))
        offender: User
        if type(_offender) is User:
            offender = _offender
        elif type(_offender) is int:
            offender = User.objects.get(id=_offender)
        elif type(_offender) is str:
            offender = User.objects.get(id=int(_offender))
        else:
            raise ValidationError('Cannot identify the offender from provided attributes')

        if created_by == offender:
            raise ValidationError('A user cannot report themselves or their own content')

        content_checks = [
            { 'type_key': 'playlist',    'class': Playlist   },
            { 'type_key': 'experience',  'class': Experience },
            { 'type_key': 'post',        'class': Post       },
            { 'type_key': 'comment',     'class': Comment    },
        ]

        # If this report is not on the offender directly,
        # the offender must be the creator of the content
        for content_check_dict in content_checks:
            type_key = content_check_dict['type_key']
            # Fallback to _id because admin forms return the raw ids
            _c = data.get(type_key, data.get(f'{type_key}_id'))
            if _c is not None:
                Class: type = content_check_dict['class']
                c: Class = None
                if type(_c) is Class:
                    c = _c
                elif isinstance(_c, int | str):
                    # Try to use the all_objects manager because
                    # reported content is likely to be soft deleted
                    # but fall back to using the default_manager if all_objects
                    # doesn't exist.
                    manager = getattr(Class, 'all_objects', Class.objects)
                    if type(_c) is int:
                        c = manager.get(id=_c)
                    elif type(_c) is str:
                        c = manager.get(id=int(_c))
                else:
                    raise ValidationError(
                        f'Cannot identify the {type_key} '
                        'from provided attributes')
                if c.created_by != offender:
                    raise ValidationError(
                        f'The {type_key} creator must be the offender')
