from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from rest_framework import routers

from api.views.action import ActionViewSet
from api.views.activity import ActivityViewSet
from api.views.app_color import AppColorViewSet
from api.views.category import CategoryViewSet
from api.views.conversation import ConversationViewSet
from api.views.custom_category import CustomCategoryViewSet
from api.views.comment import CommentViewSet
from api.views.device import DevicesViewSet
from api.views.discover_feed import DiscoverFeedViewSet
from api.views.experience import ExperienceViewSet
from api.views.follow_feed import FollowFeedViewSet
from api.views.for_you_feed import ForYouFeedViewSet
from api.views.google_maps import GoogleMapsViewSet
from api.views.healthcheck import healthcheck
from api.views.info import InfoViewSet
from api.views.interest import InterestViewSet
from api.views.playlist import PlaylistViewSet
from api.views.post import PostViewSet
from api.views.report import ReportViewSet
from api.views.user import UserViewSet
from api.views.webhooks import WebhookViewSet

from schedules.views.experience_of_the_day import ExperienceOfTheDayScheduleViewSet


router = routers.DefaultRouter()
router.register(
    r'activities',
    ActivityViewSet,
    basename='activities')
router.register(
    r'action',
    ActionViewSet,
    basename='action')
router.register(
    r'app_colors',
    AppColorViewSet,
    basename='app_colors')
router.register(
    r'categories',
    CategoryViewSet,
    basename='categories')
router.register(
    r'custom_categories',
    CustomCategoryViewSet,
    basename='custom_categories')
router.register(
    r'experience_of_the_day_schedules',
    ExperienceOfTheDayScheduleViewSet,
    basename='experience_of_the_day_schedules')
router.register(
    r'for_you_feed',
    ForYouFeedViewSet,
    basename='for_you_feed')
router.register(
    r'playlists',
    PlaylistViewSet,
    basename='playlists')
router.register(
    r'experiences',
    ExperienceViewSet,
    basename='experiences')
router.register(
    r'comments',
    CommentViewSet,
    basename='comments')
router.register(
    r'conversations',
    ConversationViewSet,
    basename='conversations')
router.register(
    r'discover_feed',
    DiscoverFeedViewSet,
    basename='discover_feed')
router.register(
    r'devices',
    DevicesViewSet,
    basename='devices')
router.register(
    r'follow_feed',
    FollowFeedViewSet,
    basename='follow_feed')
router.register(
    r'google_maps',
    GoogleMapsViewSet,
    basename='google_maps')
router.register(
    r'interests',
    InterestViewSet,
    basename='interests')
router.register(
    r'posts',
    PostViewSet,
    basename='posts')
router.register(
    r'reports',
    ReportViewSet,
    basename='reports')
router.register(
    r'users',
    UserViewSet,
    basename='users')
router.register(
    r'info',
    InfoViewSet,
    basename='info')
router.register(
    r'webhooks',
    WebhookViewSet,
    basename='webhooks')


#! BACK COMPAT (EARLIEST_SUPPORTED_APP_VERSION=15)
router.register(
    r'category',
    CategoryViewSet,
    basename='category')
#! Remove this line soon

urlpatterns = [
    *router.urls,
    path('healthcheck/', healthcheck, name='healthcheck'),
    path('admin/', admin.site.urls),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
