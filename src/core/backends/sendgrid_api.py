"""
SendGrid Web API Backend for Django
Обходит SMTP блокировку используя HTTP API SendGrid
"""

import logging
from typing import List

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage

logger = logging.getLogger(__name__)

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, From, To, Subject, PlainTextContent, HtmlContent
    SENDGRID_AVAILABLE = True
except ImportError:
    logger.error("SendGrid library not installed. Run: pip install sendgrid")
    SENDGRID_AVAILABLE = False


class SendGridAPIBackend(BaseEmailBackend):
    """
    Email backend that uses SendGrid Web API instead of SMTP.
    Perfect for DigitalOcean and other providers that block SMTP ports.
    
    Usage in settings:
        EMAIL_BACKEND = 'src.core.backends.sendgrid_api.SendGridAPIBackend'
        SENDGRID_API_KEY = 'SG.your_api_key_here'
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        if not SENDGRID_AVAILABLE:
            logger.error("SendGrid SDK not available")
            self.sg = None
            return
            
        # Get API key from settings
        api_key = getattr(settings, 'SENDGRID_API_KEY', None)
        if not api_key:
            # Fallback to EMAIL_HOST_PASSWORD for compatibility
            api_key = getattr(settings, 'EMAIL_HOST_PASSWORD', None)
            
        if api_key and api_key.startswith('SG.'):
            try:
                self.sg = sendgrid.SendGridAPIClient(api_key=api_key)
                logger.info("SendGrid Web API backend initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize SendGrid client: {e}")
                self.sg = None
        else:
            logger.error("Invalid or missing SendGrid API key. Key should start with 'SG.'")
            self.sg = None

    def send_messages(self, email_messages: List[EmailMessage]) -> int:
        """
        Send emails using SendGrid Web API.
        
        Args:
            email_messages: List of Django EmailMessage objects
            
        Returns:
            Number of successfully sent emails
        """
        if not self.sg:
            if not self.fail_silently:
                raise RuntimeError("SendGrid client not initialized")
            return 0

        sent_count = 0
        
        for message in email_messages:
            try:
                success = self._send_single_message(message)
                if success:
                    sent_count += 1
                    
            except Exception as e:
                logger.error(f"Failed to send email '{message.subject}': {e}")
                if not self.fail_silently:
                    raise e
                    
        logger.info(f"SendGrid Web API: {sent_count}/{len(email_messages)} emails sent successfully")
        return sent_count

    def _send_single_message(self, message: EmailMessage) -> bool:
        """
        Send single email message via SendGrid Web API.
        
        Args:
            message: Django EmailMessage object
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            # Create SendGrid Mail object
            mail = Mail()
            
            # Set from email
            from_email = message.from_email or getattr(settings, 'DEFAULT_FROM_EMAIL', '')
            mail.from_email = From(from_email)
            
            # Set recipients
            to_list = []
            if hasattr(message, 'to') and message.to:
                for email in message.to:
                    to_list.append(To(email))
            mail.to = to_list
            
            # Set subject
            mail.subject = Subject(message.subject)
            
            # Set content
            content_list = []
            
            # Plain text content
            if message.body:
                content_list.append(PlainTextContent(message.body))
                
            # HTML content (if available)
            if hasattr(message, 'alternatives') and message.alternatives:
                for content, mimetype in message.alternatives:
                    if mimetype == 'text/html':
                        content_list.append(HtmlContent(content))
                        break
            
            mail.content = content_list if content_list else [PlainTextContent(message.body or '')]
            
            # Send via SendGrid API
            response = self.sg.send(mail)
            
            # Check response status
            if response.status_code in [200, 201, 202]:
                logger.info(f"Email sent successfully: '{message.subject}' to {message.to}")
                return True
            else:
                logger.error(f"SendGrid API error: HTTP {response.status_code}")
                if hasattr(response, 'body'):
                    logger.error(f"Response body: {response.body}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending email via SendGrid API: {e}")
            if not self.fail_silently:
                raise e
            return False

    def open(self) -> bool:
        """
        Open connection (not needed for Web API).
        """
        return True

    def close(self):
        """
        Close connection (not needed for Web API).
        """
        pass


# Fallback backend if SendGrid is not available
class ConsoleFallbackBackend(BaseEmailBackend):
    """
    Fallback backend that outputs emails to console if SendGrid is not available.
    """
    
    def send_messages(self, email_messages):
        logger.warning("Using console fallback backend - emails will not be delivered")
        for message in email_messages:
            print(f"\n--- EMAIL ---")
            print(f"From: {message.from_email}")
            print(f"To: {message.to}")
            print(f"Subject: {message.subject}")
            print(f"Body:\n{message.body}")
            print(f"--- END EMAIL ---\n")
        return len(email_messages)
