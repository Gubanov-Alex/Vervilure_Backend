import logging
from typing import Dict, Optional, Tuple

from google.auth.transport import requests
from google.oauth2 import id_token

logger = logging.getLogger(__name__)


class GoogleOAuthValidator:
    """
    Secure Google OAuth token validation with comprehensive error handling.
    """

    def __init__(self, client_id: str):
        self.client_id = client_id

    def validate_token(self, token: str) -> Tuple[bool, Optional[Dict], Optional[str]]:
        """
        Validate Google ID token and extract user info.

        Returns:
            (is_valid, user_info, error_message)
        """
        try:
            # Verify the token
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), self.client_id)

            # Verify issuer
            if idinfo["iss"] not in ["accounts.google.com", "https://accounts.google.com"]:
                raise ValueError("Wrong issuer.")

            # Extract user information
            user_info = {
                "google_id": idinfo["sub"],
                "email": idinfo["email"],
                "email_verified": idinfo.get("email_verified", False),
                "first_name": idinfo.get("given_name", ""),
                "last_name": idinfo.get("family_name", ""),
                "avatar_url": idinfo.get("picture", ""),
            }

            return True, user_info, None

        except ValueError as e:
            logger.warning(f"Google token validation failed: {str(e)}")
            return False, None, "Invalid Google token"
        except Exception as e:
            logger.error(f"Google OAuth validation error: {str(e)}")
            return False, None, "OAuth validation failed"
