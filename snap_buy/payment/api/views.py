import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from snap_buy.order.models import Order
from snap_buy.order.permissions import IsOrderByBuyerOrAdmin
from snap_buy.payment.api.serializers import CheckoutSerializer
from snap_buy.payment.api.serializers import PaymentSerializer
from snap_buy.payment.models import Payment
from snap_buy.payment.permissions import DoesOrderHaveAddress
from snap_buy.payment.permissions import IsOrderPendingWhenCheckout
from snap_buy.payment.permissions import IsPaymentByUser
from snap_buy.payment.permissions import IsPaymentForOrderNotCompleted
from snap_buy.payment.permissions import IsPaymentPending
from snap_buy.payment.tasks import send_payment_success_email_task

stripe.api_key = settings.STRIPE_SECRET_KEY


class PaymentViewSet(ModelViewSet):
    """
    CRUD payment for an order
    """

    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer
    permission_classes = [IsPaymentByUser]

    def get_queryset(self):
        res = super().get_queryset()
        user = self.request.user
        return res.filter(order__buyer=user)

    def get_permissions(self):
        if self.action in ("update", "partial_update", "destroy"):
            self.permission_classes += [IsPaymentPending]

        return super().get_permissions()


class CheckoutAPIView(RetrieveUpdateAPIView):
    """
    Create, Retrieve, Update billing address, shipping address and payment of an order
    """

    queryset = Order.objects.all()
    serializer_class = CheckoutSerializer
    permission_classes = [IsOrderByBuyerOrAdmin]

    def get_permissions(self):
        if self.request.method in ("PUT", "PATCH"):
            self.permission_classes += [IsOrderPendingWhenCheckout]

        return super().get_permissions()


class StripeCheckoutSessionCreateAPIView(APIView):
    """
    Create and return checkout session ID for order payment of type 'Stripe'
    """

    permission_classes = (
        IsPaymentForOrderNotCompleted,
        DoesOrderHaveAddress,
    )

    def post(self, request, *args, **kwargs):
        order = get_object_or_404(Order, id=self.kwargs.get("order_id"))

        order_items = []

        for order_item in order.order_items.all():
            product = order_item.product
            quantity = order_item.quantity

            data = {
                "price_data": {
                    "currency": "usd",
                    "unit_amount_decimal": product.price,
                    "product_data": {
                        "name": product.name,
                        "description": product.desc,
                        "images": [f"{settings.BACKEND_DOMAIN}{product.image.url}"],
                    },
                },
                "quantity": quantity,
            }

            order_items.append(data)

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=order_items,
            metadata={"order_id": order.id},
            mode="payment",
            success_url=settings.PAYMENT_SUCCESS_URL,
            cancel_url=settings.PAYMENT_CANCEL_URL,
        )

        return Response(
            {"sessionId": checkout_session["id"]},
            status=status.HTTP_201_CREATED,
        )


class StripeWebhookAPIView(APIView):
    """
    Stripe webhook API view to handle checkout session completed and other events.
    """

    def post(self, request, *args, **kwargs):
        payload = request.body
        endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
        sig_header = request.headers["stripe-signature"]
        event = None

        try:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        except ValueError:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            customer_email = session["customer_details"]["email"]
            order_id = session["metadata"]["order_id"]

            payment = get_object_or_404(Payment, order=order_id)
            payment.status = "C"
            payment.save()

            order = get_object_or_404(Order, id=order_id)
            order.status = "C"
            order.save()

            # TODO - Decrease product quantity
            send_payment_success_email_task.delay(customer_email)

        # Can handle other events here.

        return Response(status=status.HTTP_200_OK)
