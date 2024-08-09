from enum import Enum


class BasePermissionEnum(Enum):
    @property
    def codename(self):
        return self.value.split(".")[1]


class AccountPermissions(BasePermissionEnum):
    MANAGE_USERS = "account.manage_users"
    MANAGE_STAFF = "account.manage_staff"
    IMPERSONATE_USER = "account.impersonate_user"


class AppPermission(BasePermissionEnum):
    MANAGE_APPS = "app.manage_apps"
    MANAGE_OBSERVABILITY = "app.manage_observability"


class CheckoutPermissions(BasePermissionEnum):
    MANAGE_CHECKOUTS = "checkout.manage_checkouts"
    HANDLE_CHECKOUTS = "checkout.handle_checkouts"
    HANDLE_TAXES = "checkout.handle_taxes"
    MANAGE_TAXES = "checkout.manage_taxes"


class ChannelPermissions(BasePermissionEnum):
    MANAGE_CHANNELS = "channel.manage_channels"


class GiftcardPermissions(BasePermissionEnum):
    MANAGE_GIFT_CARD = "giftcard.manage_gift_card"


class DiscountPermissions(BasePermissionEnum):
    MANAGE_DISCOUNTS = "discount.manage_discounts"


class OrderPermissions(BasePermissionEnum):
    MANAGE_ORDERS = "order.manage_orders"
    MANAGE_ORDERS_IMPORT = "order.manage_orders_import"


class ProductPermissions(BasePermissionEnum):
    MANAGE_PRODUCTS = "product.manage_products"


class ProductTypePermissions(BasePermissionEnum):
    MANAGE_PRODUCT_TYPES_AND_ATTRIBUTES = "product.manage_product_types_and_attributes"


class ShippingPermissions(BasePermissionEnum):
    MANAGE_SHIPPING = "shipping.manage_shipping"
