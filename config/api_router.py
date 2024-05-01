from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from snap_buy.orders.api.views import OrderItemViewSet
from snap_buy.orders.api.views import OrderViewSet
from snap_buy.payments.api.views import PaymentViewSet
from snap_buy.products.api.views import ProductCategoryViewSet
from snap_buy.products.api.views import ProductViewSet
from snap_buy.users.api.views import AddressViewSet
from snap_buy.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("users", AddressViewSet, basename="user-address")


router.register("products", ProductCategoryViewSet, basename="product-category")
router.register("products", ProductViewSet)

router.register("orders", OrderViewSet)
router.register("orders", OrderItemViewSet, basename="order-orderitem")

router.register("payments", PaymentViewSet, basename="order-payment")


app_name = "api"
urlpatterns = router.urls
