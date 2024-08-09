from urllib.parse import urljoin

from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.encoding import iri_to_uri


def get_public_url(domain: str | None = None) -> str:
    if settings.PUBLIC_URL:
        return settings.PUBLIC_URL
    host = domain or Site.objects.get_current().domain
    protocol = "https" if settings.ENABLE_SSL else "http"
    return f"{protocol}://{host}"


def build_absolute_uri(location: str, domain: str | None = None) -> str:
    """Create absolute uri from location.

    If provided location is absolute uri by itself, it returns unchanged value,
    otherwise if provided location is relative, absolute uri is built and returned.
    """
    current_uri = get_public_url(domain)
    location = urljoin(current_uri, location)
    return iri_to_uri(location)
