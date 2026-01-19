import colorama
import random

from lf_service.util import LifeFrameUtilService
from lf_service import LifeFrameException, LifeFrameUserIDRequiredError
from lf_service.category import LifeFrameCategoryService
from lf_service.user import LifeFrameUserService, LifeFrameUser

from api.tests import SilenceableAPITestCase

# Notes on the difference between setUpTestData() and setUp()
# https://stackoverflow.com/questions/29428894/django-setuptestdata-vs-setup

class Test(SilenceableAPITestCase):
    """
    This tests what will eventually be moved to the LifeFrame
    library for other organizations to use in their python projects
    when it is created.
    """
    # silent = False

    can_test: bool = True
    util_service = LifeFrameUtilService()
    user_service = LifeFrameUserService()
    category_service = LifeFrameCategoryService()
    lf_user: LifeFrameUser

    def setUpTestData():
        color = colorama.Fore.LIGHTYELLOW_EX
        bright = colorama.Style.BRIGHT
        reset = colorama.Style.RESET_ALL
        try:
            response = Test.util_service.healthcheck()
        except:
            _msg = [
                '\nCould not get a response from LifeFrame,',
                'LifeFrame method testing will be skipped.'
            ]
            msg = ' '.join(_msg)
            print(f'{bright}{color}{msg}{reset}')
            Test.can_test = False
        if not Test.can_test:
            return
        try:
            response = Test.util_service.check_api_key()
            assert response.status_code == 200
        except:
            _msg = [
                'Bad LifeFrame api key,',
                'LifeFrame method testing will be skipped.'
            ]
            msg = ' '.join(_msg)
            print(f'{bright}{color}{msg}{reset}')
            Test.can_test = False
        if not Test.can_test:
            return

        # Build a user and insert some activities for them
        Test.lf_user = Test.user_service.create()
        categories = Test.category_service.random(limit=20)
        if len(categories) == 0:
            Test.can_test = False
        if not Test.can_test:
            return
        for i in range(10):
            add_more_categories = True
            # Get random categories to add to this experience.
            # Will always insert at least 1.
            activity_category_ids = []
            while add_more_categories:
                exp_category_id_to_add = random.choice(categories).id
                if exp_category_id_to_add not in activity_category_ids:
                    activity_category_ids.append(exp_category_id_to_add)
                if random.randint(0, 1) == 1:
                    add_more_categories = False
            Test.category_service.record_activity(
                lifeframe_id=Test.lf_user.id,
                categories=activity_category_ids)

    def setUp(self):
        super().setUp()

    def test_category_search_fail_cases(self):
        if not Test.can_test:
            return
        exception = None
        try:
            Test.category_service.search(phrase=None)
        except LifeFrameException as e:
            exception = e
        assert exception is not None


    def test_category_search(self):
        if not Test.can_test:
            return
        categories = Test.category_service.search('doggy')
        assert type(categories) is list
        categories = Test.category_service.search('doggy', threshold=0.2)
        assert type(categories) is list


    def test_category_popular(self):
        if not Test.can_test:
            return
        response_data = Test.category_service.popular()
        category_groups = response_data['category_groups']
        categories = response_data['categories']
        assert type(category_groups) is list
        assert type(categories) is list
        categories = Test.category_service.popular(limit=100)
        category_groups = response_data['category_groups']
        categories = response_data['categories']
        assert type(category_groups) is list
        assert type(categories) is list
        categories = Test.category_service.popular(org_activities_only=False)
        category_groups = response_data['category_groups']
        categories = response_data['categories']
        assert type(category_groups) is list
        assert type(categories) is list


    def test_category_relevant(self):
        if not Test.can_test:
            return
        response_data = Test.category_service.relevant(
            life_frame_id=Test.lf_user.id)
        category_groups = response_data['category_groups']
        categories = response_data['categories']
        assert type(category_groups) is list
        assert type(categories) is list


    def test_relevant_fail_cases(self):
        if not Test.can_test:
            return
        exception = None
        try:
            Test.category_service.relevant(life_frame_id=None)
        except LifeFrameUserIDRequiredError as e:
            exception = e
        assert exception is not None
