"""Utils initialization module."""


from .oauth_validators import GoogleOAuthValidator

# # Import only what's actually needed to avoid conflicts
# try:
#     from .oauth_validators import GoogleOAuthValidator
#     __all__ = ["GoogleOAuthValidator"]
# except ImportError:
#     __all__ = []
#
# # Lazy import for EmailTester to avoid Django initialization issues
# def get_email_tester():
#     """Factory function for EmailTester with lazy import."""
#     from .email_testing import EmailTester
#     return EmailTester
#
# # Don't import EmailTester at module level to avoid Django setup issues
# # Instead, provide factory function for accessing it
