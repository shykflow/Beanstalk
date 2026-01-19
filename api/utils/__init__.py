import logging
import random

from django.contrib.gis.geos import Point
from django.utils import timezone

logger = logging.getLogger('app')

def random_code(length: int):
    return "".join(random.choice("0123456789") for i in range(length))

def split_ints(value: str | None) -> list[int]:
    if value is None:
        return []
    _value = ''.join(value.split())
    try:
        strs = _value.split(',')
        return [int(x) for x in strs]
    except:
        pass
    return []

def unique_objects(list_one: list[object], list_two: list[object]) -> list[object]:
    """
    Returns a list containing only objects that were not in both lists,
    as determined by their IDs.

    Objects in both lists must have an `id` field.

    Note that a `set` does not work well for objects since they allow multiple objects
    with the same data as long as they are in a different location in memory.
    """
    ids_and_objects = {}
    combined_list = list_one + list_two
    for obj in combined_list:
        if obj.id not in ids_and_objects:
            ids_and_objects[obj.id] = obj
    return list(ids_and_objects.values())

def username_from_email(email:str):
    from api.models.user import User
    i = 1
    base_username = email.split('@')[0]
    base_username = base_username.replace('.', '')
    while True:
        candidate_username = base_username if i == 1 else f'{base_username}{i}'
        taken = User.objects \
            .filter(username=candidate_username) \
            .exists()
        if not taken:
            return candidate_username
        i += 1
        if i > 1_000_000:
            raise Exception(f'Could not find a unique candidate username for email: {email}')

def validate_start_and_end_dts(start: timezone.datetime, end: timezone.datetime):
    now = timezone.datetime.now(tz=timezone.utc)
    if start is None and end is None:
        return
    if end is not None and end < now:
        raise Exception('End date must be in the future.')
    if start is not None and end is not None and start > end:
        raise Exception('End date must be after start date.')

def update_experience_latlong_one_to_one_ref(experience):
    from api.models import Experience, ExperienceLatLong
    # Note: GeoDjango documentation says Point(longitude, latitude), in that order
    # Note: srid=4326 ensures the point is stored using WGS84,
    #       the most common coordinate system for latitude and longitude.
    instance: Experience = experience
    exp_location = ExperienceLatLong.objects \
        .filter(experience=instance) \
        .first()
    if exp_location is None:
        if instance.latitude is not None and instance.longitude is not None:
            logger.info(f'- Experience {instance.id} got a point set')
            point = Point(instance.longitude, instance.latitude, srid=4326)
            ExperienceLatLong.objects.create(
                experience=instance,
                point=point)
        return
    if instance.latitude is None or instance.longitude is None:
        logger.info(f'- Experience {instance.id} lost its lat/long info')
        exp_location.delete()
        return
    exp_point: Point = exp_location.point
    long, lat = exp_point.coords
    if instance.latitude != lat or instance.longitude != long:
        logger.info(f'- Experience {instance.id} lat or long changed')
        exp_location.point = Point(instance.longitude, instance.latitude, srid=4326)
        exp_location.save()