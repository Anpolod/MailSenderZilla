"""Gmail SMTP mailer implementation."""
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List, Dict, Any
from datetime import datetime, time as dt_time, timedelta
from backend.mailer.base import BaseMailer


class GmailMailer(BaseMailer):
    """Gmail SMTP mailer (OAuth/App-Password support)."""
    
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587  # TLS
    SMTP_PORT_SSL = 465  # SSL (alternative)
    MAX_BCC_PER_EMAIL = 90  # Gmail limit
    DAILY_LIMIT = 2000  # Gmail daily sending limit
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.app_password = config.get('app_password', '')
        self.username = config.get('username', '')  # For OAuth: client_id, client_secret, etc.
        self.use_ssl = config.get('use_ssl', False)
        self.sent_today = config.get('sent_today', 0)
        self.last_reset_date = config.get('last_reset_date', datetime.now().date())
    
    def validate_config(self) -> bool:
        """Validate Gmail configuration."""
        # For App Password authentication
        if self.app_password:
            return len(self.app_password) >= 16
        # TODO: Add OAuth validation when implemented
        return False
    
    def _check_daily_limit(self) -> bool:
        """Check if daily limit is reached. Reset at 00:05 local time."""
        today = datetime.now().date()
        
        # Reset counter if new day (or after 00:05)
        now = datetime.now()
        if today != self.last_reset_date:
            self.sent_today = 0
            self.last_reset_date = today
            return True
        
        # Check if we've reached the limit
        return self.sent_today < self.DAILY_LIMIT
    
    def _get_reset_time(self) -> datetime:
        """Get next reset time (00:05 local time)."""
        today = datetime.now().date()
        tomorrow = today + timedelta(days=1)
        return datetime.combine(tomorrow, dt_time(0, 5))  # 00:05
    
    def send(
        self,
        subject: str,
        html_body: str,
        recipients: List[str],
        sender_email: str,
        sender_name: str = "ASAP Crew"
    ) -> Dict[str, Any]:
        """
        Send email via Gmail SMTP.
        
        Respects 90 BCC per email and 2000 emails/day limits.
        """
        if not recipients:
            return {'success': False, 'message': 'No recipients provided'}
        
        if not self.validate_config():
            return {'success': False, 'message': 'Invalid Gmail configuration'}
        
        # Check daily limit
        if not self._check_daily_limit():
            reset_time = self._get_reset_time()
            return {
                'success': False,
                'message': f'Daily limit {self.DAILY_LIMIT} reached. Resets at {reset_time.strftime("%Y-%m-%d %H:%M")}',
                'reset_time': reset_time.isoformat()
            }
        
        # Clean recipients
        clean_recipients = [r.strip() for r in recipients if r and isinstance(r, str)]
        if not clean_recipients:
            return {'success': False, 'message': 'No valid recipients after cleaning'}
        
        # Split into batches if exceeding BCC limit
        if len(clean_recipients) > self.MAX_BCC_PER_EMAIL + 1:
            # First recipient as "to", up to 90 as "bcc"
            batches = []
            for i in range(0, len(clean_recipients), self.MAX_BCC_PER_EMAIL + 1):
                batch = clean_recipients[i:i + self.MAX_BCC_PER_EMAIL + 1]
                batches.append(batch)
        else:
            batches = [clean_recipients]
        
        # Send each batch
        total_sent = 0
        errors = []
        
        for batch in batches:
            try:
                if len(batch) == 1:
                    to_emails = batch
                    bcc_emails = []
                else:
                    to_emails = [batch[0]]
                    bcc_emails = batch[1:]
                
                # Create message
                msg = MIMEMultipart('alternative')
                msg['From'] = f"{sender_name} <{sender_email}>"
                msg['To'] = to_emails[0]
                msg['Subject'] = subject.strip()
                
                if bcc_emails:
                    msg['Bcc'] = ', '.join(bcc_emails)
                
                # Add HTML part
                html_part = MIMEText(html_body, 'html', 'utf-8')
                msg.attach(html_part)
                
                # Connect and send
                port = self.SMTP_PORT_SSL if self.use_ssl else self.SMTP_PORT
                
                if self.use_ssl:
                    server = smtplib.SMTP_SSL(self.SMTP_SERVER, port)
                else:
                    server = smtplib.SMTP(self.SMTP_SERVER, port)
                    server.starttls()
                
                # Authenticate
                if self.app_password:
                    server.login(sender_email, self.app_password)
                # TODO: Add OAuth authentication here
                
                # Send
                all_recipients = to_emails + bcc_emails
                server.sendmail(sender_email, all_recipients, msg.as_string())
                server.quit()
                
                total_sent += len(batch)
                self.sent_today += len(batch)
                
            except smtplib.SMTPException as e:
                error_msg = f'SMTP error: {str(e)}'
                errors.append(error_msg)
            except Exception as e:
                error_msg = f'Error sending batch: {str(e)}'
                errors.append(error_msg)
        
        if errors:
            return {
                'success': len(errors) < len(batches),
                'message': f'Sent {total_sent} emails. Errors: {"; ".join(errors)}',
                'sent_count': total_sent
            }
        
        return {
            'success': True,
            'message': f'Successfully sent to {total_sent} recipient(s)',
            'sent_count': total_sent
        }
