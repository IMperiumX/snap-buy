from django.conf import settings
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from snap_buy.payment.api.views import PaymentViewSet
from snap_buy.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)

router.register("payments", PaymentViewSet, basename="order-payment")


app_name = "api"
urlpatterns = router.urls
