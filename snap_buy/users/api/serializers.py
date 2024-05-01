from django.conf import settings
from django.utils.translation import gettext as _
from django_countries.serializers import CountryFieldMixin
from phonenumber_field.serializerfields import PhoneNumberField
from rest_framework import serializers

from snap_buy.users.exceptions import AccountNotRegisteredException
from snap_buy.users.models import Address
from snap_buy.users.models import PhoneNumber
from snap_buy.users.models import Profile
from snap_buy.users.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["name", "url"]

        extra_kwargs = {
            "url": {"view_name": "api:user-detail", "lookup_field": "pk"},
        }


class ShippingAddressSerializer(CountryFieldMixin, serializers.ModelSerializer):
    """
    Serializer class to seralize address of type shipping

    For shipping address, automatically set address type to shipping
    """

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Address
        fields = "__all__"
        read_only_fields = ("address_type",)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["address_type"] = "S"

        return representation


class BillingAddressSerializer(CountryFieldMixin, serializers.ModelSerializer):
    """
    Serializer class to seralize address of type billing

    For billing address, automatically set address type to billing
    """

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Address
        fields = "__all__"
        read_only_fields = ("address_type",)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation["address_type"] = "B"

        return representation


class AddressReadOnlySerializer(CountryFieldMixin, serializers.ModelSerializer):
    """
    Serializer class to seralize Address model
    """

    user = serializers.CharField(source="user.get_full_name", read_only=True)

    class Meta:
        model = Address
        fields = "__all__"


class VerifyPhoneNumberSerialzier(serializers.Serializer):
    """
    Serializer class to verify OTP.
    """

    phone_number = PhoneNumberField()
    otp = serializers.CharField(max_length=settings.TOKEN_LENGTH)

    def validate_phone_number(self, value):
        queryset = User.objects.filter(phone__phone_number=value)
        if not queryset.exists():
            raise AccountNotRegisteredException
        return value

    def validate(self, validated_data):
        phone_number = str(validated_data.get("phone_number"))
        otp = validated_data.get("otp")

        queryset = PhoneNumber.objects.get(phone_number=phone_number)

        queryset.check_verification(security_code=otp)

        return validated_data


class ProfileSerializer(serializers.ModelSerializer):
    """
    Serializer class to serialize the user Profile model
    """

    class Meta:
        model = Profile
        fields = (
            "avatar",
            "bio",
            "created_at",
            "updated_at",
        )


class PhoneNumberSerializer(serializers.ModelSerializer):
    """
    Serializer class to serialize phone number.
    """

    phone_number = PhoneNumberField()

    class Meta:
        model = PhoneNumber
        fields = ("phone_number",)

    def validate_phone_number(self, value):
        try:
            queryset = User.objects.get(phone__phone_number=value)
            if queryset.phone.is_verified:
                err_message = _("Phone number is already verified")
                raise serializers.ValidationError(err_message)

        except User.DoesNotExist:
            raise AccountNotRegisteredException from None

        return value
