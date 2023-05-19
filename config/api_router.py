from django.conf import settings
from rest_framework.routers import DefaultRouter, SimpleRouter

from snap_buy.users.api.views import UserViewSet

if settings.DEBUG:
    router = DefaultRouter()
else:
    router = SimpleRouter()

# basename = user-detail, if not specified it will get the object.model_name.lower
# and add -detail to it so for the final viewname it will be user-detal with the
# api namespace api:user-detail,
# inside get_default_basename funciton return... queryset.model._meta.object_name.lower()
router.register("users", UserViewSet)

app_name = "api"
urlpatterns = router.urls
