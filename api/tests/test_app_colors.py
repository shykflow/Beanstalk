from api.models import AppColor
from . import SilenceableAPITestCase

class Test(SilenceableAPITestCase):
    black: str
    white: str
    red: str
    green: str
    blue: str

    def setUpTestData():
        Test.black = AppColor.objects.create(color='#000000').color
        Test.white = AppColor.objects.create(color='#FFFFFF').color
        Test.red = AppColor.objects.create(color='#FF0000').color
        Test.green = AppColor.objects.create(color='#00FF00').color
        Test.blue = AppColor.objects.create(color='#0000FF').color

    def setUp(self):
        super().setUp()

    def test_app_colors(self):
        response = self.client.get('/app_colors/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 5)
        self.assertIn(Test.black, response.data)
        self.assertIn(Test.white, response.data)
        self.assertIn(Test.red, response.data)
        self.assertIn(Test.green, response.data)
        self.assertIn(Test.blue, response.data)
