import math
import re
from json import JSONEncoder
from json.encoder import ESCAPE_DCT  # type: ignore[misc] # private method
from json.encoder import INFINITY  # type: ignore[misc] # private method
from json.encoder import _make_iterencode  # type: ignore[misc] # private method
from json.encoder import c_make_encoder  # type: ignore[misc] # private method

from django.core.serializers.json import DjangoJSONEncoder
from django.core.serializers.json import Serializer as JsonSerializer
from measurement.measures import Weight
from prices import Money

MONEY_TYPE = "Money"
ESCAPE_CHARS = re.compile(r"[\x00-\x1f\\\"\b\f\n\r\t<>']")


class Serializer(JsonSerializer):
    def _init_options(self):
        super()._init_options()  # type: ignore[misc] # private method
        self.json_kwargs["cls"] = CustomJsonEncoder


class CustomJsonEncoder(DjangoJSONEncoder):
    def default(self, obj):
        if isinstance(obj, Money):
            return {"_type": MONEY_TYPE, "amount": obj.amount, "currency": obj.currency}
        # Mirror implementation of django_measurement.MeasurementField.value_to_string
        if isinstance(obj, Weight):
            return f"{obj.value}:{obj.unit}"
        return super().default(obj)


class SafeJSONEncoder(JSONEncoder):
    @property
    def escape_chars_pattern(self):
        return ESCAPE_CHARS

    def make_safe_string(self, s: str):
        def replace(match):
            c = match.group(0)
            if c not in ESCAPE_DCT:
                return rf"\u{ord(c):04x}"
            return ESCAPE_DCT[c]

        return f'"{self.escape_chars_pattern.sub(replace, s)}"'

    def encode(self, o):
        if isinstance(o, str):
            return self.make_safe_string(o)
        return super().encode(o)

    def iterencode(self, o, *, _one_shot=False):
        """Encode the given object and yield each string
        representation as available.

        For example::

            for chunk in JSONEncoder().iterencode(bigobject):
                mysocket.write(chunk)

        """
        markers = {} if self.check_circula else None

        _encoder = self.make_safe_string

        def floatstr(
            o,
            allow_nan=self.allow_nan,
            _repr=float.__repr__,
            _inf=INFINITY,
            _neginf=-INFINITY,
        ):
            # Check for specials.  Note that this type of test is processor
            # and/or platform-specific, so do tests which don't depend on the
            # internals.

            if math.isnan(o):
                text = "NaN"
            elif o == _inf:
                text = "Infinity"
            elif o == _neginf:
                text = "-Infinity"
            else:
                return _repr(o)

            if not allow_nan:
                raise ValueError(
                    "Out of range float values are not JSON compliant: " + repr(o),
                )

            return text

        if _one_shot and c_make_encoder is not None and self.indent is None:
            _iterencode = c_make_encoder(
                markers,
                self.default,
                _encoder,
                self.indent,
                self.key_separator,
                self.item_separator,
                self.sort_keys,
                self.skipkeys,
                self.allow_nan,
            )
        else:
            _iterencode = _make_iterencode(
                markers,
                self.default,
                _encoder,
                self.indent,
                floatstr,
                self.key_separator,
                self.item_separator,
                self.sort_keys,
                self.skipkeys,
                _one_shot,
            )
        return _iterencode(o, 0)


class HTMLSafeJSON(SafeJSONEncoder, DjangoJSONEncoder):
    """Escape dangerous characters from JSON.

    It is used for integrating JSON into HTML content in addition to
    serializing Django objects.
    """
