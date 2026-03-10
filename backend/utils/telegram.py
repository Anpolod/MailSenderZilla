"""Telegram notification utility."""
import requests
from typing import Optional


def send_telegram_message(
    bot_token: str,
    chat_id: str,
    message: str,
    timeout: int = 10
) -> bool:
    """
    Send message to Telegram.
    
    Args:
        bot_token: Telegram bot token
        chat_id: Telegram chat ID
        message: Message text
        timeout: Request timeout in seconds
        
    Returns:
        True if sent successfully, False otherwise
    """
    if not bot_token or not chat_id:
        return False
    
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{bot_token}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": message
            },
            timeout=timeout
        )
        response.raise_for_status()
        return True
    except Exception:
        return False

