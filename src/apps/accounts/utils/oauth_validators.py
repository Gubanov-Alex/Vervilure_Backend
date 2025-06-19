import logging
from typing import Any, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


class GoogleOAuthValidator:
    """
    Validator for Google OAuth access tokens.

    Handles token validation and user info extraction from Google's API.
    """

    def __init__(self, client_id: str):
        self.client_id = client_id
        self.google_userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        self.google_tokeninfo_url = "https://www.googleapis.com/oauth2/v1/tokeninfo"

    def validate_token(self, access_token: str) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Validate Google access token and return user information.

        Returns:
            Tuple of (is_valid, user_info, error_message)
        """
        try:
            # First, validate the token
            token_info = self._get_token_info(access_token)
            if not token_info:
                return False, None, "Invalid token"

            # Check if token is for our app
            if token_info.get("audience") != self.client_id:
                return False, None, "Token not issued for this application"

            # Get user information
            user_info = self._get_user_info(access_token)
            if not user_info:
                return False, None, "Could not retrieve user information"

            # Process and normalize user data
            processed_user_info = self._process_user_info(user_info)

            return True, processed_user_info, None

        except requests.RequestException as e:
            logger.error(f"Google API request failed: {str(e)}")
            return False, None, "Failed to validate token with Google"
        except Exception as e:
            logger.error(f"Token validation error: {str(e)}")
            return False, None, "Token validation failed"

    def _get_token_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get token information from Google."""
        try:
            response = requests.get(self.google_tokeninfo_url, params={"access_token": access_token}, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Token info request failed: {response.status_code}")
                return None

        except requests.RequestException as e:
            logger.error(f"Token info request failed: {str(e)}")
            return None

    def _get_user_info(self, access_token: str) -> Optional[Dict[str, Any]]:
        """Get user information from Google."""
        try:
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(self.google_userinfo_url, headers=headers, timeout=10)

            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"User info request failed: {response.status_code}")
                return None

        except requests.RequestException as e:
            logger.error(f"User info request failed: {str(e)}")
            return None

    def _process_user_info(self, raw_user_info: Dict[str, Any]) -> Dict[str, Any]:
        """Process and normalize user information from Google."""
        return {
            "google_id": raw_user_info.get("id"),
            "email": raw_user_info.get("email"),
            "email_verified": raw_user_info.get("verified_email", False),
            "first_name": raw_user_info.get("given_name", ""),
            "last_name": raw_user_info.get("family_name", ""),
            "full_name": raw_user_info.get("name", ""),
            "picture_url": raw_user_info.get("picture", ""),
            "locale": raw_user_info.get("locale", "en"),
        }
