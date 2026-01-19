import logging
from django.core.management.base import BaseCommand

from .helpers import REGEX
from api.models import Experience
from api.utils import commands

logger = logging.getLogger('app')

class Command(BaseCommand):

    def handle(self, *args, **options):
        base_qs = Experience.objects \
            .filter(geo_tag__isnull=False) \
            .filter(latitude__isnull=True) \
            .filter(longitude__isnull=True)

        # geo_lat_long_can_adapt matches should have been adapted at this point
        # so they will match geo_lat_long
        lat_long_matches = base_qs.filter(
            geo_tag__iregex=REGEX['geo_lat_long'])
        i = 0
        total_lat_long_matches = lat_long_matches.count()
        lat_long_ids = [x for x in lat_long_matches.values_list('id', flat=True)]
        for id in lat_long_ids:
            exp: Experience = Experience.objects.get(pk=id)
            i += 1
            geo_tag = exp.geo_tag
            try:
                split = geo_tag.split(',')
                latstr = split[0].strip()
                lngstr = split[1].strip()
                exp.latitude = float(latstr)
                exp.longitude = float(lngstr)
                exp.save()
            except Exception as e:
                exp_info = str(exp)[:75].ljust(80)
                msg = f"Converting geo_tag of {exp_info}raised {e}"
                logger.error(msg)
            commands.print_progress(on=i, outof=total_lat_long_matches)

        hour_min_sec_matches = base_qs.filter(
            geo_tag__iregex=REGEX['geo_hour_min_sec'])
        i = 0
        total_hour_min_sec_matches = hour_min_sec_matches.count()
        hour_min_sec_ids = [x for x in hour_min_sec_matches.values_list('id', flat=True)]
        for id in hour_min_sec_ids:
            exp: Experience = Experience.objects.get(pk=id)
            i += 1
            geo_tag = exp.geo_tag
            try:
                split = geo_tag.split()
                lathour = int(split[0][1:]) # Chop off N or S
                latmin = int(split[1])
                latsec = float(split[2])
                longhour = int(split[3][1:]) # Chop off E or W
                longmin = int(split[4])
                longsec = float(split[5])
                exp.latitude = convert_to_decimal(lathour, latmin, latsec)
                exp.longitude = convert_to_decimal(longhour, longmin, longsec)
                exp.save()
            except Exception as e:
                exp_info = str(exp)[:75].ljust(80)
                msg = f"Converting geo_tag of {exp_info}raised {e}"
                logger.error(msg)
            commands.print_progress(on=i, outof=total_hour_min_sec_matches)

        degree_quote_matches = base_qs.filter(
            geo_tag__iregex=REGEX['geo_degree_quote'])
        i = 0
        total_degree_quote_matches = degree_quote_matches.count()
        degree_quote_ids = [x for x in degree_quote_matches.values_list('id', flat=True)]
        for id in degree_quote_ids:
            exp: Experience = Experience.objects.get(pk=id)
            i += 1
            geo_tag = exp.geo_tag
            try:
                cut_position = geo_tag.find('N')
                if cut_position == -1:
                    cut_position = geo_tag.find('n')
                if cut_position == -1:
                    cut_position = geo_tag.find('S')
                if cut_position == -1:
                    cut_position = geo_tag.find('s')
                latpart, longpart = geo_tag[:cut_position], geo_tag[cut_position+1:]
                first_degree_pos = latpart.find('°')
                latdeg = float(latpart[:first_degree_pos])
                latpart = latpart[first_degree_pos+1:]
                first_single_quote_position = latpart.find('′')
                latmin = 0
                if first_single_quote_position != -1:
                    latmin = float(latpart[:first_single_quote_position])
                    latpart = latpart[first_single_quote_position+1:]
                first_double_quote_position = latpart.find('″')
                latsec = 0
                if first_double_quote_position != -1:
                    latsec = float(latpart[:first_double_quote_position])
                if (longpart[0] == ','):
                    longpart = longpart[1:] # Chop off optional ,
                longpart.strip()
                second_degree_pos = longpart.find('°')
                longdeg = float(longpart[:second_degree_pos])
                longpart = longpart[second_degree_pos+1:]
                second_single_quote_position = longpart.find('′')
                longmin = 0
                if second_single_quote_position != -1:
                    longmin = float(longpart[:second_single_quote_position])
                    longpart = longpart[second_single_quote_position+1:]
                second_double_quote_position = longpart.find('″')
                longsec = 0
                if second_double_quote_position != -1:
                    longsec = float(longpart[:second_double_quote_position])
                exp.latitude = convert_to_decimal(latdeg, latmin, latsec)
                exp.longitude = convert_to_decimal(longdeg, longmin, longsec)
                exp.save()
            except Exception as e:
                exp_info = str(exp)[:75].ljust(80)
                msg = f"Converting geo_tag of {exp_info}raised {e}"
                logger.error(msg)
            commands.print_progress(on=i, outof=total_degree_quote_matches)

def convert_to_decimal(
    degrees_or_hours: int | float, minutes: int | float, seconds: float):
    return degrees_or_hours + (minutes / 60) + (seconds / 3600)
