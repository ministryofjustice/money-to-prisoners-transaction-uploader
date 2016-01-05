from urllib.parse import urljoin

from oauthlib.oauth2 import LegacyApplicationClient
from requests.exceptions import HTTPError
from requests_oauthlib import OAuth2Session
import slumber

from . import settings

REQUEST_TOKEN_URL = urljoin(settings.API_URL, '/oauth2/token/')


def get_authenticated_connection():
    """
    Returns:
        an authenticated slumber connection
    """
    session = OAuth2Session(
        client=LegacyApplicationClient(
            client_id=settings.API_CLIENT_ID
        )
    )

    session.fetch_token(
        token_url=REQUEST_TOKEN_URL,
        username=settings.API_USERNAME,
        password=settings.API_PASSWORD,
        client_id=settings.API_CLIENT_ID,
        client_secret=settings.API_CLIENT_SECRET
    )

    return slumber.API(
        base_url=settings.API_URL, session=session
    )
