"""MailerSend API mailer implementation."""
import requests
import time
import re
from typing import List, Dict, Any
from backend.mailer.base import BaseMailer


class MailerSendMailer(BaseMailer):
    """MailerSend API mailer."""
    
    API_URL = "https://api.mailersend.com/v1/email"
    MAX_RETRIES = 3
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.api_token = config.get('api_token', '')
        self.request_timeout = config.get('request_timeout', 15)
    
    def validate_config(self) -> bool:
        """Validate MailerSend configuration."""
        return bool(self.api_token and len(self.api_token) > 10)
    
    def _extract_text_from_html(self, html: str) -> str:
        """Extract plain text from HTML for fallback."""
        # Remove style and script blocks
        text = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
        # Remove all HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    
    def send(
        self,
        subject: str,
        html_body: str,
        recipients: List[str],
        sender_email: str,
        sender_name: str = "ASAP Crew"
    ) -> Dict[str, Any]:
        """
        Send email via MailerSend API.
        
        Handles rate limiting (429) with exponential backoff.
        """
        if not recipients:
            return {'success': False, 'message': 'No recipients provided'}
        
        if not self.validate_config():
            return {'success': False, 'message': 'Invalid MailerSend configuration'}
        
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        
        # Clean recipients
        clean_recipients = [r.strip() for r in recipients if r and isinstance(r, str)]
        if not clean_recipients:
            return {'success': False, 'message': 'No valid recipients after cleaning'}
        
        # Extract plain text version
        text_body = self._extract_text_from_html(html_body)
        
        # Build payload: use first recipient as "to", rest as "bcc"
        if len(clean_recipients) == 1:
            payload = {
                "from": {"email": sender_email, "name": sender_name},
                "to": [{"email": clean_recipients[0]}],
                "subject": subject.strip(),
                "html": html_body.strip(),
                "text": text_body,
            }
        else:
            payload = {
                "from": {"email": sender_email, "name": sender_name},
                "to": [{"email": clean_recipients[0]}],
                "bcc": [{"email": email} for email in clean_recipients[1:]],
                "subject": subject.strip(),
                "html": html_body.strip(),
                "text": text_body,
            }
        
        # Retry logic with exponential backoff
        for attempt in range(self.MAX_RETRIES):
            try:
                response = requests.post(
                    self.API_URL,
                    headers=headers,
                    json=payload,
                    timeout=self.request_timeout
                )
                
                # Success codes
                if response.status_code in (200, 202):
                    return {
                        'success': True,
                        'message': f'Successfully sent to {len(clean_recipients)} recipient(s)',
                        'status_code': response.status_code
                    }
                
                # Rate limiting (429) or conflict (409)
                if response.status_code in (429, 409):
                    retry_after = int(response.headers.get("Retry-After", 60))
                    if attempt < self.MAX_RETRIES - 1:
                        wait_time = retry_after * (2 ** attempt)  # Exponential backoff
                        time.sleep(wait_time)
                        continue
                    return {
                        'success': False,
                        'message': f'Rate limited after {self.MAX_RETRIES} attempts',
                        'status_code': response.status_code
                    }
                
                # Other errors
                return {
                    'success': False,
                    'message': f'MailerSend API error {response.status_code}: {response.text[:200]}',
                    'status_code': response.status_code
                }
                
            except requests.Timeout:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {
                    'success': False,
                    'message': f'Request timeout after {self.MAX_RETRIES} attempts'
                }
            except requests.RequestException as e:
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {
                    'success': False,
                    'message': f'Request failed: {str(e)}'
                }
        
        return {
            'success': False,
            'message': 'Failed after all retry attempts'
        }

