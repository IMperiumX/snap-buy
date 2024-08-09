from django.urls import path

from snap_buy.payment.api.views import CheckoutAPIView
from snap_buy.payment.api.views import StripeCheckoutSessionCreateAPIView
from snap_buy.payment.api.views import StripeWebhookAPIView

app_name = "payments"
urlpatterns = [
    path(
        "stripe/create-checkout-session/<int:order_id>/",
        StripeCheckoutSessionCreateAPIView.as_view(),
        name="checkout_session",
    ),
    path("stripe/webhook/", StripeWebhookAPIView.as_view(), name="stripe_webhook"),
    path("checkout/<int:pk>/", CheckoutAPIView.as_view(), name="checkout"),
]
