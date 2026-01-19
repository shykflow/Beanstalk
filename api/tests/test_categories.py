import colorama
from requests.exceptions import ConnectionError

from api.models import (
    CategoryMapping,
    CustomCategory,
)
from api.testing_overrides import GlobalTestCredentials
from lf_service.category import Category, LifeFrameCategoryService
from lf_service.util import LifeFrameUtilService
from . import disable_logging, SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    should_test_categories: bool
    categories: list[Category]
    category_mapping_black: CategoryMapping
    category_mapping_white: CategoryMapping
    category_mapping_red: CategoryMapping
    category_mapping_green: CategoryMapping
    category_mapping_blue: CategoryMapping

    def setUpTestData():
        try:
            # LifeFrame must be able to be communicated with
            response = LifeFrameUtilService().healthcheck()
            if response.status_code != 200:
                raise ConnectionError
        except ConnectionError:
            Test.should_test_categories = False
            color = colorama.Fore.LIGHTYELLOW_EX
            bright = colorama.Style.BRIGHT
            reset = colorama.Style.RESET_ALL
            msg = 'Could not get a response from LifeFrame, ' + \
                'CategoryMapping testing will be skipped.'
            print(f'\n{bright}{color}{msg}{reset}')
            return
        category_ids = [1, 2, 3, 4, 5]
        unknown_category_ids: list[int]
        try:
            # LifeFrame must have at least categories with ids 1, 2, 3, 4, 5
            Test.categories, unknown_category_ids = LifeFrameCategoryService() \
                .list(category_ids)
            if len(unknown_category_ids) > 0:
                raise Exception()
        except:
            Test.should_test_categories = False
            color = colorama.Fore.LIGHTYELLOW_EX
            bright = colorama.Style.BRIGHT
            reset = colorama.Style.RESET_ALL
            print()
            print(f'{bright}{color}'
                'Warning: '
                f'Checked for ids {category_ids} - '
                f'Could not find {unknown_category_ids}. '
                'CategoryMapping tests will be skipped.'
                f'{reset}')
            return

        Test.should_test_categories = True
        Test.category_mapping_black = CategoryMapping.objects.create(
            category_id=1,
            show_in_picker=True,
            background_color='#000000')
        Test.category_mapping_white = CategoryMapping.objects.create(
            category_id=2,
            show_in_picker=True,
            text_color='#000000',
            background_color='#FFFFFF')
        Test.category_mapping_red = CategoryMapping.objects.create(
            category_id=3,
            show_in_picker=False,
            background_color='#FF0000')
        Test.category_mapping_green = CategoryMapping.objects.create(
            category_id=4,
            show_in_picker=False,
            background_color='#00FF00')
        Test.category_mapping_blue = CategoryMapping.objects.create(
            category_id=5,
            show_in_picker=False,
            background_color='#0000FF')


    def setUp(self):
        if not Test.should_test_categories:
            return
        super().setUp()
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {GlobalTestCredentials.token}')


    def test_retrieve_model(self):
        if not Test.should_test_categories:
            return
        category_mappings = {
            'black': Test.category_mapping_black,
            'white': Test.category_mapping_white,
            'red': Test.category_mapping_red,
            'green': Test.category_mapping_green,
            'blue': Test.category_mapping_blue,
        }
        resource = '/categories/'
        for key, cm in category_mappings.items():
            endpoint = f'{resource}{cm.id}/'
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            data = response.data
            self.assertEqual(data['category_id'],      cm.category_id,      msg=key)
            self.assertEqual(data['show_in_picker'],   cm.show_in_picker,   msg=key)
            self.assertEqual(data['text_color'],       cm.text_color,       msg=key)
            self.assertEqual(data['background_color'], cm.background_color, msg=key)
            self.assertEqual(data['sponsorship'],      cm.sponsorship,      msg=key)


    def test_from_category_id(self):
        if not Test.should_test_categories:
            return
        category_mappings = {
            'black': Test.category_mapping_black,
            'white': Test.category_mapping_white,
            'red': Test.category_mapping_red,
            'green': Test.category_mapping_green,
            'blue': Test.category_mapping_blue,
        }
        resource = '/categories/from_category_id/'
        for key, cm in category_mappings.items():
            endpoint = f'{resource}?id={cm.id}'
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            data = response.data
            self.assertEqual(data['category_id'],      cm.category_id,      msg=key)
            self.assertEqual(data['show_in_picker'],   cm.show_in_picker,   msg=key)
            self.assertEqual(data['text_color'],       cm.text_color,       msg=key)
            self.assertEqual(data['background_color'], cm.background_color, msg=key)
            self.assertEqual(data['sponsorship'],      cm.sponsorship,      msg=key)


    @disable_logging
    def test_invalid_relevant(self):
        if not Test.should_test_categories:
            return
        with self.assertRaises(ValueError):
            self.client.get('/category/relevant/?limit=abc123')


    def test_picker(self):
        if not Test.should_test_categories:
            return
        response = self.client.get('/category/picker/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 2)

        self.assertEqual(response.data[0]['category_id'], 1)
        self.assertTrue(response.data[0]['show_in_picker'])
        self.assertEqual(response.data[0]['text_color'], '#FFFFFF')
        self.assertEqual(response.data[0]['background_color'], '#000000')

        self.assertEqual(response.data[1]['category_id'], 2)
        self.assertTrue(response.data[1]['show_in_picker'])
        self.assertEqual(response.data[1]['text_color'], '#000000')
        self.assertEqual(response.data[1]['background_color'], '#FFFFFF')


    def test_search(self):
        if not Test.should_test_categories:
            return
        # No phrase provided should 400
        response = self.client.get('/category/search/')
        self.assertEqual(response.status_code, 400)

        # Empty string phrase should 400
        phrase = ''
        response = self.client.get(f'/category/search/?phrase={phrase}')
        self.assertEqual(response.status_code, 400)

        # White space phrase should 400
        phrase = ' \n  \t '
        response = self.client.get(f'/category/search/?phrase={phrase}')
        self.assertEqual(response.status_code, 400)

        # Exact name of the category phrase should 200 and return at least one category mapping
        phrase = Test.categories[0].name
        response = self.client.get(f'/category/search/?phrase={phrase}')
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(response.data['category_mappings'], [])
        category_ids = [
            c['category_id']
            for c in response.data['category_mappings']
        ]
        self.assertIn(Test.categories[0].id, category_ids)

        # Similar search should return both category mappings and custom categories
        custom = CustomCategory.objects.create(name=Test.categories[0].name + 'a')
        response = self.client.get(f'/category/search/?phrase={phrase}')
        self.assertEqual(response.status_code, 200)
        category_ids = [
            c['category_id']
            for c in response.data['category_mappings']
        ]
        self.assertIn(Test.categories[0].id, category_ids)
        self.assertIn(custom.name, response.data['custom_categories'])
