import json
from typing import Dict

from django.test import Client
from django.urls import reverse


class TestResult:
    """Represents the result of a test operation."""

    def __init__(self, success: bool, message: str, data: dict = None, error: str = None):
        self.success = success
        self.message = message
        self.data = data or {}
        self.error = error


class JWTAuthTester:
    """Production-grade JWT authentication flow tester with correct URL mapping."""

    def __init__(self):
        self.client = Client()
        self.test_password = "SecureTestPassword123!"
        self.base_url = "/api/v1"

    def _test_jwt_token_api_generation(self, email: str) -> TestResult:
        """Test JWT token generation via correct API endpoint."""
        try:
            response = self.client.post(
                f"{self.base_url}/auth/jwt/",
                data=json.dumps({"email": email, "password": self.test_password}),
                content_type="application/json",
            )

            response_data = {}
            try:
                response_data = json.loads(response.content)
            except json.JSONDecodeError:
                response_data = {"raw_content": response.content.decode("utf-8")}

            if response.status_code == 200:
                access_token = response_data.get("access")
                refresh_token = response_data.get("refresh")

                return TestResult(
                    success=True,
                    message="JWT tokens generated via API",
                    data={
                        "access_token": access_token,
                        "refresh_token": refresh_token,
                        "status_code": response.status_code,
                    },
                )
            else:
                error_detail = response_data.get("detail", response_data.get("error", "Unknown error"))
                return TestResult(
                    success=False,
                    message=f"API token generation failed: HTTP {response.status_code}",
                    data={
                        "status_code": response.status_code,
                        "error_detail": error_detail,
                        "response_data": response_data,
                        "url": f"{self.base_url}/auth/jwt/",
                    },
                    error=f"HTTP {response.status_code}: {error_detail}",
                )

        except Exception as e:
            return TestResult(success=False, message=f"API token generation error: {str(e)}", data={}, error=str(e))

    def _test_protected_endpoint_access(self, access_token: str) -> TestResult:
        """Test access to a protected endpoint using JWT with the correct URL resolution."""
        try:
            profile_urls = [
                f"{self.base_url}/users/profile/",
                f"{self.base_url}/accounts/",
            ]

            profile_url = None
            last_response = None

            for url in profile_urls:
                try:
                    response = self.client.get(url, HTTP_AUTHORIZATION=f"Bearer {access_token}")
                    last_response = response

                    if response.status_code != 404:
                        profile_url = url
                        break

                except Exception:
                    continue

            if not profile_url:
                try:
                    from django.urls import reverse

                    profile_url = reverse("users:profile", kwargs={"pk": "me"})

                    response = self.client.get(profile_url, HTTP_AUTHORIZATION=f"Bearer {access_token}")
                    last_response = response

                except Exception:
                    profile_url = profile_urls[0]  # Fallback
                    response = (
                        last_response
                        if last_response
                        else self.client.get(profile_url, HTTP_AUTHORIZATION=f"Bearer {access_token}")
                    )

            if response.status_code == 200:
                try:
                    data = json.loads(response.content)
                except json.JSONDecodeError:
                    data = {"raw_content": response.content.decode("utf-8")}

                return TestResult(
                    success=True,
                    message="Protected endpoint access successful",
                    data={"status_code": response.status_code, "user_data": data, "url": profile_url},
                )
            else:
                return TestResult(
                    success=False,
                    message=f"Protected endpoint returned {response.status_code}",
                    data={
                        "status_code": response.status_code,
                        "url": profile_url,
                        "expected_url": f"{self.base_url}/users/profile/me/",
                    },
                    error=f"HTTP {response.status_code}",
                )

        except Exception as e:
            return TestResult(success=False, message=f"Protected endpoint test failed: {str(e)}", data={}, error=str(e))

    def _test_token_refresh_api(self, refresh_token: str) -> TestResult:
        """Test token refresh via API endpoint."""
        try:
            response = self.client.post(
                f"{self.base_url}/auth/jwt/refresh/",
                data=json.dumps({"refresh": refresh_token}),
                content_type="application/json",
            )

            if response.status_code == 200:
                data = json.loads(response.content)
                return TestResult(
                    success=True,
                    message="Token refresh successful",
                    data={
                        "new_access_token": data.get("access"),
                        "status_code": response.status_code,
                    },
                )
            else:
                return TestResult(
                    success=False,
                    message=f"Token refresh failed: HTTP {response.status_code}",
                    data={"status_code": response.status_code},
                    error=f"HTTP {response.status_code}",
                )

        except Exception as e:
            return TestResult(success=False, message=f"Token refresh error: {str(e)}", data={}, error=str(e))

    def _test_token_blacklisting(self, refresh_token: str) -> TestResult:
        """Test token blacklisting via logout endpoint with correct URL."""
        try:
            access_token = self._get_access_token_for_user()

            logout_urls = [
                # f"{self.base_url}/users/auth/logout/",
                 "/api/v1/users/auth/logout/",
            ]

            logout_url = None
            last_response = None

            for url in logout_urls:
                try:
                    response = self.client.post(
                        url,
                        data=json.dumps({"refresh": refresh_token}),
                        content_type="application/json",
                        HTTP_AUTHORIZATION=f"Bearer {access_token}",
                    )
                    last_response = response

                    if response.status_code != 404:
                        logout_url = url
                        break

                except Exception:
                    continue

            if not logout_url or (last_response and last_response.status_code == 404):

                try:
                    from django.urls import reverse

                    # Попробуем точный namespace и basename из конфигурации
                    logout_url = reverse("auth:auth-logout")

                    response = self.client.post(
                        logout_url,
                        data=json.dumps({"refresh": refresh_token}),
                        content_type="application/json",
                        HTTP_AUTHORIZATION=f"Bearer {access_token}",
                    )
                    last_response = response

                except Exception as reverse_error:
                    return TestResult(
                        success=False,
                        message="Logout endpoint not found - URL configuration issue",
                        data={
                            "tested_urls": logout_urls,
                            "last_status_code": last_response.status_code if last_response else "No response",
                            "reverse_error": str(reverse_error),
                            "suggestion": "URL configuration: users/ + auth/ + logout/ = /api/v1/users/auth/logout/",
                        },
                        error="HTTP 404 - Endpoint not found",
                    )

            response = last_response

            if response.status_code == 200:
                refresh_response = self.client.post(
                    f"{self.base_url}/auth/jwt/refresh/",
                    data=json.dumps({"refresh": refresh_token}),
                    content_type="application/json",
                )

                if refresh_response.status_code != 200:
                    return TestResult(
                        success=True,
                        message="Token blacklisting working correctly",
                        data={"blacklisted": True, "url": logout_url, "status_code": response.status_code},
                    )
                else:
                    return TestResult(
                        success=False,
                        message="Blacklisted token still working",
                        data={"url": logout_url, "status_code": response.status_code},
                        error="Blacklisting failed",
                    )
            else:
                response_data = {}
                try:
                    response_data = json.loads(response.content)
                except Exception:
                    pass

                return TestResult(
                    success=False,
                    message=f"Logout API failed: HTTP {response.status_code}",
                    data={
                        "status_code": response.status_code,
                        "response_data": response_data,
                        "url": logout_url,
                        "expected_url": f"{self.base_url}/auth/logout/",
                    },
                    error=f"HTTP {response.status_code}",
                )

        except Exception as e:
            return TestResult(success=False, message=f"Token blacklisting test failed: {str(e)}", data={}, error=str(e))

    def _url_exists(self, url_name: str) -> bool:
        """Check if a URL name exists in the URLconf."""
        try:
            reverse(url_name)
            return True
        except Exception:
            return False

    def _test_url_exists(self, url: str) -> bool:
        """Test if a URL exists by making a simple request."""
        try:
            response = self.client.get(url)
            return response.status_code != 404
        except Exception:
            return False

    def _get_access_token_for_user(self) -> str:
        """Get valid access token for authenticated requests."""
        try:
            from django.contrib.auth import get_user_model

            User = get_user_model()

            temp_user = User.objects.filter(email="temp.logout@test.com").first()
            if not temp_user:
                temp_user = User.objects.create_user(
                    email="temp.logout@test.com", password=self.test_password, is_active=True
                )

            from rest_framework_simplejwt.tokens import RefreshToken

            refresh = RefreshToken.for_user(temp_user)
            return str(refresh.access_token)

        except Exception:
            return "dummy_token_for_testing"

    def test_complete_jwt_flow(self, email: str) -> Dict[str, TestResult]:
        """Test complete JWT authentication flow from registration to logout."""
        results = {}

        try:
            # Step 1: Create test user
            results["user_creation"] = self._create_test_user(email)
            if not results["user_creation"].success:
                return results

            # Step 2: Test JWT token generation via API
            results["token_generation"] = self._test_jwt_token_api_generation(email)
            if not results["token_generation"].success:
                return results

            # Extract tokens for further tests
            access_token = results["token_generation"].data.get("access_token")
            refresh_token = results["token_generation"].data.get("refresh_token")

            if not access_token or not refresh_token:
                results["token_extraction"] = TestResult(
                    success=False,
                    message="Failed to extract tokens from login response",
                    data={},
                    error="Tokens missing from API response",
                )
                return results

            # Step 3: Test protected endpoint access
            results["protected_access"] = self._test_protected_endpoint_access(access_token)

            # Step 4: Test token refresh
            results["token_refresh"] = self._test_token_refresh_api(refresh_token)

            # Step 5: Test token blacklisting (logout)
            results["token_blacklisting"] = self._test_token_blacklisting(refresh_token)

            # Step 6: Cleanup - remove test user
            results["cleanup"] = self._cleanup_test_user(email)

            return results

        except Exception as e:
            results["critical_error"] = TestResult(
                success=False, message=f"Critical error in JWT flow test: {str(e)}", data={}, error=str(e)
            )
            return results

    def _create_test_user(self, email: str) -> TestResult:
        """Create test user for JWT testing."""
        try:
            from django.contrib.auth import get_user_model

            User = get_user_model()

            # Clean up existing test user
            User.objects.filter(email=email).delete()

            # Create new test user
            user = User.objects.create_user(
                email=email, password=self.test_password, first_name="JWT", last_name="Test", is_active=True
            )

            return TestResult(
                success=True,
                message="Test user created successfully",
                data={"user_id": user.id, "email": user.email, "is_active": user.is_active},
            )

        except Exception as e:
            return TestResult(success=False, message=f"Failed to create test user: {str(e)}", data={}, error=str(e))

    def _cleanup_test_user(self, email: str) -> TestResult:
        """Clean up test user after JWT testing."""
        try:
            from django.contrib.auth import get_user_model

            User = get_user_model()

            deleted_count, _ = User.objects.filter(email=email).delete()

            return TestResult(
                success=True,
                message=f"Test user cleanup completed ({deleted_count} users deleted)",
                data={"deleted_count": deleted_count, "email": email},
            )

        except Exception as e:
            return TestResult(success=False, message=f"Failed to cleanup test user: {str(e)}", data={}, error=str(e))
