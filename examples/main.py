#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import warnings
import logging
import os
import re
import sqlite3
import importlib
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any, Optional

import pandas as pd
import requests
from email_sender import confirm_email

# Опциональный импорт для .env файла без жёсткой зависимости (исправляет предупреждение линтера)
try:
    _dotenv_module = importlib.import_module("dotenv")
    load_dotenv = getattr(_dotenv_module, "load_dotenv", None)
    DOTENV_AVAILABLE = callable(load_dotenv)
except Exception:
    load_dotenv = None
    DOTENV_AVAILABLE = False

# Загружаем переменные окружения из .env файла
if DOTENV_AVAILABLE:
    load_dotenv()

# --- отключаем FutureWarning от pandas, но всё равно приводим типы ---
warnings.filterwarnings("ignore", category=FutureWarning, module="pandas")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('main.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Constants
DEFAULT_DAILY_LIMIT = 5000
MAX_RETRIES = 3
REQUEST_TIMEOUT = 15


# ---------- УТИЛИТЫ ----------------------------------------------------------
def fix_common_email_issues(email: str) -> str:
    """Fix common email formatting issues."""
    if not email or not isinstance(email, str):
        return email
    
    email = email.strip()
    
    # Common replacements: Excel or other tools sometimes replace @ with other characters
    # Replace common patterns that should be @
    replacements = [
        (r'\+AEA-', '@'),           # polandy79+AEA-gmail.com -> polandy79@gmail.com
        (r'\+AT\+', '@'),           # email+AT+domain.com -> email@domain.com
        (r'\[at\]', '@'),           # email[at]domain.com -> email@domain.com
        (r'\(at\)', '@'),           # email(at)domain.com -> email@domain.com
        (r'\s+at\s+', '@'),         # email at domain.com -> email@domain.com
        (r'\s*@\s*', '@'),          # Remove spaces around @
    ]
    
    for pattern, replacement in replacements:
        email = re.sub(pattern, replacement, email, flags=re.IGNORECASE)
    
    # Remove any remaining spaces
    email = email.replace(' ', '')
    
    return email


def is_valid_email(email: str) -> bool:
    """Validate email address format."""
    if not email or not isinstance(email, str):
        return False
    email = email.strip()
    
    # Check if @ symbol is present
    if '@' not in email:
        return False
    
    # More robust email validation pattern
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def safe_telegram_message(token: str, chat_id: str, msg: str) -> None:
    """Send Telegram message safely, catching all exceptions."""
    if not token or not chat_id:
        logger.warning("Telegram token or chat_id is empty, skipping message")
        return
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": msg},
            timeout=10,
        )
        response.raise_for_status()
        logger.debug(f"Telegram message sent: {msg[:50]}...")
    except requests.RequestException as exc:
        logger.error(f"Telegram error → {exc}")
    except Exception as exc:
        logger.error(f"Unexpected Telegram error → {exc}")


def send_email_mailersend(
    subject: str,
    body: str,
    bcc: List[str],
    sender_email: str,
    api_token: str,
    tg_token: str,
    tg_chat: str,
) -> None:
    """Send email via MailerSend API with retry logic."""
    if not bcc:
        raise ValueError("No recipients to send to (empty bcc list)")
    
    if not subject or not body:
        raise ValueError("Subject and body cannot be empty")
    
    if not sender_email or not api_token:
        raise ValueError("Sender email and API token are required")

    url = "https://api.mailersend.com/v1/email"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    # Send emails directly to recipients without copying to sender_email
    # If single recipient, use "to". If multiple, use "to" for first and "bcc" for rest to hide addresses
    # Strip HTML tags for plain text version (fallback for email clients without HTML support)
    # First remove style and script blocks completely
    text_body = re.sub(r'<style[^>]*>.*?</style>', '', body, flags=re.DOTALL | re.IGNORECASE)
    text_body = re.sub(r'<script[^>]*>.*?</script>', '', text_body, flags=re.DOTALL | re.IGNORECASE)
    # Then remove all remaining HTML tags
    text_body = re.sub(r'<[^>]+>', '', text_body)
    # Normalize whitespace
    text_body = re.sub(r'\s+', ' ', text_body).strip()
    
    # Clean and validate recipient emails
    recipient_emails = [e.strip() for e in bcc if e and isinstance(e, str) and e.strip()]
    
    if not recipient_emails:
        error_msg = "No valid recipients after filtering"
        logger.error(error_msg)
        raise ValueError(error_msg)
    
    # If single recipient, send directly to them
    if len(recipient_emails) == 1:
        payload = {
            "from": {"email": sender_email, "name": "ASAP Crew"},
            "to": [{"email": recipient_emails[0]}],
            "subject": subject.strip(),
            "html": body.strip(),
            "text": text_body,  # Plain text version extracted from HTML
        }
    else:
        # If multiple recipients, use first as "to" and rest as "bcc" to hide addresses from each other
        payload = {
            "from": {"email": sender_email, "name": "ASAP Crew"},
            "to": [{"email": recipient_emails[0]}],
            "bcc": [{"email": email} for email in recipient_emails[1:]],
            "subject": subject.strip(),
            "html": body.strip(),
            "text": text_body,  # Plain text version extracted from HTML
        }
    
    logger.info(f"Preparing to send email via MailerSend API")
    logger.info(f"Total recipients: {len(recipient_emails)}")
    logger.info(f"Subject: {subject[:100]}")
    logger.info(f"HTML body length: {len(body)} chars")
    logger.info(f"Text body length: {len(text_body)} chars")
    if len(recipient_emails) > 1:
        logger.debug(f"TO: {recipient_emails[0]}, BCC: {len(recipient_emails)-1} recipient(s)")
    else:
        logger.debug(f"TO: {recipient_emails[0]}")

    # Retry logic
    for attempt in range(MAX_RETRIES):
        try:
            logger.info(f"Sending email attempt {attempt + 1}/{MAX_RETRIES}")
            logger.debug(f"Request URL: {url}")
            logger.debug(f"Payload keys: {list(payload.keys())}")
            
            resp = requests.post(url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT)
            
            logger.info(f"MailerSend API response: Status {resp.status_code}")
            logger.debug(f"Response headers: {dict(resp.headers)}")
            logger.debug(f"Response body: {resp.text[:500]}")
            
            # Accept 200 or 202 as success
            if resp.status_code in (200, 202):
                logger.info(f"Successfully sent batch: {len(recipient_emails)} recipients")
                logger.info(f"MailerSend API response: Status {resp.status_code}, Response: {resp.text[:200]}")
                print(f"   ✅ MailerSend API responded: Status {resp.status_code}")
                if resp.text:
                    print(f"   📋 Response: {resp.text[:200]}")
                recipient_info = f"{len(recipient_emails)} recipient(s)" + (f" (1 TO, {len(recipient_emails)-1} BCC)" if len(recipient_emails) > 1 else "")
                safe_telegram_message(
                    tg_token, tg_chat,
                    f"📤 Sent batch: {recipient_info}. Status: {resp.status_code}"
                )
                return
            
            # Handle rate limiting
            if resp.status_code == 429:
                retry_after = int(resp.headers.get("Retry-After", 60))
                if attempt < MAX_RETRIES - 1:
                    logger.warning(f"Rate limited. Waiting {retry_after}s before retry {attempt + 1}/{MAX_RETRIES}")
                    time.sleep(retry_after)
                    continue
            
            err = f"❌ MailerSend error {resp.status_code}:\n{resp.text[:500]}"
            logger.error(err)
            safe_telegram_message(tg_token, tg_chat, err)
            raise RuntimeError(err)
            
        except requests.Timeout as exc:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"Request timeout. Retrying {attempt + 1}/{MAX_RETRIES}")
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            err = f"❌ MailerSend request timeout after {MAX_RETRIES} attempts: {exc}"
            safe_telegram_message(tg_token, tg_chat, err)
            raise
        except requests.RequestException as exc:
            if attempt < MAX_RETRIES - 1:
                logger.warning(f"Request failed. Retrying {attempt + 1}/{MAX_RETRIES}: {exc}")
                time.sleep(2 ** attempt)
                continue
            err = f"❌ MailerSend request failed after {MAX_RETRIES} attempts: {exc}"
            safe_telegram_message(tg_token, tg_chat, err)
            raise


def read_email_content(path: str) -> Tuple[str, str]:
    """Read email subject and HTML body from file."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Email content file not found: {path}")
    
    # Global email rendering preferences
    GLOBAL_FONT_SIZE_PX = 18  # Increase base font size by +2px from common defaults
    LOGO_SOURCE_URL = "https://imgur.com/PUn562O"  # Provided by user
    
    def to_direct_imgur_image(url: str) -> str:
        """
        Convert an Imgur page URL to a direct image URL for email embedding.
        Examples:
          https://imgur.com/abc123   -> https://i.imgur.com/abc123.png
          https://i.imgur.com/abc123.jpg -> stays as is
        """
        try:
            # If already i.imgur.com with an image extension, return as-is
            if re.search(r'i\.imgur\.com/.+\.(png|jpg|jpeg|gif|webp)$', url, flags=re.IGNORECASE):
                return url
            # Extract ID from common imgur page URLs
            m = re.search(r'imgur\.com/(?:gallery/|a/)?([A-Za-z0-9]+)', url, flags=re.IGNORECASE)
            if m:
                image_id = m.group(1)
                return f"https://i.imgur.com/{image_id}.png"
        except Exception:
            pass
        # Fallback: return original (may not render in some clients)
        return url
    
    LOGO_IMAGE_SRC = to_direct_imgur_image(LOGO_SOURCE_URL)
    
    def insert_global_styles(html: str) -> str:
        """
        Ensure a global font-size is applied across the email content, even if the template has its own styles.
        Inserts a <style> block into <head> if present; otherwise, injects at the top of the HTML.
        """
        styles = (
            "<style type=\"text/css\">"
            f"body, p, li, td, div, span {{ font-size: {GLOBAL_FONT_SIZE_PX}px !important; }}"
            "</style>"
        )
        # Try to find <head> for cleaner injection
        head_match = re.search(r'<head[^>]*>', html, flags=re.IGNORECASE)
        if head_match:
            insert_pos = head_match.end()
            return html[:insert_pos] + styles + html[insert_pos:]
        # Otherwise, try to insert before first <body>, or just prepend
        body_match = re.search(r'<body[^>]*>', html, flags=re.IGNORECASE)
        if body_match:
            return html[:body_match.start()] + styles + html[body_match.start():]
        return styles + html
    
    def insert_logo_block(html: str) -> str:
        """
        Inject a clickable logo block at the top of the email body.
        If <body> exists, insert right after it; otherwise prepend.
        """
        # Note: Many email clients prefer fixed sizes; adjust width/height if needed
        # Render logo as a plain image (no hyperlink).
        logo_block = (
            "<div style=\"text-align:center; margin: 0 0 16px 0;\">"
            f"<img src=\"{LOGO_IMAGE_SRC}\" alt=\"Company Logo\" "
            "style=\"display:inline-block; max-width: 220px; width: 100%; height: auto; border: 0;\"/>"
            "</div><!--__LOGO_END__-->"
        )
        try:
            body_tag_match = re.search(r'<body[^>]*>', html, flags=re.IGNORECASE)
            if body_tag_match:
                insert_pos = body_tag_match.end()
                return html[:insert_pos] + logo_block + html[insert_pos:]
            # If there's an html tag but no body tag, just prepend
            return logo_block + html
        except Exception:
            return logo_block + html
    
    def sanitize_and_restructure_body(html: str) -> str:
        """
        - Remove top header block with agency name / vacancies
        - Move Telegram CTA to top under logo
        - Remove bottom 'how to apply' and 'Contact: Kseniya'
        - Inline UNSUBSCRIBE link inside the specific sentence and remove footer unsubscribe
        """
        working = html
        
        # Helper to remove blocks containing specific phrases
        def remove_blocks_with_phrases(source_html: str, phrases: List[str]) -> str:
            result = source_html
            try:
                # Remove enclosing <div>...</div> that contains phrases
                pattern_div = re.compile(r'<div[^>]*>[\s\S]*?</div>', re.IGNORECASE)
                changed = True
                while changed:
                    changed = False
                    for m in list(pattern_div.finditer(result)):
                        block = m.group(0)
                        if any(p.lower() in block.lower() for p in phrases):
                            result = result[:m.start()] + result[m.end():]
                            changed = True
                            break
                # Remove enclosing <section>...</section>
                pattern_section = re.compile(r'<section[^>]*>[\s\S]*?</section>', re.IGNORECASE)
                changed = True
                while changed:
                    changed = False
                    for m in list(pattern_section.finditer(result)):
                        block = m.group(0)
                        if any(p.lower() in block.lower() for p in phrases):
                            result = result[:m.start()] + result[m.end():]
                            changed = True
                            break
                # Remove <table> blocks that contain phrases
                pattern_table = re.compile(r'<table[^>]*>[\s\S]*?</table>', re.IGNORECASE)
                changed = True
                while changed:
                    changed = False
                    for m in list(pattern_table.finditer(result)):
                        block = m.group(0)
                        if any(p.lower() in block.lower() for p in phrases):
                            result = result[:m.start()] + result[m.end():]
                            changed = True
                            break
                # Remove standalone paragraphs containing phrases
                pattern_p = re.compile(r'<p[^>]*>[\s\S]*?</p>', re.IGNORECASE)
                for m in list(pattern_p.finditer(result)):
                    block = m.group(0)
                    if any(p.lower() in block.lower() for p in phrases):
                        result = result.replace(block, '')
            except Exception:
                return source_html
            return result
        
        # 1) Remove header with agency name and vacancies
        working = remove_blocks_with_phrases(
            working,
            ["A.S.A.P.Marine Agency Ukraine", "Vacancies"]
        )
        
        # 2) Extract Telegram CTA block
        telegram_html = ""
        experience_html = ""
        try:
            # Prefer a <div> containing telegram words/links
            div_blocks = list(re.finditer(r'<div[^>]*>[\s\S]*?</div>', working, flags=re.IGNORECASE))
            for m in div_blocks:
                block = m.group(0)
                if re.search(r'(telegram|t\.me)', block, flags=re.IGNORECASE) or \
                   re.search(r'join\s+to\s+our\s+telegram', block, flags=re.IGNORECASE):
                    telegram_html = block
                    # Remove it from original position
                    working = working[:m.start()] + working[m.end():]
                    break
            # Fallback: paragraph containing telegram
            if not telegram_html:
                p_blocks = list(re.finditer(r'<p[^>]*>[\s\S]*?</p>', working, flags=re.IGNORECASE))
                for m in p_blocks:
                    block = m.group(0)
                    if re.search(r'(telegram|t\.me)', block, flags=re.IGNORECASE) or \
                       re.search(r'join\s+to\s+our\s+telegram', block, flags=re.IGNORECASE):
                        telegram_html = block
                        working = working[:m.start()] + working[m.end():]
                        break
            # Extract the "substantial experience" paragraph/div/li
            # Match common containers (<p>, <div>, <li>) that include the beginning of the sentence
            exp_pattern = re.compile(
                r'(<(?:p|div|li)[^>]*>[\s\S]*?If\s+you\s+have\s+substantial\s+experience\s+and\s+are\s+considering\s+changing\s+companies[\s\S]*?</(?:p|div|li)>)',
                flags=re.IGNORECASE
            )
            mexp = exp_pattern.search(working)
            if mexp:
                experience_html = mexp.group(1)
                working = working[:mexp.start()] + working[mexp.end():]
        except Exception:
            pass
        
        # 3) Remove bottom blocks: how to apply / Contact: Kseniya (narrowed matching)
        working = remove_blocks_with_phrases(
            working,
            ["how to apply", "Contact: Kseniya"]
        )
        # Aggressively strip any tag blocks that contain the exact "Contact: Kseniya"
        try:
            def remove_blocks_matching(inner_regex: str) -> None:
                nonlocal working
                tag_names = ["div", "p", "li", "section", "table", "tbody", "tr", "td", "th", "span", "font"]
                pattern_blocks = [
                    re.compile(fr'<{tn}[^>]*>[\s\S]*?</{tn}>', re.IGNORECASE) for tn in tag_names
                ]
                changed = True
                while changed:
                    changed = False
                    for pat in pattern_blocks:
                        for m in list(pat.finditer(working)):
                            block = m.group(0)
                            if re.search(inner_regex, block, flags=re.IGNORECASE):
                                working = working[:m.start()] + working[m.end():]
                                changed = True
                                break
                        if changed:
                            break
            # Remove any block containing the exact phrase
            remove_blocks_matching(r'Contact:\s*Kseniya')
            # Remove any residual inline occurrences
            working = re.sub(r'(?i)Contact:\s*Kseniya', '', working)
        except Exception:
            pass
        # Remove stop/alert emojis if present
        try:
            working = working.replace('🛑', '')
            working = working.replace('🔴', '')
        except Exception:
            pass
        # 4) Insert Telegram block after logo marker or at top of body
        if telegram_html:
            if "<!--__LOGO_END__-->" in working:
                insertion = "<!--__LOGO_END__-->" + telegram_html + (experience_html or "")
                working = working.replace("<!--__LOGO_END__-->", insertion)
            else:
                # Insert after <body>
                body_tag_match = re.search(r'<body[^>]*>', working, flags=re.IGNORECASE)
                if body_tag_match:
                    pos = body_tag_match.end()
                    working = working[:pos] + telegram_html + (experience_html or "") + working[pos:]
                else:
                    working = telegram_html + (experience_html or "") + working
        else:
            # If no Telegram block found, but we have the experience paragraph, place it after the logo or at top
            if experience_html:
                if "<!--__LOGO_END__-->" in working:
                    working = working.replace("<!--__LOGO_END__-->", "<!--__LOGO_END__-->" + experience_html)
                else:
                    body_tag_match = re.search(r'<body[^>]*>', working, flags=re.IGNORECASE)
                    if body_tag_match:
                        pos = body_tag_match.end()
                        working = working[:pos] + experience_html + working[pos:]
                    else:
                        working = experience_html + working
        # 5) Inline UNSUBSCRIBE link in the sentence and ensure no bullet/LI formatting
        try:
            unsubscribe_to = os.getenv("SENDER_EMAIL", "").strip() or "unsubscribe@example.com"
            mailto = (
                f"mailto:{unsubscribe_to}"
                "?subject=Unsubscribe"
                "&body=Please%20unsubscribe%20me%20from%20your%20mailing%20list."
            )
            # Replace first standalone "UNSUBSCRIBE" with a mailto link (covers different phrasings)
            working = re.sub(r'(?i)\bUNSUBSCRIBE\b', f'<a href="{mailto}">UNSUBSCRIBE</a>', working, count=1)
            # Also handle the explicit "reply with UNSUBSCRIBE" phrasing
            working = re.sub(r'(?i)(reply\s+with\s+)<a[^>]*>\s*UNSUBSCRIBE\s*</a>', rf'\1<a href="{mailto}">UNSUBSCRIBE</a>', working)
            working = re.sub(r'(?i)(reply\s+with\s+)UNSUBSCRIBE', rf'\1<a href="{mailto}">UNSUBSCRIBE</a>', working)
            # Convert LI containing that sentence into a P (to remove the bullet/red dot)
            # General convert: any <li> that contains the sentence -> <p> with inner HTML
            working = re.sub(r'(?is)<li([^>]*)>([\s\S]*?If\s+you\s+no\s+longer\s+wish\s+to\s+receive\s+emails[\s\S]*?)</li>', r'<p>\2</p>', working)
            # Also convert <li> that contains the (now linked) UNSUBSCRIBE word -> <p>
            working = re.sub(r'(?is)<li([^>]*)>([\s\S]*?<a[^>]*>\s*UNSUBSCRIBE\s*</a>[\s\S]*?)</li>', r'<p>\2</p>', working)
            # Remove common bullet characters at line starts inside tags for that sentence
            working = re.sub(
                r'(?is)>(\s*[•●▪▫‣∙🔴]\s*)(If\s+you\s+no\s+longer\s+wish\s+to\s+receive\s+emails[^<]*?)',
                r'>\2',
                working,
            )
            # Remove now-empty UL/OL wrappers (no li inside)
            working = re.sub(r'(?is)<ul[^>]*>\s*</ul>', '', working)
            working = re.sub(r'(?is)<ol[^>]*>\s*</ol>', '', working)
            # Remove any standalone footer UNSUBSCRIBE paragraph (if present from older templates)
            working = re.sub(
                r'(?is)<p[^>]*>\s*<a[^>]*>\s*UNSUBSCRIBE\s*</a>\s*</p>',
                '',
                working,
            )
        except Exception:
            pass
        
        return working
    
    subject, body, html_body, started_body, started_html = "", "", "", False, False
    try:
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
            lines = content.split('\n')
            
            # Поддержка чистых HTML-файлов без заголовков Subject:/HTML:/Body:
            is_pure_html = bool(re.search(r'<html', content, flags=re.IGNORECASE))
            
            for line in lines:
                line_lower = line.lower().strip()
                if line_lower.startswith("subject:"):
                    subject = line.replace("Subject:", "").replace("subject:", "").strip()
                elif line_lower.startswith("html:"):
                    started_html = True
                    started_body = False
                elif line_lower.startswith("body:"):
                    started_body = True
                    started_html = False
                elif started_html:
                    html_body += line + "\n"
                elif started_body:
                    body += line + "\n"
            
            # Если это чистый HTML и парсер по секциям ничего не нашёл — используем весь контент как HTML
            if is_pure_html and not html_body and not body:
                html_body = content
        
        # Remove trailing newlines
        body = body.rstrip()
        html_body = html_body.rstrip()
        # If HTML section exists but only contains comments/whitespace, ignore it and fall back to Body
        try:
            html_body_visible = re.sub(r'<!--[\s\S]*?-->', '', html_body).strip()
            if html_body and not html_body_visible:
                html_body = ""
        except Exception:
            pass
        
        # Пытаемся определить тему, если она отсутствует
        if not subject:
            # 1) Из <title>
            m_title = re.search(r'<title[^>]*>(.*?)</title>', html_body or body or "", flags=re.IGNORECASE | re.DOTALL)
            if m_title:
                subject = re.sub(r'\s+', ' ', m_title.group(1)).strip()
            else:
                # 2) Из первого заголовка h1/h2
                m_h = re.search(r'<h[12][^>]*>(.*?)</h[12]>', html_body or body or "", flags=re.IGNORECASE | re.DOTALL)
                if m_h:
                    subject = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', m_h.group(1))).strip()
                else:
                    # 3) Фолбек
                    subject = "ASAP Marine Update"
        
        # Если есть HTML - используем его, иначе конвертируем текст в HTML
        if html_body:
            # RAW: use HTML exactly as provided in the file, without modifications
            final_body = html_body
        elif body:
            # Convert plain text Body to simple HTML (preserve paragraphs and line breaks), no additional injections
            final_body = "<html><head></head><body style='font-family: Arial, sans-serif; line-height: 1.6; color: #333;'>\n"
            # Разбиваем на параграфы по пустым строкам
            paragraphs = body.split('\n\n')
            for para in paragraphs:
                para = para.strip()
                if para:
                    # Заменяем одинарные переносы на <br>
                    para_html = para.replace('\n', '<br>\n')
                    final_body += f"<p>{para_html}</p>\n"
            final_body += "</body></html>"
        else:
            raise ValueError("Body or HTML not found in email content file")
        
        if not final_body:
            raise ValueError("Body content is empty")
            
        logger.info(f"Loaded email content: Subject='{subject[:50]}...', HTML length={len(final_body)}")
        return subject, final_body
    except UnicodeDecodeError as e:
        raise ValueError(f"Failed to decode email content file (not UTF-8): {e}")
    except FileNotFoundError:
        raise  # Re-raise FileNotFoundError as-is
    except Exception as e:
        raise RuntimeError(f"Failed to read email content file: {e}")


def load_env_file_manual() -> None:
    """Manually load .env file if python-dotenv is not available."""
    if os.path.exists(".env"):
        try:
            with open(".env", "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Пропускаем пустые строки и комментарии
                    if not line or line.startswith("#"):
                        continue
                    # Парсим KEY=VALUE
                    if "=" in line:
                        key, value = line.split("=", 1)
                        key = key.strip()
                        value = value.strip().strip('"').strip("'")
                        # Устанавливаем переменную окружения только если её ещё нет
                        if key and value and key not in os.environ:
                            os.environ[key] = value
        except Exception as e:
            logger.warning(f"Failed to read .env file manually: {e}")


def load_config_from_env() -> Dict[str, Any]:
    """Load configuration from environment variables (.env file)."""
    # Загружаем .env файл если доступен
    if DOTENV_AVAILABLE:
        if not os.path.exists(".env"):
            logger.warning(".env file not found. Using environment variables only.")
        else:
            load_dotenv()
            logger.info("Loaded configuration from .env file")
    else:
        # Fallback: читаем .env файл вручную если python-dotenv недоступен
        if os.path.exists(".env"):
            logger.info("python-dotenv not available, reading .env file manually")
            load_env_file_manual()
        else:
            logger.warning(".env file not found. Using environment variables only.")
    
    config = {}
    
    # Обязательные параметры
    config["database_file"] = os.getenv(
        "DATABASE_FILE",
        "/Users/andriipolodiienko/Documents/GitHub/Mail-Sender-Mailersend/Mail Sender Mailersend/UkrCrewing_DataBase.db"
    )
    config["sender_email"] = os.getenv("SENDER_EMAIL", "")
    config["api_token"] = os.getenv("MAILERSEND_API_TOKEN", "")
    config["telegram_bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN", "")
    config["telegram_chat_id"] = os.getenv("TELEGRAM_CHAT_ID", "")
    
    # Параметры с значениями по умолчанию
    config["batch_size"] = int(os.getenv("BATCH_SIZE", "1"))
    config["delay_between_sends"] = int(os.getenv("DELAY_BETWEEN_SENDS", "45"))
    config["daily_limit"] = int(os.getenv("DAILY_LIMIT", str(DEFAULT_DAILY_LIMIT)))
    config["email_content_dir"] = os.getenv("EMAIL_CONTENT_DIR", "email_example")
    
    # Тестовая база данных (опционально)
    config["test_database_file"] = os.getenv("TEST_DATABASE_FILE", "UkrCrewing_DataBase_test.db")
    
    return config


def get_all_tables(db_path: str) -> List[str]:
    """Get list of all tables and views across all attached schemas in SQLite database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # List schemas (databases): e.g., main, temp, others attached
        cursor.execute("PRAGMA database_list;")
        schemas = [row[1] for row in cursor.fetchall() if row and row[1]]
        tables: List[str] = []
        for schema in schemas:
            # Query each schema's sqlite_master for tables and views
            try:
                cursor.execute(f"SELECT name, type FROM {schema}.sqlite_master WHERE type IN ('table','view') ORDER BY name;")
                rows = cursor.fetchall()
                for name, _type in rows:
                    # Qualify with schema to avoid ambiguity and support non-main tables
                    # Skip SQLite internal objects for a cleaner list
                    if name.startswith("sqlite_"):
                        continue
                    tables.append(f"{schema}.{name}")
            except Exception as inner_exc:
                logger.debug(f"Skipping schema '{schema}' due to error: {inner_exc}")
                continue
        conn.close()
        return sorted(tables)
    except Exception as e:
        logger.error(f"Failed to get tables from database: {e}")
        raise


def get_table_columns(db_path: str, table_name: str) -> List[str]:
    """Get list of columns in a table."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        # Экранируем имя таблицы для SQLite, учитывая схему
        if "." in table_name:
            schema, tbl = table_name.split(".", 1)
            # Корректный синтаксис: PRAGMA schema.table_info('table')
            cursor.execute(f"PRAGMA {schema}.table_info('{tbl}');")
        else:
            cursor.execute(f"PRAGMA table_info('{table_name}');")
        columns = [row[1] for row in cursor.fetchall()]
        conn.close()
        return columns
    except Exception as e:
        logger.error(f"Failed to get columns from table {table_name}: {e}")
        raise


def clear_sent_flags(db_path: str, table_name: str) -> int:
    """Clear 'sent' flags and related metadata columns (date, count) if they exist.
    
    Supports multiple naming variants:
      - Sent, sent
      - Sent_Date, Sent Date, sent_date, sent date
      - Send_Count, Send Count, send_count, send count
    
    Returns: number of rows affected (table row count).
    """
    conn = sqlite3.connect(db_path)
    try:
        cursor = conn.cursor()
        # Collect detailed column info: name -> {type, notnull}
        # Use PRAGMA schema-qualified if needed
        columns: List[str] = []
        col_info: Dict[str, Dict[str, Any]] = {}
        if "." in table_name:
            schema, tbl = table_name.split(".", 1)
            cursor.execute(f"PRAGMA {schema}.table_info('{tbl}');")
        else:
            cursor.execute(f"PRAGMA table_info('{table_name}');")
        for cid, name, ctype, notnull, dflt, pk in cursor.fetchall():
            columns.append(name)
            col_info[name] = {
                "type": (ctype or "").upper(),
                "notnull": bool(notnull),
            }
        
        # Escape table name with optional schema
        if "." in table_name:
            schema, tbl = table_name.split(".", 1)
            table_name_escaped = f'"{schema}"."{tbl}"'
        else:
            table_name_escaped = f'"{table_name}"'
        
        set_parts: List[str] = []
        # Helper to decide reset value respecting NOT NULL and type affinity
        def reset_expr(col: str, semantic: str) -> str:
            info = col_info.get(col, {"type": "", "notnull": False})
            col_type = info["type"]
            is_notnull = info["notnull"]
            if semantic == "flag":  # Sent/sent
                if is_notnull:
                    # Prefer numeric zero for integer-like columns, else empty string
                    return f'"{col}" = 0' if "INT" in col_type else f'"{col}" = \'\''
                else:
                    return f'"{col}" = NULL'
            if semantic == "date":  # Sent_Date variants
                if is_notnull:
                    return f'"{col}" = \'\''
                else:
                    return f'"{col}" = NULL'
            if semantic == "count":  # Send_Count variants
                return f'"{col}" = 0'
            # Fallback
            return f'"{col}" = NULL'
        
        for name in ("Sent", "sent"):
            if name in columns:
                set_parts.append(reset_expr(name, "flag"))
        for name in ("Sent_Date", "Sent Date", "sent_date", "sent date"):
            if name in columns:
                set_parts.append(reset_expr(name, "date"))
        for name in ("Send_Count", "Send Count", "send_count", "send count"):
            if name in columns:
                set_parts.append(reset_expr(name, "count"))
        if not set_parts:
            logger.info(f"No Sent-related columns found to clear in '{table_name}'")
            # Still return row count for consistency
            cursor.execute(f'SELECT COUNT(*) FROM {table_name_escaped};')
            count = cursor.fetchone()[0]
            return count
        
        set_clause = ", ".join(set_parts)
        cursor.execute(f'UPDATE {table_name_escaped} SET {set_clause};')
        conn.commit()
        
        cursor.execute(f'SELECT COUNT(*) FROM {table_name_escaped};')
        count = cursor.fetchone()[0]
        logger.info(f"Cleared Sent flags in '{table_name}' for {count} record(s)")
        return count
    except Exception as e:
        logger.warning(f"Failed to clear Sent flags in '{table_name}': {e}")
        raise
    finally:
        conn.close()


def read_emails_from_table(db_path: str, table_name: str, email_column: str = "email") -> pd.DataFrame:
    """Read emails from SQLite database table."""
    try:
        # Подключаемся к базе
        conn = sqlite3.connect(db_path)
        
        # Пробуем разные варианты названия колонки email
        columns = get_table_columns(db_path, table_name)
        email_col = None
        for col_variant in [email_column, "E-Mail", "Email", "EMAIL", "e_mail", "e-mail", "email"]:
            if col_variant in columns:
                email_col = col_variant
                break
        
        if not email_col:
            raise ValueError(
                f"Column 'email' not found in table '{table_name}'. "
                f"Available columns: {', '.join(columns)}"
            )
        
        # Читаем данные с email колонкой и всеми остальными для сохранения
        # Экранируем имена таблицы и колонок для SQLite (особенно важно для имен с дефисами и схемой)
        if "." in table_name:
            schema, tbl = table_name.split(".", 1)
            table_name_escaped = f'"{schema}"."{tbl}"'
        else:
            table_name_escaped = f'"{table_name}"'
        email_col_escaped = f'"{email_col}"'
        query = f"SELECT *, ROWID as _rowid FROM {table_name_escaped} WHERE {email_col_escaped} IS NOT NULL AND {email_col_escaped} != '';"
        df = pd.read_sql_query(query, conn)
        
        # Переименовываем email колонку в стандартный "Email"
        if email_col != "Email":
            df["Email"] = df[email_col]
        
        conn.close()
        
        logger.info(f"Loaded {len(df)} emails from table '{table_name}'")
        return df
        
    except Exception as e:
        logger.error(f"Failed to read emails from table {table_name}: {e}")
        raise


def update_email_status(db_path: str, table_name: str, rowid: int, sent: str, sent_date: str, send_count: int) -> None:
    """Update email sending status in database."""
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем наличие колонок, если нет - создаем
        columns = get_table_columns(db_path, table_name)
        
        # Экранируем имя таблицы, учитывая схему
        if "." in table_name:
            schema, tbl = table_name.split(".", 1)
            table_name_escaped = f'"{schema}"."{tbl}"'
        else:
            table_name_escaped = f'"{table_name}"'
        
        # Определяем реальные имена колонок в таблице
        # Sent flag
        sent_col = None
        for name in ["Sent", "sent"]:
            if name in columns:
                sent_col = name
                break
        # Sent_Date / sent_date
        sent_date_col = None
        for name in ["Sent_Date", "Sent Date", "sent_date", "sent date"]:
            if name in columns:
                sent_date_col = name
                break
        # Send_Count / send_count
        send_count_col = None
        for name in ["Send_Count", "Send Count", "send_count", "send count"]:
            if name in columns:
                send_count_col = name
                break

        # Если нет ни одной подходящей колонки для флага отправки — создаём стандартную "Sent"
        if sent_col is None:
            cursor.execute(f"ALTER TABLE {table_name_escaped} ADD COLUMN Sent TEXT;")
            sent_col = "Sent"
            columns.append("Sent")
        # Даты/счётчик создаём только если уже есть стандартные — чтобы не засорять временные тестовые таблицы
        if sent_date_col is None and ("Sent_Date" in columns or "Sent Date" in columns):
            # уже существует один из вариантов — использовать его
            sent_date_col = "Sent_Date" if "Sent_Date" in columns else "Sent Date"
        elif sent_date_col is None and "sent_date" in columns:
            sent_date_col = "sent_date"
        elif sent_date_col is None and "sent date" in columns:
            sent_date_col = "sent date"
        elif sent_date_col is None:
            # создаём стандартную, чтобы иметь дату (опционально)
            cursor.execute(f"ALTER TABLE {table_name_escaped} ADD COLUMN Sent_Date TEXT;")
            sent_date_col = "Sent_Date"

        if send_count_col is None and ("Send_Count" in columns or "Send Count" in columns):
            send_count_col = "Send_Count" if "Send_Count" in columns else "Send Count"
        elif send_count_col is None and "send_count" in columns:
            send_count_col = "send_count"
        elif send_count_col is None and "send count" in columns:
            send_count_col = "send count"
        elif send_count_col is None:
            cursor.execute(f"ALTER TABLE {table_name_escaped} ADD COLUMN Send_Count INTEGER DEFAULT 0;")
            send_count_col = "Send_Count"

        # Формируем динамический UPDATE с корректными именами колонок
        set_parts = []
        params = []
        set_parts.append(f'{sent_col} = ?')
        params.append(sent)
        if sent_date_col:
            set_parts.append(f'{sent_date_col} = ?')
            params.append(sent_date)
        if send_count_col:
            set_parts.append(f'{send_count_col} = ?')
            params.append(send_count)
        params.append(rowid)
        set_clause = ", ".join(set_parts)
        cursor.execute(f"UPDATE {table_name_escaped} SET {set_clause} WHERE ROWID = ?", params)
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Failed to update status in database: {e}")
        raise


def get_email_files(email_dir: str = "email_example") -> List[str]:
    """Get list of email content files from directory."""
    if not os.path.exists(email_dir):
        return []
    
    # Файлы, которые нужно исключить
    exclude_files = {'requirements.txt', 'main.log', 'email_sender.log'}
    
    email_files = []
    for file in os.listdir(email_dir):
        if file.endswith(('.txt', '.TXT')):
            # Пропускаем служебные файлы
            if file.lower() in exclude_files or file.endswith('.log'):
                continue
                
            full_path = os.path.join(email_dir, file)
            if os.path.isfile(full_path):
                # Проверяем, что файл содержит "Subject:" (базовая проверка что это письмо)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        content = f.read(400)  # Читаем первые ~400 символов
                        # Включаем также чистые HTML шаблоны (содержат <html)
                        if ('Subject:' in content or 'subject:' in content) or re.search(r'<html', content, flags=re.IGNORECASE):
                            email_files.append(full_path)
                except:
                    continue  # Пропускаем файлы, которые не можем прочитать
    
    return sorted(email_files)


def select_email_file_interactive(email_dir: str = "email_example") -> str:
    """Interactive email file selection."""
    email_files = get_email_files(email_dir)
    
    if not email_files:
        print(f"❌ No email files (.txt) found in '{email_dir}' directory!")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"📧 Available email content files:")
    print(f"{'='*60}")
    
    for idx, file_path in enumerate(email_files, 1):
        file_name = os.path.basename(file_path)
        print(f"  {idx:3}. {file_name}")
    
    print(f"{'='*60}")
    
    while True:
        try:
            choice = input(f"\nSelect email file number (1-{len(email_files)}) or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                print("Cancelled by user.")
                sys.exit(0)
            
            file_num = int(choice)
            if 1 <= file_num <= len(email_files):
                selected_file = email_files[file_num - 1]
                file_name = os.path.basename(selected_file)
                print(f"✅ Selected email file: {file_name}")
                return selected_file
            else:
                print(f"❌ Please enter a number between 1 and {len(email_files)}")
        except ValueError:
            print("❌ Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\n\nCancelled by user.")
            sys.exit(0)

 


def select_mode() -> str:
    """Select running mode: test or production."""
    print(f"\n{'='*60}")
    print("🚀 SELECT RUNNING MODE")
    print(f"{'='*60}")
    print("  1. 🧪 TEST MODE (uses 'test' table)")
    print("  2. 🚀 PRODUCTION MODE (select any table)")
    print(f"{'='*60}")
    
    while True:
        try:
            choice = input("\nSelect mode (1 or 2) or 'q' to quit: ").strip().lower()
            
            if choice == 'q':
                print("Cancelled by user.")
                sys.exit(0)
            
            if choice == '1':
                print("✅ Selected: TEST MODE (using 'test' table)")
                return 'test'
            elif choice == '2':
                print("✅ Selected: PRODUCTION MODE")
                return 'production'
            else:
                print("❌ Please enter '1' for test mode or '2' for production mode")
        except KeyboardInterrupt:
            print("\n\nCancelled by user.")
            sys.exit(0)


def select_table_interactive(tables: List[str]) -> str:
    """Interactive table selection."""
    if not tables:
        print("❌ No tables found in database!")
        sys.exit(1)
    
    print(f"\n{'='*60}")
    print("📋 Available tables in database:")
    print(f"{'='*60}")
    
    # Pretty, multi-column listing (hide 'main.' schema prefix for display)
    total = len(tables)
    display_names: List[str] = []
    for name in tables:
        if name.startswith("main."):
            display_names.append(name.split(".", 1)[1])
        else:
            display_names.append(name)
    entries = [f"{i:3}. {disp}" for i, disp in enumerate(display_names, 1)]
    max_len = max(len(e) for e in entries) if entries else 0
    col_width = min(max_len + 2, 50)  # cap width to keep layout tidy
    term_cols = 120  # assume a wide-enough terminal; simple heuristic
    num_cols = max(1, term_cols // col_width)
    # Split into rows
    rows = []
    for i in range(0, len(entries), num_cols):
        rows.append(entries[i:i+num_cols])
    # Print rows
    for row in rows:
        line = ""
        for cell in row:
            line += cell.ljust(col_width)
        print("  " + line.rstrip())
    
    print(f"{'-'*60}")
    print(f"Total: {total} object(s)")
    print(f"{'='*60}")
    
    while True:
        try:
            choice = input(f"\nSelect table number (1-{len(tables)}) or 'q' to quit: ").strip()
            
            if choice.lower() == 'q':
                print("Cancelled by user.")
                sys.exit(0)
            
            table_num = int(choice)
            if 1 <= table_num <= len(tables):
                selected_table = tables[table_num - 1]
                print(f"✅ Selected table: {selected_table}")
                return selected_table
            else:
                print(f"❌ Please enter a number between 1 and {len(tables)}")
        except ValueError:
            print("❌ Please enter a valid number or 'q' to quit")
        except KeyboardInterrupt:
            print("\n\nCancelled by user.")
            sys.exit(0)


# ---------- ОСНОВНОЙ СКРИПТ --------------------------------------------------
if __name__ == "__main__":
    cfg = load_config_from_env()

    # basic config validation
    required_keys = {
        "database_file": "DATABASE_FILE",
        "sender_email": "SENDER_EMAIL",
        "api_token": "MAILERSEND_API_TOKEN",
        "telegram_bot_token": "TELEGRAM_BOT_TOKEN",
        "telegram_chat_id": "TELEGRAM_CHAT_ID",
    }
    
    missing = []
    for key, env_var in required_keys.items():
        if not cfg.get(key):
            missing.append(f"{env_var} (environment variable)")
    
    if missing:
        print(f"❌ ERROR: Missing required environment variables:")
        for var in missing:
            print(f"   - {var}")
        print(f"\n💡 Please create a .env file or set these environment variables.")
        print(f"   See .env.example for reference.")
        sys.exit(1)
    
    # Validate numeric values
    try:
        cfg["batch_size"] = int(cfg["batch_size"])
        cfg["delay_between_sends"] = int(cfg["delay_between_sends"])
        cfg["daily_limit"] = int(cfg["daily_limit"])
    except (ValueError, TypeError) as e:
        print(f"❌ ERROR: Invalid numeric configuration values: {e}")
        sys.exit(1)

    # -- Выбор режима запуска --
    mode = select_mode()
    
    # -- Интерактивный выбор файла письма --
    email_dir = cfg.get("email_content_dir", "email_example")
    email_content_file = select_email_file_interactive(email_dir)
    
    # -- работаем с базой данных --
    # Выбираем базу данных в зависимости от режима
    if mode == 'test':
        # Тестовый режим - используем тестовую базу данных
        db_path = cfg.get("test_database_file", "UkrCrewing_DataBase_test.db")
        
        # Если путь относительный, делаем его абсолютным относительно текущей директории
        if not os.path.isabs(db_path):
            db_path = os.path.join(os.getcwd(), db_path)
        
        print(f"\n🧪 TEST MODE: Using test database")
        print(f"📁 Database path: {db_path}")
        
        # Проверяем существование тестовой базы данных
        if not os.path.exists(db_path):
            print(f"❌ ERROR: Test database file not found: {db_path}")
            print(f"💡 Please run 'python3 create_test_database.py' to create the test database.")
            logger.error(f"Test database file not found: {db_path}")
            sys.exit(1)
        
        # Проверяем существование таблицы test
        try:
            tables = get_all_tables(db_path)
            if "test" not in tables:
                print(f"❌ ERROR: Table 'test' not found in test database!")
                logger.error("Table 'test' not found in test database")
                sys.exit(1)
            logger.info(f"Test mode: using test database '{db_path}' with table 'test'")
        except Exception as e:
            logger.error(f"Failed to read test database: {e}")
            print(f"❌ ERROR: Failed to read test database: {e}")
            sys.exit(1)
        
        selected_table = "test"
        print(f"✅ Using table 'test' from test database")
        
        # В тестовом режиме автоматически сбрасываем статус отправки для возможности повторного тестирования
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute('UPDATE "test" SET "Sent" = NULL, "Sent_Date" = NULL, "Send_Count" = 0;')
            conn.commit()
            
            # Проверяем результат
            cursor.execute('SELECT COUNT(*) FROM "test";')
            count = cursor.fetchone()[0]
            conn.close()
            
            print(f"🔄 Reset sending status in test database for {count} record(s)")
            logger.info(f"Test mode: Reset sending status in test database")
        except Exception as e:
            logger.warning(f"Failed to reset status in test database: {e}")
            print(f"⚠️  Warning: Could not reset status in test database: {e}")
            # Продолжаем работу, даже если не удалось сбросить статус
    else:
        # Продакшн режим - используем основную базу данных
        db_path = cfg["database_file"]
        print(f"\n🚀 PRODUCTION MODE: Using production database")
        print(f"📁 Database path: {db_path}")
        
        if not os.path.exists(db_path):
            logger.error(f"Database file not found: {db_path}")
            print(f"❌ ERROR: Database file not found: {db_path}")
            sys.exit(1)
        
        # Продакшн режим - интерактивный выбор таблицы
        try:
            tables = get_all_tables(db_path)
            logger.info(f"Found {len(tables)} tables in database")
        except Exception as e:
            logger.error(f"Failed to read database: {e}")
            print(f"❌ ERROR: Failed to read database: {e}")
            sys.exit(1)
        
        # Интерактивный выбор таблицы
        selected_table = select_table_interactive(tables)
        
        # Предложение очистить флаги отправки в продакшене
        try:
            reset_choice = input(f"\nDo you want to clear Sent flags in table '{selected_table}' to resend to all? (yes/no): ").strip().lower()
            if reset_choice == 'yes':
                try:
                    count = clear_sent_flags(db_path, selected_table)
                    
                    print(f"🔄 Cleared Sent flags in table '{selected_table}' for {count} record(s)")
                    logger.info(f"Production mode: Cleared Sent flags in table '{selected_table}' for {count} record(s)")
                except Exception as e:
                    logger.warning(f"Failed to clear Sent flags in production table '{selected_table}': {e}")
                    print(f"⚠️  Warning: Could not clear Sent flags: {e}")
        except KeyboardInterrupt:
            print("\n\nCancelled by user.")
            sys.exit(0)
    
    # -- контент письма (загружаем сразу после выбора таблицы) --
    print(f"\n📄 Loading email content from: {os.path.basename(email_content_file)}...")
    try:
        subject, body = read_email_content(email_content_file)
        print(f"✅ Email content loaded successfully")
    except FileNotFoundError as e:
        print(f"❌ ERROR: Email content file not found: {email_content_file}")
        logger.error(f"Failed to read email content: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ ERROR: Failed to read email content: {e}")
        logger.error(f"Failed to read email content: {e}")
        sys.exit(1)
    
    # Показываем содержимое письма для подтверждения
    print(f"\n{'='*60}")
    print("📧 EMAIL PREVIEW")
    print(f"{'='*60}")
    print(f"📋 Subject: {subject}")
    print(f"\n📄 Body:")
    print("-" * 60)
    print(body)
    print("-" * 60)
    print(f"{'='*60}\n")
    
    # Запрашиваем подтверждение
    confirmation = input("Do you want to proceed with sending? (yes/no): ").strip().lower()
    if confirmation != 'yes':
        print("❌ Cancelled by user.")
        logger.info("Email sending cancelled by user.")
        sys.exit(0)
    
    print("✅ Confirmed. Loading recipients from database...")
    print(f"📊 Reading emails from table: {selected_table}\n")
    
    # Читаем emails из выбранной таблицы
    try:
        df = read_emails_from_table(db_path, selected_table)
        print(f"✅ Successfully loaded {len(df)} emails from database")
    except Exception as e:
        print(f"❌ ERROR: Failed to read emails from table '{selected_table}': {e}")
        logger.error(f"Failed to read emails from table: {e}", exc_info=True)
        sys.exit(1)
    
    # Validate required "Email" column exists
    if "Email" not in df.columns:
        print(f"❌ ERROR: Database table must contain an 'Email' column")
        print(f"   Available columns: {', '.join(df.columns.tolist())}")
        logger.error(f"Database table must contain an 'Email' column. Available: {df.columns.tolist()}")
        sys.exit(1)
    
    # Check if dataframe is empty
    if df.empty:
        print(f"❌ ERROR: No emails found in selected table '{selected_table}'")
        logger.error("Database table is empty")
        sys.exit(1)
    
    print(f"📧 Found {len(df)} email addresses in table\n")

    # Проверка колонки unsubscribe и фильтрация
    print("🔍 Processing emails...")
    unsubscribe_col = None
    for col in ["unsubscribe", "Unsubscribe", "UNSUBSCRIBE"]:
        if col in df.columns:
            unsubscribe_col = col
            break
    
    if unsubscribe_col:
        # Подсчитываем сколько адресов будет пропущено
        # Галочка может быть: True, "TRUE", "true", "1", "✓", "☑", "YES", "Yes", "yes", checkbox value
        unsubscribe_values = df[unsubscribe_col].astype(str).str.upper().isin([
            "TRUE", "1", "YES", "✓", "☑", "TRUE", "CHECKED", "V", "X"
        ]) | df[unsubscribe_col].astype(bool)
        
        skipped_count = unsubscribe_values.sum()
        if skipped_count > 0:
            logger.info(f"Found {skipped_count} email(s) with unsubscribe flag. They will be skipped.")
            print(f"⚠️  Skipping {skipped_count} email(s) with unsubscribe flag")
        
        # Удаляем строки с unsubscribe
        df = df[~unsubscribe_values].copy()
        print(f"✅ After unsubscribe filter: {len(df)} emails remain")
    else:
        logger.info("No 'unsubscribe' column found. All emails will be processed.")
        print("ℹ️  No unsubscribe column found. All emails will be processed.")
    
    # Проверяем наличие _rowid для обновления записей в БД
    if "_rowid" not in df.columns:
        logger.warning("ROWID column not found. Cannot update database records. Adding placeholder.")
        df["_rowid"] = range(len(df))
    
    print(f"✅ Processing {len(df)} email addresses\n")

    # -- подготовка списков --
    # Filter out rows without valid email addresses
    df = df[df["Email"].notna()].copy()
    
    # Store original emails to check what was fixed
    original_emails = df["Email"].astype(str).copy()
    
    # Fix common email formatting issues before validation
    df["Email"] = df["Email"].astype(str).apply(fix_common_email_issues)
    
    # Log emails that were fixed (compare original vs fixed)
    fixed_emails = df[original_emails != df["Email"]]
    if not fixed_emails.empty:
        logger.info(f"Fixed {len(fixed_emails)} email(s) with formatting issues:")
        for idx in fixed_emails.index:
            original = original_emails.loc[idx]
            fixed = df.loc[idx, "Email"]
            logger.info(f"  Row {idx}: '{original}' -> '{fixed}'")
    
    # Фильтруем неотправленные (проверяем обе возможные колонки)
    sent_col = None
    if "Sent" in df.columns:
        sent_col = "Sent"
    elif "sent" in df.columns:
        sent_col = "sent"
    
    if sent_col:
        unsent_df = df[df[sent_col] != "Yes"].copy()
    else:
        unsent_df = df.copy()  # Если колонки нет, отправляем все
    
    today = datetime.now().date()

    # compute sent_today safely using pandas datetime operations
    sent_today = 0
    sent_date_col = None
    for col in ["Sent_Date", "Sent Date", "sent_date"]:
        if col in df.columns:
            sent_date_col = col
            break
    
    if sent_col and sent_date_col:
        sent_mask = df[sent_col] == "Yes"
        if sent_mask.any():
            sent_dates = pd.to_datetime(df.loc[sent_mask, sent_date_col], errors="coerce")
            # Count only valid dates that match today
            valid_dates = sent_dates.dropna()
            if not valid_dates.empty:
                sent_today = (valid_dates.dt.date == today).sum()
    
    logger.info(f"Unsent emails: {len(unsent_df)}, Sent today: {sent_today}")

    # Get daily limit and batch size from config
    daily_limit = cfg.get("daily_limit", DEFAULT_DAILY_LIMIT)
    batch_size = cfg["batch_size"]
    start_date = today

    print(f"\n{'='*60}")
    print("🚀 STARTING EMAIL SENDING")
    print(f"{'='*60}")
    print(f"📧 Subject: {subject}")
    print(f"📬 Unsent emails: {len(unsent_df)}")
    print(f"📅 Sent today: {sent_today}/{daily_limit}")
    print(f"📦 Batch size: {batch_size}")
    print(f"⏱️  Delay between batches: {cfg['delay_between_sends']} seconds")
    print(f"{'='*60}\n")
    
    safe_telegram_message(
        cfg["telegram_bot_token"],
        cfg["telegram_chat_id"],
        f"🚀 Start\nSubject: {subject}\nUnsent: {len(unsent_df)}\nSent today: {sent_today}",
    )

    if len(unsent_df) == 0:
        logger.warning("No unsent emails found. All emails have already been sent.")
        safe_telegram_message(
            cfg["telegram_bot_token"],
            cfg["telegram_chat_id"],
            "ℹ️ No unsent emails found. All emails have already been sent."
        )
        sys.exit(0)
    
    # Check for invalid emails before showing preview
    invalid_emails = unsent_df[~unsent_df["Email"].apply(is_valid_email)]
    if not invalid_emails.empty:
        logger.warning(f"⚠️ Found {len(invalid_emails)} invalid email address(es):")
        for idx, email in invalid_emails["Email"].items():
            logger.warning(f"  Row {idx}: '{email}'")
        print(f"\n⚠️ WARNING: Found {len(invalid_emails)} invalid email address(es) in your file!")
        print("   These emails will be skipped during sending.")
        print("   Invalid emails:")
        for idx, email in list(invalid_emails["Email"].items())[:10]:  # Show first 10
            print(f"     - Row {idx}: {email}")
        if len(invalid_emails) > 10:
            print(f"     ... and {len(invalid_emails) - 10} more")
        print()
    
    # Показываем финальную информацию перед началом отправки
    preview_emails = unsent_df["Email"].dropna().astype(str).head(5).tolist()
    preview = ", ".join(preview_emails) + ("..." if len(unsent_df) > 5 else "")
    
    # Show email validation status in preview
    valid_count = unsent_df["Email"].apply(is_valid_email).sum()
    invalid_count = len(unsent_df) - valid_count
    
    print(f"\n{'='*60}")
    print("📊 SENDING SUMMARY")
    print(f"{'='*60}")
    print(f"📋 Table: {selected_table}")
    print(f"📧 Subject: {subject}")
    print(f"📬 Total emails in table: {len(df)}")
    print(f"📭 Unsent emails: {len(unsent_df)}")
    print(f"✅ Valid emails: {valid_count}")
    if invalid_count > 0:
        print(f"❌ Invalid emails (will be skipped): {invalid_count}")
    print(f"📅 Already sent today: {sent_today}/{daily_limit}")
    print(f"📦 Batch size: {batch_size}")
    print(f"⏱️  Delay between batches: {cfg['delay_between_sends']} seconds")
    print(f"\n📧 Email preview (first 5): {preview}")
    print(f"{'='*60}\n")

    for i in range(0, len(unsent_df), batch_size):

        # --- суточный лимит ---
        if sent_today >= daily_limit:
            msg = f"❌ Daily limit {daily_limit} reached. Stopping. Resume tomorrow."
            logger.warning(msg)
            safe_telegram_message(cfg["telegram_bot_token"], cfg["telegram_chat_id"], msg)
            
            # Calculate time until midnight
            tomorrow = start_date + timedelta(days=1)
            midnight = datetime.combine(tomorrow, datetime.min.time())
            wait_sec = (midnight - datetime.now()).total_seconds()
            
            if wait_sec > 0:
                wait_hours = wait_sec / 3600
                logger.info(f"Daily limit reached. Waiting {wait_hours:.1f} hours until midnight...")
                safe_telegram_message(
                    cfg["telegram_bot_token"], 
                    cfg["telegram_chat_id"],
                    f"⏰ Waiting {wait_hours:.1f} hours until midnight to reset daily limit..."
                )
                
                # Sleep in smaller chunks to allow interruption
                try:
                    while wait_sec > 0:
                        sleep_time = min(300, wait_sec)  # Sleep max 5 minutes at a time
                        time.sleep(sleep_time)
                        wait_sec -= sleep_time
                except KeyboardInterrupt:
                    safe_telegram_message(
                        cfg["telegram_bot_token"], 
                        cfg["telegram_chat_id"],
                        "⏹️ Рассылка остановлена вручную."
                    )
                    sys.exit(0)
            
            sent_today = 0
            start_date = datetime.now().date()
            logger.info("Daily limit reset. Continuing...")

        # --- формируем партию ---
        batch = unsent_df.iloc[i : i + batch_size]
        
        # Validate emails and filter invalid ones
        # Emails should already be fixed by fix_common_email_issues, but validate again
        valid_mask = batch["Email"].apply(
            lambda x: is_valid_email(str(x)) if pd.notna(x) else False
        )
        valid = batch[valid_mask]
        emails = valid["Email"].astype(str).str.strip().tolist()
        invalid_cnt = len(batch) - len(valid)
        
        if invalid_cnt > 0:
            invalid_emails = batch[~valid_mask]["Email"].tolist()
            logger.warning(f"Batch {i//batch_size + 1}: Found {invalid_cnt} invalid email(s): {invalid_emails}")

        batch_num = i // batch_size + 1
        safe_telegram_message(
            cfg["telegram_bot_token"],
            cfg["telegram_chat_id"],
            f"✅ Valid: {len(emails)} | ❌ Invalid: {invalid_cnt}",
        )
        
        print(f"\n{'='*60}")
        print(f"📦 Batch {batch_num}/{len(unsent_df)//batch_size + 1}")
        print(f"   Valid emails: {len(emails)} | Invalid: {invalid_cnt}")
        print(f"{'='*60}")

        if not emails:
            print("⚠️  No valid emails in this batch. Skipping...")
            continue

        # enforce remaining daily limit: send only up to allowed, postpone the rest
        allowed = max(0, daily_limit - sent_today)
        if allowed == 0:
            print("⚠️  Daily limit reached. This batch will be processed tomorrow.")
            # will be handled by the top-of-loop sleep next iteration
            continue

        send_list = emails if len(emails) <= allowed else emails[:allowed]
        
        print(f"\n📤 Sending batch {batch_num}...")
        print(f"   Recipients: {len(send_list)} email(s)")
        if len(send_list) <= 5:
            print(f"   Emails: {', '.join(send_list)}")
        else:
            print(f"   Emails: {', '.join(send_list[:3])} ... and {len(send_list)-3} more")

        # --- отправка ---
        try:
            logger.info(f"Attempting to send batch {batch_num} with {len(send_list)} recipients")
            logger.info(f"Subject: {subject[:100]}")
            logger.info(f"Recipients: {send_list[:3]}{'...' if len(send_list) > 3 else ''}")
            
            send_email_mailersend(
                subject, body, send_list,
                cfg["sender_email"], cfg["api_token"],
                cfg["telegram_bot_token"], cfg["telegram_chat_id"],
            )
            print(f"✅ SUCCESS: Batch {batch_num} sent successfully!")
            print(f"   📧 Sent to {len(send_list)} recipient(s)")
            logger.info(f"Batch {batch_num} sent successfully to {len(send_list)} recipients")
        except Exception as exc:
            error_msg = str(exc)
            print(f"❌ ERROR: Failed to send batch {batch_num}")
            print(f"   Error: {error_msg}")
            logger.error(f"Failed to send batch {batch_num}: {error_msg}", exc_info=True)
            # Log full traceback for debugging
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            # do not mark as sent; continue with next batch
            continue

        # --- статистика ---
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sent_idx = valid[valid["Email"].astype(str).str.strip().isin(send_list)].index
        sent_rows = df.loc[sent_idx]
        
        # Обновляем статус в базе данных для каждой отправленной записи
        for idx in sent_idx:
            rowid = df.loc[idx, "_rowid"]
            old_send_count = df.loc[idx, "Send_Count"] if "Send_Count" in df.columns else 0
            if pd.isna(old_send_count):
                old_send_count = 0
            new_send_count = int(old_send_count) + 1
            
            try:
                update_email_status(db_path, selected_table, int(rowid), "Yes", now_str, new_send_count)
            except Exception as e:
                logger.error(f"Failed to update status for rowid {rowid}: {e}")
        
        # Обновляем локальный DataFrame для корректного подсчета
        if "Sent" not in df.columns:
            df["Sent"] = ""
        if "Sent_Date" not in df.columns:
            df["Sent_Date"] = ""
        if "Send_Count" not in df.columns:
            df["Send_Count"] = 0
        
        df.loc[sent_idx, "Sent"] = "Yes"
        df.loc[sent_idx, "Sent_Date"] = now_str
        df.loc[sent_idx, "Send_Count"] = (
            df.loc[sent_idx, "Send_Count"].fillna(0).astype(int) + 1
        )
        
        sent_today += len(send_list)
        
        print(f"📊 Progress: {sent_today}/{daily_limit} emails sent today")
        print(f"   Remaining: {daily_limit - sent_today} emails left today")
        print(f"💾 Database updated successfully")
        logger.info(f"Batch {batch_num}: Marked {len(send_list)} emails as sent. Total sent today: {sent_today}")


        # --- пауза между партиями ---
        if i + batch_size < len(unsent_df):  # Not the last batch
            delay = cfg["delay_between_sends"]
            print(f"⏳ Waiting {delay} seconds before next batch...\n")
        try:
            time.sleep(cfg["delay_between_sends"])
        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping email sending (KeyboardInterrupt)...")
            safe_telegram_message(cfg["telegram_bot_token"], cfg["telegram_chat_id"],
                                  "⏹️ Рассылка остановлена вручную.")
            sys.exit(0)

    # финальное сохранение
    print(f"\n{'='*60}")
    print("💾 Final state saved to database")
    print("✅ Database update completed")
    logger.info("Final database update completed")

    print(f"\n{'='*60}")
    print("🎉 EMAIL SENDING COMPLETED!")
    print(f"{'='*60}")
    completion_msg = f"✅ Done. Total sent today: {sent_today}/{daily_limit}"
    print(f"📊 Summary:")
    print(f"   • Total emails sent today: {sent_today}/{daily_limit}")
    print(f"   • Remaining in queue: {len(unsent_df) - sent_today if len(unsent_df) > sent_today else 0}")
    print(f"{'='*60}\n")
    logger.info(completion_msg)
    safe_telegram_message(cfg["telegram_bot_token"], cfg["telegram_chat_id"], completion_msg)
