from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from snap_buy.products.api.views import ProductCategoryViewSet
from snap_buy.products.api.views import ProductViewSet
from snap_buy.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("product-categories", ProductCategoryViewSet)
router.register("products", ProductViewSet)

app_name = "api"
urlpatterns = router.urls
