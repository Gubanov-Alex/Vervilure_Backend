import json
import logging
from typing import Dict

from django.test import Client

logger = logging.getLogger(__name__)


class TestResult:
    """Represents the result of a test operation."""

    def __init__(self, success: bool, message: str, data: dict = None, error: str = None):
        self.success = success
        self.message = message
        self.data = data or {}
        self.error = error


class JWTAuthTester:
    """Production-grade JWT authentication flow tester with complete implementation."""

    def __init__(self):
        self.client = Client()
        self.test_password = "SecureTestPassword123!"
        self.base_url = "/api/v1"
        self.current_test_user = None

    def test_complete_jwt_flow(self, email: str) -> Dict[str, TestResult]:
        """Test complete JWT authentication flow from registration to logout."""
        results = {}

        try:
            logger.info(f"Starting complete JWT flow test for {email}")

            # Step 1: Create test user
            results["user_creation"] = self._create_test_user(email)
            if not results["user_creation"].success:
                logger.error("User creation failed, stopping test flow")
                return results

            # Step 2: Test JWT token generation via API
            results["token_generation"] = self._test_jwt_token_api_generation(email)
            if not results["token_generation"].success:
                logger.error("Token generation failed, continuing with other tests")
                # Don't return early - continue with other tests that don't require tokens

            # Extract tokens for further tests
            access_token = results["token_generation"].data.get("access_token")
            refresh_token = results["token_generation"].data.get("refresh_token")

            if access_token and refresh_token:
                # Step 3: Test protected endpoint access
                results["protected_access"] = self._test_protected_endpoint_access(access_token)

                # Step 4: Test token refresh
                results["token_refresh"] = self._test_token_refresh_api(refresh_token)

                # Step 5: Test token blacklisting (logout) - FIXED VERSION
                results["token_blacklisting"] = self._test_token_blacklisting_fixed(email)
            else:
                logger.warning("Skipping token-dependent tests due to token generation failure")
                results["token_extraction"] = TestResult(
                    success=False,
                    message="Failed to extract tokens from login response",
                    data={"access_token_present": bool(access_token), "refresh_token_present": bool(refresh_token)},
                    error="Tokens missing from API response",
                )

            # Step 6: Test user authentication endpoints
            results["user_authentication"] = self._test_user_authentication_endpoints(email)

            # Step 7: Test JWT settings validation - FIXED VERSION
            results["jwt_settings"] = self._test_jwt_settings_validation_fixed()

            # Step 8: Cleanup - remove test user (always attempt)
            results["cleanup"] = self._cleanup_test_user(email)

            logger.info(f"Completed JWT flow test for {email}")
            return results

        except Exception as e:
            logger.exception(f"Critical error in JWT flow test: {e}")
            results["critical_error"] = TestResult(
                success=False,
                message=f"Critical error in JWT flow test: {str(e)}",
                data={"exception_type": type(e).__name__},
                error=str(e),
            )

            # Attempt cleanup even on critical error
            try:
                results["emergency_cleanup"] = self._cleanup_test_user(email)
            except Exception as cleanup_error:
                logger.error(f"Emergency cleanup failed: {cleanup_error}")

            return results

    def _test_jwt_token_api_generation(self, email: str) -> TestResult:
        """Test JWT token generation via API endpoint."""
        try:
            # Try multiple possible JWT token endpoints
            jwt_endpoints = [
                f"{self.base_url}/auth/jwt/",
                f"{self.base_url}/auth/login/",
                f"{self.base_url}/users/auth/login/",
                f"{self.base_url}/token/",
            ]

            last_response = None
            last_response_data = {}

            for endpoint in jwt_endpoints:
                try:
                    logger.debug(f"Testing JWT endpoint: {endpoint}")
                    response = self.client.post(
                        endpoint,
                        data=json.dumps({"email": email, "password": self.test_password}),
                        content_type="application/json",
                    )
                    last_response = response

                    response_data = {}
                    try:
                        response_data = json.loads(response.content) if response.content else {}
                    except json.JSONDecodeError:
                        response_data = {"raw_content": response.content.decode("utf-8") if response.content else ""}

                    last_response_data = response_data

                    if response.status_code == 200:
                        access_token = response_data.get("access")
                        refresh_token = response_data.get("refresh")

                        if access_token and refresh_token:
                            return TestResult(
                                success=True,
                                message=f"JWT tokens generated successfully via {endpoint}",
                                data={
                                    "access_token": access_token,
                                    "refresh_token": refresh_token,
                                    "status_code": response.status_code,
                                    "endpoint": endpoint,
                                    "user_id": (
                                        response_data.get("user", {}).get("id") if "user" in response_data else None
                                    ),
                                },
                            )
                        else:
                            logger.warning(f"Endpoint {endpoint} returned 200 but missing tokens")

                    elif response.status_code == 404:
                        logger.debug(f"Endpoint {endpoint} not found (404)")
                        continue
                    else:
                        logger.warning(f"Endpoint {endpoint} returned {response.status_code}")

                except Exception as e:
                    logger.debug(f"Error testing endpoint {endpoint}: {e}")
                    continue

            # If we get here, all endpoints failed
            error_detail = last_response_data.get("detail", last_response_data.get("error", "Authentication failed"))

            return TestResult(
                success=False,
                message=f"JWT token generation failed on all endpoints",
                data={
                    "tested_endpoints": jwt_endpoints,
                    "last_status_code": last_response.status_code if last_response else None,
                    "last_response_data": last_response_data,
                    "error_detail": error_detail,
                },
                error=f"All JWT endpoints failed. Last error: {error_detail}",
            )

        except Exception as e:
            logger.exception(f"JWT token generation error: {e}")
            return TestResult(
                success=False,
                message=f"JWT token generation error: {str(e)}",
                data={"exception_type": type(e).__name__},
                error=str(e),
            )

    def _test_token_refresh_api(self, refresh_token: str) -> TestResult:
        """Test JWT token refresh functionality."""
        try:
            refresh_endpoints = [
                f"{self.base_url}/auth/jwt/refresh/",
                f"{self.base_url}/auth/refresh/",
                f"{self.base_url}/token/refresh/",
            ]

            for endpoint in refresh_endpoints:
                try:
                    logger.debug(f"Testing refresh endpoint: {endpoint}")
                    response = self.client.post(
                        endpoint,
                        data=json.dumps({"refresh": refresh_token}),
                        content_type="application/json",
                    )

                    if response.status_code == 404:
                        continue

                    response_data = {}
                    try:
                        response_data = json.loads(response.content) if response.content else {}
                    except json.JSONDecodeError:
                        response_data = {"raw_content": response.content.decode("utf-8") if response.content else ""}

                    if response.status_code == 200:
                        new_access_token = response_data.get("access")

                        if new_access_token:
                            return TestResult(
                                success=True,
                                message=f"Token refresh successful via {endpoint}",
                                data={
                                    "new_access_token": new_access_token,
                                    "status_code": response.status_code,
                                    "endpoint": endpoint,
                                    "refresh_token_valid": True,
                                },
                            )
                        else:
                            return TestResult(
                                success=False,
                                message=f"Token refresh returned 200 but no access token",
                                data={
                                    "status_code": response.status_code,
                                    "response_data": response_data,
                                    "endpoint": endpoint,
                                },
                                error="Missing access token in refresh response",
                            )

                    elif response.status_code == 401:
                        error_detail = response_data.get("detail", "Token invalid")
                        return TestResult(
                            success=False,
                            message=f"Token refresh failed: {error_detail}",
                            data={
                                "status_code": response.status_code,
                                "response_data": response_data,
                                "endpoint": endpoint,
                                "refresh_token_invalid": True,
                            },
                            error=f"HTTP 401: {error_detail}",
                        )

                except Exception as e:
                    logger.debug(f"Error testing refresh endpoint {endpoint}: {e}")
                    continue

            return TestResult(
                success=False,
                message="All token refresh endpoints failed or not found",
                data={"tested_endpoints": refresh_endpoints},
                error="No working refresh endpoint found",
            )

        except Exception as e:
            logger.exception(f"Token refresh test error: {e}")
            return TestResult(
                success=False,
                message=f"Token refresh test error: {str(e)}",
                data={"exception_type": type(e).__name__},
                error=str(e),
            )

    def _test_token_blacklisting_fixed(self, email: str) -> TestResult:
        """
        FIXED: Test token blacklisting via logout endpoint with proper token handling.
        Creates fresh tokens specifically for blacklisting test.
        """
        try:
            from django.contrib.auth import get_user_model
            from rest_framework_simplejwt.tokens import RefreshToken

            User = get_user_model()

            try:
                test_user = User.objects.get(email=email)
            except User.DoesNotExist:
                return TestResult(
                    success=False,
                    message=f"Test user with email {email} not found",
                    data={"email": email},
                    error="User does not exist",
                )

            # Create fresh tokens specifically for blacklisting test
            fresh_refresh = RefreshToken.for_user(test_user)
            fresh_access_token = str(fresh_refresh.access_token)
            fresh_refresh_token = str(fresh_refresh)

            logger.debug(f"Created fresh tokens for blacklisting test: user_id={test_user.id}")

            logout_endpoints = [
                "/api/v1/auth/logout/",
                "/api/v1/users/auth/logout/",
                "/api/v1/auth/jwt/logout/",
            ]

            # Try each logout endpoint
            for logout_url in logout_endpoints:
                try:
                    logger.debug(f"Testing logout endpoint: {logout_url}")
                    response = self.client.post(
                        logout_url,
                        data=json.dumps({"refresh": fresh_refresh_token}),
                        content_type="application/json",
                        HTTP_AUTHORIZATION=f"Bearer {fresh_access_token}",
                    )

                    if response.status_code == 404:
                        continue

                    if response.status_code == 200:
                        # Test if token is actually blacklisted by trying to refresh it
                        refresh_test_response = self.client.post(
                            f"{self.base_url}/auth/jwt/refresh/",
                            data=json.dumps({"refresh": fresh_refresh_token}),
                            content_type="application/json",
                        )

                        # Token should be blacklisted now, so refresh should fail
                        if refresh_test_response.status_code == 401:
                            refresh_error_data = {}
                            try:
                                refresh_error_data = (
                                    json.loads(refresh_test_response.content) if refresh_test_response.content else {}
                                )
                            except Exception:
                                pass

                            # Check if error indicates blacklisting
                            error_detail = refresh_error_data.get("detail", "").lower()
                            if "blacklist" in error_detail or "invalid" in error_detail:
                                return TestResult(
                                    success=True,
                                    message="Token blacklisting working correctly",
                                    data={
                                        "blacklisted": True,
                                        "logout_url": logout_url,
                                        "logout_status_code": response.status_code,
                                        "refresh_test_status": refresh_test_response.status_code,
                                        "refresh_error_detail": error_detail,
                                        "user_id": test_user.id,
                                    },
                                )

                        # If refresh still works, blacklisting failed
                        elif refresh_test_response.status_code == 200:
                            return TestResult(
                                success=False,
                                message="Token blacklisting failed - token still works after logout",
                                data={
                                    "logout_url": logout_url,
                                    "logout_status_code": response.status_code,
                                    "refresh_still_works": True,
                                    "user_id": test_user.id,
                                },
                                error="Token blacklisting mechanism not working",
                            )

                        # Unexpected refresh response
                        else:
                            return TestResult(
                                success=False,
                                message=f"Unexpected refresh response after logout: {refresh_test_response.status_code}",
                                data={
                                    "logout_url": logout_url,
                                    "logout_status_code": response.status_code,
                                    "refresh_test_status": refresh_test_response.status_code,
                                },
                                error="Unexpected behavior during blacklist verification",
                            )

                    elif response.status_code == 401:
                        response_data = {}
                        try:
                            response_data = json.loads(response.content) if response.content else {}
                        except Exception:
                            response_data = {"raw_content": response.content.decode() if response.content else None}

                        return TestResult(
                            success=False,
                            message="Authentication failed during logout",
                            data={
                                "status_code": response.status_code,
                                "response_data": response_data,
                                "logout_url": logout_url,
                                "user_id": test_user.id,
                            },
                            error=f"HTTP 401: {response_data.get('detail', 'Authentication failed')}",
                        )

                except Exception as e:
                    logger.debug(f"Error testing logout endpoint {logout_url}: {e}")
                    continue

            return TestResult(
                success=False,
                message="All logout endpoints failed or not found",
                data={"tested_endpoints": logout_endpoints},
                error="No working logout endpoint found",
            )

        except Exception as e:
            logger.exception(f"Token blacklisting test failed: {e}")
            return TestResult(
                success=False,
                message=f"Token blacklisting test failed: {str(e)}",
                data={"exception_type": type(e).__name__},
                error=str(e),
            )

    def _test_jwt_settings_validation_fixed(self) -> TestResult:
        """
        FIXED: Test JWT settings and configuration with accurate INSTALLED_APPS checking.
        """
        try:
            from django.conf import settings

            jwt_settings = {}
            jwt_issues = []
            jwt_warnings = []

            # Check if JWT settings exist
            if hasattr(settings, "SIMPLE_JWT"):
                jwt_settings = settings.SIMPLE_JWT

                # Check important JWT settings
                important_settings = [
                    "ACCESS_TOKEN_LIFETIME",
                    "REFRESH_TOKEN_LIFETIME",
                    "ALGORITHM",
                    "SIGNING_KEY",
                ]

                for setting_name in important_settings:
                    if setting_name in jwt_settings:
                        jwt_settings[f"has_{setting_name.lower()}"] = True
                    else:
                        jwt_issues.append(f"Missing {setting_name}")

                # FIXED: More accurate blacklist checking
                installed_apps = getattr(settings, "INSTALLED_APPS", [])
                blacklist_apps = [app for app in installed_apps if "token_blacklist" in app or "blacklist" in app]

                if blacklist_apps:
                    jwt_settings["blacklist_enabled"] = True
                    jwt_settings["blacklist_apps"] = blacklist_apps
                else:
                    jwt_warnings.append("Token blacklist app not found in INSTALLED_APPS")

                # Check rotation settings
                rotate_tokens = jwt_settings.get("ROTATE_REFRESH_TOKENS", False)
                blacklist_after_rotation = jwt_settings.get("BLACKLIST_AFTER_ROTATION", False)

                if rotate_tokens and not blacklist_after_rotation:
                    jwt_warnings.append("ROTATE_REFRESH_TOKENS is True but BLACKLIST_AFTER_ROTATION is False")

                # Check algorithm security
                algorithm = jwt_settings.get("ALGORITHM", "")
                if algorithm and algorithm.startswith("HS"):
                    jwt_warnings.append(f"Using HMAC algorithm ({algorithm}) - consider RS256 for production")

            else:
                jwt_issues.append("SIMPLE_JWT settings not found")

            # Determine overall success
            success = len(jwt_issues) == 0

            return TestResult(
                success=success,
                message=f"JWT settings validation: {len(jwt_issues)} issues, {len(jwt_warnings)} warnings",
                data={
                    "jwt_configured": hasattr(settings, "SIMPLE_JWT"),
                    "settings_found": len(jwt_settings),
                    "issues": jwt_issues,
                    "warnings": jwt_warnings,
                    "blacklist_apps_found": jwt_settings.get("blacklist_apps", []),
                    "jwt_settings_summary": {
                        k: str(v)
                        for k, v in jwt_settings.items()
                        if not k.startswith("SIGNING") and not isinstance(v, list)
                    },
                },
                error="; ".join(jwt_issues) if jwt_issues else None,
            )

        except Exception as e:
            logger.exception(f"JWT settings validation error: {e}")
            return TestResult(
                success=False,
                message=f"JWT settings validation error: {str(e)}",
                data={"exception_type": type(e).__name__},
                error=str(e),
            )

    def _create_test_user(self, email: str) -> TestResult:
        """Create test user for JWT testing."""
        try:
            from django.contrib.auth import get_user_model

            User = get_user_model()

            # Clean up existing test user
            deleted_count, _ = User.objects.filter(email=email).delete()
            if deleted_count > 0:
                logger.debug(f"Deleted {deleted_count} existing test users with email {email}")

            # Create new test user
            user = User.objects.create_user(
                email=email,
                password=self.test_password,
                first_name="JWT",
                last_name="Test",
                is_active=True,
            )

            # Try to set email verification if field exists
            try:
                if hasattr(user, "is_email_verified"):
                    user.is_email_verified = True
                    user.save()
            except Exception as e:
                logger.debug(f"Could not set email verification: {e}")

            self.current_test_user = user

            return TestResult(
                success=True,
                message="Test user created successfully",
                data={
                    "user_id": user.id,
                    "email": user.email,
                    "is_active": user.is_active,
                    "deleted_previous": deleted_count,
                },
            )

        except Exception as e:
            logger.exception(f"Failed to create test user: {e}")
            return TestResult(
                success=False,
                message=f"Failed to create test user: {str(e)}",
                data={"exception_type": type(e).__name__},
                error=str(e),
            )

    def _cleanup_test_user(self, email: str) -> TestResult:
        """Clean up test user after JWT testing."""
        try:
            from django.contrib.auth import get_user_model

            User = get_user_model()

            cleanup_emails = [email, "temp.logout@test.com"]
            total_deleted = 0

            for cleanup_email in cleanup_emails:
                deleted_count, _ = User.objects.filter(email=cleanup_email).delete()
                total_deleted += deleted_count

            self.current_test_user = None

            return TestResult(
                success=True,
                message=f"Test user cleanup completed ({total_deleted} users deleted)",
                data={"deleted_count": total_deleted, "email": email, "cleanup_emails": cleanup_emails},
            )

        except Exception as e:
            logger.exception(f"Failed to cleanup test user: {e}")
            return TestResult(
                success=False,
                message=f"Failed to cleanup test user: {str(e)}",
                data={"exception_type": type(e).__name__},
                error=str(e),
            )

    def _test_protected_endpoint_access(self, access_token: str) -> TestResult:
        """Test access to a protected endpoint using JWT."""
        try:
            protected_endpoints = [
                f"{self.base_url}/users/profile/",
                f"{self.base_url}/auth/user/",
                f"{self.base_url}/users/me/",
            ]

            for endpoint in protected_endpoints:
                try:
                    logger.debug(f"Testing protected endpoint: {endpoint}")
                    response = self.client.get(
                        endpoint,
                        HTTP_AUTHORIZATION=f"Bearer {access_token}",
                    )

                    if response.status_code == 404:
                        continue

                    if response.status_code == 200:
                        try:
                            response_data = json.loads(response.content) if response.content else {}
                            return TestResult(
                                success=True,
                                message=f"Protected endpoint access successful via {endpoint}",
                                data={
                                    "status_code": response.status_code,
                                    "user_data": response_data,
                                    "endpoint": endpoint,
                                    "authentication_working": True,
                                },
                            )
                        except json.JSONDecodeError:
                            return TestResult(
                                success=True,
                                message=f"Protected endpoint accessible (non-JSON response) via {endpoint}",
                                data={"status_code": response.status_code, "endpoint": endpoint},
                            )

                    elif response.status_code == 401:
                        response_data = {}
                        try:
                            response_data = json.loads(response.content) if response.content else {}
                        except Exception:
                            response_data = {"raw_content": response.content.decode() if response.content else None}

                        return TestResult(
                            success=False,
                            message=f"Protected endpoint authentication failed: {response_data.get('detail', 'Unknown error')}",
                            data={
                                "status_code": response.status_code,
                                "response_data": response_data,
                                "endpoint": endpoint,
                                "diagnosis": "Check JWT settings and token validation",
                            },
                            error=f"HTTP 401: {response_data.get('detail', 'Authentication failed')}",
                        )

                except Exception as e:
                    logger.debug(f"Error testing protected endpoint {endpoint}: {e}")
                    continue

            return TestResult(
                success=False,
                message="All protected endpoints failed or not found",
                data={"tested_endpoints": protected_endpoints},
                error="No working protected endpoint found",
            )

        except Exception as e:
            logger.exception(f"Protected endpoint access error: {e}")
            return TestResult(
                success=False,
                message=f"Protected endpoint access error: {str(e)}",
                data={"exception_type": type(e).__name__},
                error=str(e),
            )

    def _test_user_authentication_endpoints(self, email: str) -> TestResult:
        """Test various user authentication endpoints."""
        try:
            endpoints_to_test = [
                {
                    "url": f"{self.base_url}/auth/register/",
                    "method": "POST",
                    "data": {
                        "email": f"test.register.{email}",
                        "password": self.test_password,
                        "first_name": "Test",
                        "last_name": "Register",
                    },
                    "expected_status": [201, 400],  # 400 if user already exists
                    "name": "registration",
                },
            ]

            results = {}

            for endpoint_test in endpoints_to_test:
                try:
                    if endpoint_test["method"] == "POST":
                        response = self.client.post(
                            endpoint_test["url"],
                            data=json.dumps(endpoint_test["data"]),
                            content_type="application/json",
                        )
                    else:
                        response = self.client.get(endpoint_test["url"])

                    if response.status_code in endpoint_test["expected_status"]:
                        results[endpoint_test["name"]] = {
                            "success": True,
                            "status_code": response.status_code,
                            "url": endpoint_test["url"],
                        }
                    elif response.status_code == 404:
                        results[endpoint_test["name"]] = {
                            "success": False,
                            "status_code": 404,
                            "url": endpoint_test["url"],
                            "error": "Endpoint not found",
                        }
                    else:
                        results[endpoint_test["name"]] = {
                            "success": False,
                            "status_code": response.status_code,
                            "url": endpoint_test["url"],
                            "error": f"Unexpected status code",
                        }

                except Exception as e:
                    results[endpoint_test["name"]] = {"success": False, "error": str(e), "url": endpoint_test["url"]}

            successful_tests = sum(1 for result in results.values() if result.get("success", False))
            total_tests = len(results)

            return TestResult(
                success=successful_tests > 0,
                message=f"Authentication endpoints tested: {successful_tests}/{total_tests} working",
                data={
                    "endpoints_tested": total_tests,
                    "endpoints_working": successful_tests,
                    "detailed_results": results,
                },
            )

        except Exception as e:
            logger.exception(f"User authentication endpoints test error: {e}")
            return TestResult(
                success=False,
                message=f"User authentication endpoints test error: {str(e)}",
                data={"exception_type": type(e).__name__},
                error=str(e),
            )


def get_logger():
    """Get properly configured logger for JWT auth testing."""
    logger = logging.getLogger("jwt_auth_tester")

    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


jwt_logger = get_logger()
