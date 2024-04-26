import datetime
import logging
import string

from django.conf import settings
from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import NotAcceptable
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client

logger = logging.getLogger(__name__)


class PhoneVerificationMixin:
    def generate_security_code(self):
        """
        Returns a unique random `security_code` for given `TOKEN_LENGTH` in the settings.
        Default token length = 6
        """
        token_length = getattr(settings, "TOKEN_LENGTH", 6)
        return get_random_string(token_length, allowed_chars=string.digits)

    def is_security_code_expired(self):
        expiration_date = self.sent + datetime.timedelta(
            minutes=settings.TOKEN_EXPIRE_MINUTES,
        )
        return expiration_date <= timezone.now()

    def send_confirmation(self):
        twilio_account_sid = settings.TWILIO_ACCOUNT_SID
        twilio_auth_token = settings.TWILIO_AUTH_TOKEN
        twilio_phone_number = settings.TWILIO_PHONE_NUMBER

        if not all([twilio_account_sid, twilio_auth_token, twilio_phone_number]):
            logger.debug("Twilio credentials are not set")
            return False

        self.security_code = self.generate_security_code()
        logger.info(
            f"Sending security code {self.security_code} to phone {self.phone_number}",
        )

        try:
            twilio_client = Client(twilio_account_sid, twilio_auth_token)
            twilio_client.messages.create(
                body=f"Your activation code is {self.security_code}",
                to=str(self.phone_number),
                from_=twilio_phone_number,
            )
        except TwilioRestException as e:
            logger.debug(f"Twilio error: {e}")
            return False
        else:
            self.sent = timezone.now()
            self.save()
            return True

    def check_verification(self, security_code):
        if (
            not self.is_security_code_expired()
            and security_code == self.security_code
            and not self.is_verified
        ):
            self.is_verified = True
            self.save()
        else:
            raise NotAcceptable(
                _(
                    "Your security code is wrong, expired or this phone is verified before.",
                ),
            )

        return self.is_verified
