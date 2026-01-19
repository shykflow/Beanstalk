from django.db.models import (
  CharField,
  DateField,
  ForeignKey,
  IntegerField,
  JSONField,
  Model,
)
from django.db.models.deletion import CASCADE

from api.enums import DeviceOS



class Device(Model):
  user = ForeignKey('User', on_delete=CASCADE)
  token = CharField(max_length=500)
  details = JSONField(blank=True, null=True)
  last_check_in = DateField(auto_now_add=True)
  minutes_offset = IntegerField(blank=True, null=True)
  os = IntegerField(choices=DeviceOS.choices, default=None, blank=True, null=True)

  def __str__(self):
    return f'user: {self.user.username} | device_id: {self.id}'
