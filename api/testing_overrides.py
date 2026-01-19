from django.conf import settings
from rest_framework.authtoken.models import Token
from api.decorators import static_property
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.core.cache import cache

from api.models.user import User
from lf_service.models import (
    Category,
    CategoryGroup,
)

class MockTwilioMessageInstance:
    pass


class TestingFileSystemStorage(FileSystemStorage):
    def __init__(self, *args, **kwargs):
        kwargs['location'] = f'{settings.BASE_DIR}/api/tests/tmp'
        super().__init__(*args, **kwargs)


class GlobalTestCredentials:
    _user: User = None
    _token: Token = None

    @static_property
    def user() -> User:
        if not settings.TESTING:
            raise Exception('Cannot use this user in ')
        return GlobalTestCredentials._user

    @static_property
    def token() -> Token:
        if not settings.TESTING:
            raise Exception('Cannot use this user in ')
        return GlobalTestCredentials._token

    @staticmethod
    def initialize():
        user, _ = User.objects.get_or_create(
            username='global',
            email='global@email.com',
            email_verified=True,
            name="Global Test User")
        GlobalTestCredentials._user = user
        token, _ = Token.objects.get_or_create(
            user=user)
        GlobalTestCredentials._token = token


class LifeFrameCategoryOverrides:
    search_categories: list[Category] = [
        Category({
            'id': 100,
            'name': 'test searched category 1',
            'parent_id': None,
            'search_similarity': 0.75,
        }),
        Category({
            'id': 101,
            'name': 'test searched category 2',
            'parent_id': None,
            'search_similarity': 0.75,
        }),
    ]
    popular: dict[str, Category] = {
        'category_groups': [
            CategoryGroup({
                "name": "Action Comedy",
                "categories": [
                    27,
                    29
                ]
            }),
        ],
        'categories': [
            Category({
                'id': 200,
                'name': 'test popular category 1',
                'parent_id': None,
                'search_similarity': None,
            }),
            Category({
                'id': 201,
                'name': 'test popular category 2',
                'parent_id': None,
                'search_similarity': None,
            }),
            Category({
                'id': 202,
                'name': 'test popular category 3',
                'parent_id': None,
                'search_similarity': None,
            }),
        ]
    }
    relevant: dict[str, list[Category]] = {
        'category_groups': [
            CategoryGroup({
                "name": "Action Comedy",
                "categories": [
                    27,
                    29
                ]
            }),
        ],
        'categories': [
            Category({
                'id': 300,
                'name': 'test relevant category 1',
                'parent_id': None,
                'search_similarity': None,
            }),
            Category({
                'id': 301,
                'name': 'test relevant category 2',
                'parent_id': None,
                'search_similarity': None,
            }),
            Category({
                'id': 302,
                'name': 'test relevant category 3',
                'parent_id': None,
                'search_similarity': None,
            }),
        ],
    }
    random: list[Category] = [
        Category({
            'id': 400,
            'name': 'test random category 1',
            'parent_id': None,
            'search_similarity': None,
        }),
    ]
    @staticmethod
    def set_cache():
        categories: list[Category] = [] + \
            LifeFrameCategoryOverrides.search_categories + \
            LifeFrameCategoryOverrides.popular['categories'] + \
            LifeFrameCategoryOverrides.relevant['categories'] + \
            LifeFrameCategoryOverrides.random
        for c in categories:
            cache_key = f'category_{c.id}'
            cache.set(
                key=cache_key,
                value=c.to_dict(),
                timeout=settings.DEFAULT_CACHE_TIMEOUT)


class TestFiles:
    _file_cache: dict[str, bytes] = {}
    @staticmethod
    def get_simple_uploaded_file(kind: str, *args, **kwargs) -> SimpleUploadedFile:
        """
        Generates a `SimpleUploadedFile` and caches the bytes,
        if the same file is requested the cached bytes will be
        used to generate another `SimpleUploadedFile`.
        """
        content_type: str = None
        file_name: str = None
        # For now, the cache key is always just the file_name,
        # but mp4 should probably be split into some different
        # supported aspect ratios.
        cache_key: str = None
        match kind:
            case 'doc':
                file_name = 'test.doc'
                cache_key = file_name
                content_type = "application/msword"
            case 'docx':
                file_name = 'test.docx'
                cache_key = file_name
                content_type = "application/" + \
                    "vnd.openxmlformats-officedocument.wordprocessingml.document"
            case 'gif':
                file_name = 'test.gif'
                cache_key = file_name
                content_type = "image/gif"
            case 'mp3':
                file_name = 'test.mp3'
                cache_key = file_name
                content_type = 'audio/mpeg'
            case 'mp4':
                file_name = 'test.mp4'
                cache_key = file_name
                content_type = 'video/mp4'
            case 'heic':
                file_name = 'test.heic'
                cache_key = file_name
                content_type="image/heic"
            case 'jpeg':
                file_name = 'test.jpeg'
                cache_key = file_name
                content_type="image/jpeg"
            case 'jpg':
                file_name = "test.jpg"
                cache_key = file_name
                content_type = "image/jpg"
            case 'png':
                file_name = "test.png"
                cache_key = file_name
                content_type = "image/png"
            case 'pdf':
                file_name = "test.pdf"
                cache_key = file_name
                content_type = "application/pdf"
            case 'txt':
                file_name = "test.txt"
                content_type = "text/plain"
            case _:
                raise Exception('Requested file not supported')
        cached_bytes = TestFiles._file_cache.get(cache_key)
        if cached_bytes is not None:
            SimpleUploadedFile(
                file_name,
                cached_bytes,
                content_type=content_type)
        simple_upload_file: SimpleUploadedFile = None
        file_dir = f'{settings.BASE_DIR}/api/tests/assets'
        with open(f'{file_dir}/{file_name}', 'rb') as f:
            _bytes = f.read()
            simple_upload_file = SimpleUploadedFile(
                file_name,
                _bytes,
                content_type=content_type)
            TestFiles._file_cache[file_name] = _bytes
        return simple_upload_file
