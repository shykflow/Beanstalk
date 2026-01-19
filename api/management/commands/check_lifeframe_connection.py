from django.core.management.base import BaseCommand
import logging

from lf_service.util import LifeFrameUtilService

logger = logging.getLogger('app')

class Command(BaseCommand):
    def handle(self, *args, **options):
        lf_util_service = LifeFrameUtilService()
        try:
            logger.info('\nLifeFrame Health Check')
            response = lf_util_service.healthcheck()
            logger.info("Response:", )
            logger.info(f"  Status: {response.status_code}")
            logger.info(f"  Reason: {response.reason}")
        except:
            logger.info('Could not get a response from LifeFrame')

        try:
            logger.info('\nLifeFrame Api Key Check')
            response = lf_util_service.check_api_key()
            logger.info("Response:", )
            logger.info(f"  Status: {response.status_code}")
            logger.info(f"  Reason: {response.reason}")
        except Exception as e:
            logger.info(str(e))
        logger.info('\n')
