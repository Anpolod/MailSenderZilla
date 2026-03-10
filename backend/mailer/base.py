"""Base mailer interface."""
from abc import ABC, abstractmethod
from typing import List, Dict, Any


class BaseMailer(ABC):
    """Abstract base class for mailer implementations."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize mailer with configuration.
        
        Args:
            config: Dictionary with mailer-specific settings
        """
        self.config = config
    
    @abstractmethod
    def send(
        self,
        subject: str,
        html_body: str,
        recipients: List[str],
        sender_email: str,
        sender_name: str = "ASAP Crew"
    ) -> Dict[str, Any]:
        """
        Send email to recipients.
        
        Args:
            subject: Email subject
            html_body: HTML email body
            recipients: List of recipient email addresses
            sender_email: Sender email address
            sender_name: Sender display name
            
        Returns:
            Dictionary with 'success' (bool) and 'message' (str)
        """
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """
        Validate mailer configuration.
        
        Returns:
            True if configuration is valid
        """
        pass

