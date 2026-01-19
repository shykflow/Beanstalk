import datetime
from django.db import models
from django.utils import timezone

class StartEndTimeModel(models.Model):
    start_time = models.DateTimeField(null=True, blank=True,
        help_text="If the exact time of day is not needed, set time to midnight 00:00:00,\
            and check 'Start time date only'. Time is saved in UTC.")
    end_time = models.DateTimeField(null=True, blank=True,
        help_text="If the exact time of day is not needed, set time to midnight 00:00:00,\
            and check 'End time date only, Time is saved in UTC.")
    start_time_date_only = models.BooleanField(default=True)
    end_time_date_only = models.BooleanField(default=True)
    use_local_time = models.BooleanField(default=True,
        help_text="Checked: different, relative timezone's 1pm based on user location. Unchecked: Exactly 1pm UTC.")

    def valid_completion_time(self, minutes_offset: int) -> bool:
        finishing_time: datetime
        start = self.start_time
        end = self.end_time
        if self.use_local_time:
            finishing_time = timezone.now() + datetime.timedelta(minutes=float(minutes_offset))
        else:
            finishing_time = timezone.now()

        if self.start_time_date_only and start is not None:
                start = datetime.datetime.combine(date=self.start_time.date(), time=datetime.time(0), tzinfo=timezone.utc)
        if self.end_time_date_only and end is not None:
                end = datetime.datetime.combine(date=self.end_time.date(), time=datetime.time(0), tzinfo=timezone.utc)

        outOfTimeBounds = start is not None \
            and finishing_time < start
        outOfTimeBounds = outOfTimeBounds or (end is not None \
            and finishing_time > end)
        return not outOfTimeBounds

    class Meta:
        abstract = True

        # This constraint cannot be inherited and must be put directly on the model
        # constraints = [
        #     models.CheckConstraint(
        #         check= Q(start_time=None) | Q(end_time=None) | Q(start_time__lt=F('end_time')),
        #         name='start_before_end')
        # ]
