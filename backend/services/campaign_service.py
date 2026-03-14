"""Campaign service for managing email campaigns."""
import os
import pandas as pd
import re
import json
import logging
import traceback
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional, Tuple
from backend.models.database import get_session, Campaign, CampaignDelivery, Log, Blacklist, Settings
from backend.mailer import BaseMailer, MailerSendMailer, GmailMailer
from backend.services.template_engine import TemplateEngine
from backend.utils.campaign_logs import append_campaign_log
from backend.utils.database import read_emails_from_table, read_emails_from_tables
from backend.utils.telegram import send_telegram_message
import time

# Set up logging
logger = logging.getLogger(__name__)


def get_mailer(provider: str, config: Dict[str, Any]) -> BaseMailer:
    """
    Factory function to get mailer instance by provider name.
    
    Args:
        provider: 'mailersend' or 'gmail'
        config: Provider-specific configuration
        
    Returns:
        BaseMailer instance
    """
    if provider.lower() == 'mailersend':
        return MailerSendMailer(config)
    elif provider.lower() == 'gmail':
        return GmailMailer(config)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def validate_email(email: str) -> bool:
    """Validate email address format."""
    if not email or not isinstance(email, str):
        return False
    email = email.strip()
    if '@' not in email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def fix_common_email_issues(email: str) -> str:
    """Fix common email formatting issues."""
    if not email or not isinstance(email, str):
        return email
    email = email.strip()
    replacements = [
        (r'\+AEA-', '@'),
        (r'\+AT\+', '@'),
        (r'\[at\]', '@'),
        (r'\(at\)', '@'),
        (r'\s+at\s+', '@'),
        (r'\s*@\s*', '@'),
    ]
    for pattern, replacement in replacements:
        email = re.sub(pattern, replacement, email, flags=re.IGNORECASE)
    email = email.replace(' ', '')
    return email


def read_emails_from_csv(csv_path: str, email_column: str = None) -> pd.DataFrame:
    """
    Read emails from CSV file.
    
    Auto-detects email column if not specified.
    
    Args:
        csv_path: Path to CSV file
        email_column: Name of email column (auto-detected if None)
        
    Returns:
        DataFrame with email addresses
    """
    if not csv_path:
        raise ValueError("CSV file path is required")
    if not os.path.exists(csv_path):
        raise ValueError(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    
    # Auto-detect email column
    if email_column is None:
        email_variants = ['Email', 'email', 'E-Mail', 'E-mail', 'e-mail', 'EMAIL', 'e_mail', 'E_MAIL']
        for variant in email_variants:
            if variant in df.columns:
                email_column = variant
                break
        
        if email_column is None:
            raise ValueError(f"Could not auto-detect email column. Available columns: {', '.join(df.columns)}")
    
    # Filter out rows without emails
    df = df[df[email_column].notna()].copy()
    df = df[df[email_column].astype(str).str.strip() != ''].copy()
    
    return df


class CampaignService:
    """Service for managing email campaigns."""
    
    def __init__(self, log_callback: Callable = None):
        """
        Initialize campaign service.
        
        Args:
            log_callback: Optional callback function(campaign_id, level, message) for logging
        """
        self.log_callback = log_callback
        self.template_engine = TemplateEngine()
        self._telegram_settings_cache: Optional[Tuple[Optional[str], Optional[str]]] = None
        self._telegram_settings_cache_ts = 0.0
        self._telegram_settings_ttl_sec = 60

    def _get_telegram_settings_cached(self) -> Tuple[Optional[str], Optional[str]]:
        """Return Telegram credentials with a short-lived cache to reduce DB reads."""
        now_ts = time.time()
        if (
            self._telegram_settings_cache is not None
            and (now_ts - self._telegram_settings_cache_ts) < self._telegram_settings_ttl_sec
        ):
            return self._telegram_settings_cache

        session = get_session()
        try:
            telegram_token_setting = session.query(Settings).filter_by(key='telegram_bot_token').first()
            telegram_chat_setting = session.query(Settings).filter_by(key='telegram_chat_id').first()
            telegram_token = telegram_token_setting.value if telegram_token_setting else None
            telegram_chat_id = telegram_chat_setting.value if telegram_chat_setting else None
            self._telegram_settings_cache = (telegram_token, telegram_chat_id)
            self._telegram_settings_cache_ts = now_ts
            return self._telegram_settings_cache
        finally:
            session.close()
    
    def _log(self, campaign_id: int, level: str, message: str):
        """Log message to DB and file, optional callback, and Telegram."""
        session = get_session()
        try:
            log_ts = datetime.utcnow()

            log_entry = Log(
                campaign_id=campaign_id,
                level=level,
                message=message,
                ts=log_ts
            )
            session.add(log_entry)
            session.commit()

            append_campaign_log(campaign_id, level, message, log_ts)
            
            if self.log_callback:
                self.log_callback(campaign_id, level, message)
            
            self._send_telegram_log(campaign_id, level, message)
        except Exception as e:
            session.rollback()
            logger.error(f"Error logging for campaign {campaign_id}: {e}")
        finally:
            session.close()
    
    def _send_telegram_log(self, campaign_id: int, level: str, message: str):
        """Send log message to Telegram if configured."""
        try:
            telegram_token, telegram_chat_id = self._get_telegram_settings_cached()
            if telegram_token and telegram_chat_id:
                formatted_message = f"📧 Campaign #{campaign_id} [{level}]\n{message}"
                send_telegram_message(telegram_token, telegram_chat_id, formatted_message)
        except Exception as e:
            # Don't fail the campaign if Telegram fails
            logger.warning(f"Telegram notification error for campaign {campaign_id}: {e}")

    def _is_campaign_paused(self, campaign_id: int) -> bool:
        """Check campaign pause status with a lightweight query."""
        session = get_session()
        try:
            campaign = session.query(Campaign).filter_by(id=campaign_id).first()
            return bool(campaign and campaign.status == 'paused')
        finally:
            session.close()
    
    def _update_campaign_status(self, campaign_id: int, status: str, success_cnt: int = None, error_cnt: int = None):
        """Update campaign status."""
        session = get_session()
        try:
            campaign = session.query(Campaign).filter_by(id=campaign_id).first()
            if campaign:
                campaign.status = status
                if success_cnt is not None:
                    campaign.success_cnt = success_cnt
                if error_cnt is not None:
                    campaign.error_cnt = error_cnt
                if status == 'completed' or status == 'failed':
                    campaign.end_ts = datetime.utcnow()
                session.commit()
        except Exception as e:
            logger.error(f"Error updating campaign {campaign_id} status: {e}")
        finally:
            session.close()
    
    def _get_blacklist(self) -> List[str]:
        """Get list of blacklisted emails."""
        session = get_session()
        try:
            blacklist = session.query(Blacklist).all()
            return [b.email.lower() for b in blacklist]
        finally:
            session.close()

    def _sync_campaign_deliveries(self, campaign_id: int, valid_emails: List[str]) -> List[CampaignDelivery]:
        """Ensure campaign has one delivery row per valid email in stable order."""
        session = get_session()
        try:
            existing_rows = (
                session.query(CampaignDelivery)
                .filter_by(campaign_id=campaign_id)
                .order_by(CampaignDelivery.sequence_no.asc(), CampaignDelivery.id.asc())
                .all()
            )
            existing_by_email = {row.email.lower(): row for row in existing_rows}

            created = False
            for index, email in enumerate(valid_emails):
                email_key = email.lower()
                row = existing_by_email.get(email_key)
                if row is None:
                    row = CampaignDelivery(
                        campaign_id=campaign_id,
                        email=email,
                        sequence_no=index,
                        status='pending'
                    )
                    session.add(row)
                    existing_by_email[email_key] = row
                    created = True
                elif row.sequence_no != index:
                    row.sequence_no = index

            if created:
                session.flush()

            session.commit()
            return (
                session.query(CampaignDelivery)
                .filter_by(campaign_id=campaign_id)
                .order_by(CampaignDelivery.sequence_no.asc(), CampaignDelivery.id.asc())
                .all()
            )
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _mark_delivery_result(self, campaign_id: int, emails: List[str], status: str, last_error: Optional[str] = None):
        """Persist per-email delivery status for one batch."""
        if not emails:
            return

        session = get_session()
        try:
            now = datetime.utcnow()
            normalized = {email.lower(): email for email in emails}
            rows = (
                session.query(CampaignDelivery)
                .filter(CampaignDelivery.campaign_id == campaign_id)
                .all()
            )
            for row in rows:
                row_email = (row.email or '').lower()
                if row_email not in normalized:
                    continue
                row.status = status
                row.last_error = last_error if status == 'failed' else None
                row.updated_ts = now
                if status == 'sent':
                    row.sent_ts = now
                elif status != 'sent':
                    row.sent_ts = None
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def _split_batch_delivery_result(self, batch: List[str], result: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """Split one batch into sent and failed recipients based on provider result."""
        if not batch:
            return [], []

        sent_count_raw = result.get('sent_count')
        if sent_count_raw is None:
            sent_count = len(batch) if result.get('success') else 0
        else:
            try:
                sent_count = int(sent_count_raw)
            except (TypeError, ValueError):
                sent_count = len(batch) if result.get('success') else 0

        sent_count = max(0, min(sent_count, len(batch)))
        sent_emails = batch[:sent_count]
        failed_emails = batch[sent_count:]
        return sent_emails, failed_emails
    
    def _filter_emails(self, emails: List[str]) -> List[str]:
        """
        Filter and validate emails.
        
        Removes duplicates, validates format, checks blacklist.
        
        Args:
            emails: List of email addresses
            
        Returns:
            List of valid, non-blacklisted emails
        """
        blacklist = self._get_blacklist()
        seen = set()
        valid_emails = []
        
        for email in emails:
            # Fix common issues
            email = fix_common_email_issues(str(email))
            
            # Skip if empty
            if not email or not email.strip():
                continue
            
            # Skip duplicates
            email_lower = email.lower().strip()
            if email_lower in seen:
                continue
            seen.add(email_lower)
            
            # Check blacklist
            if email_lower in blacklist:
                continue
            
            # Validate format
            if validate_email(email):
                valid_emails.append(email.strip())
        
        return valid_emails
    
    def create_campaign(
        self,
        name: str,
        provider: str,
        subject: str,
        sender_email: str,
        csv_path: str = None,
        database_table: str = None,
        email_column: str = None,
        batch_size: int = 1,
        delay_between_batches: int = 45,
        daily_limit: int = 2000,
        html_body: str = None,
        vacancies_text: str = None,
        provider_config: Dict[str, Any] = None
    ) -> int:
        """
        Create a new campaign.
        
        Either csv_path or database_table must be provided.
        
        Returns:
            Campaign ID
        """
        if not csv_path and not database_table:
            raise ValueError("Either csv_path or database_table must be provided")
        
        session = get_session()
        try:
            campaign = Campaign(
                name=name,
                provider=provider,
                subject=subject,
                sender_email=sender_email,
                csv_path=csv_path,
                database_table=database_table,
                email_column=email_column or 'email',
                batch_size=batch_size,
                delay_between_batches=delay_between_batches,
                daily_limit=daily_limit,
                html_body=html_body,
                vacancies_text=vacancies_text,
                status='pending',
                start_ts=datetime.utcnow()
            )
            session.add(campaign)
            session.commit()
            campaign_id = campaign.id
            
            # Log that content was saved
            if html_body:
                logger.info(f"Campaign {campaign_id}: HTML body saved ({len(html_body)} characters)")
            if vacancies_text:
                logger.info(f"Campaign {campaign_id}: Vacancies text saved ({len(vacancies_text)} characters)")
            
            return campaign_id
        finally:
            session.close()
    
    def run_campaign(
        self,
        campaign_id: int,
        html_body: str,
        provider_config: Dict[str, Any],
        vacancies_text: str = ""
    ):
        """
        Run email campaign.
        
        Args:
            campaign_id: Campaign ID
            html_body: HTML email body (or None to use template)
            provider_config: Provider-specific configuration
            vacancies_text: Plain text vacancies (if html_body is None, will be rendered)
        """
        session = get_session()
        campaign = None
        try:
            logger.info(f"Starting campaign {campaign_id}")
            self._log(campaign_id, 'INFO', 'Initializing campaign...')
            
            # Get campaign from database
            campaign = session.query(Campaign).filter_by(id=campaign_id).first()
            if not campaign:
                error_msg = f"Campaign {campaign_id} not found"
                logger.error(error_msg)
                raise ValueError(error_msg)
            
            logger.info(f"Campaign {campaign_id}: {campaign.name} - Provider: {campaign.provider}")
            
            # Validate provider config
            if not provider_config:
                error_msg = f"Provider config is required for {campaign.provider}"
                logger.error(f"Campaign {campaign_id}: {error_msg}")
                raise ValueError(error_msg)
            
            # Step 1: Initialize mailer
            try:
                logger.info(f"Campaign {campaign_id}: Initializing {campaign.provider} mailer...")
                self._log(campaign_id, 'INFO', f'Initializing {campaign.provider} mailer...')
                mailer = get_mailer(campaign.provider, provider_config)
                logger.info(f"Campaign {campaign_id}: Mailer initialized successfully")
            except Exception as e:
                error_msg = f"Failed to initialize mailer: {str(e)}"
                logger.error(f"Campaign {campaign_id}: {error_msg}\n{traceback.format_exc()}")
                raise ValueError(error_msg) from e
            
            # Step 2: Load emails from CSV or database
            email_list = []
            try:
                if campaign.database_table:
                    # Parse database_table - can be single table name or JSON array
                    try:
                        table_names = json.loads(campaign.database_table)
                        if not isinstance(table_names, list):
                            table_names = [campaign.database_table]
                    except (json.JSONDecodeError, TypeError):
                        # Single table name (backward compatibility)
                        table_names = [campaign.database_table]
                    
                    if len(table_names) > 1:
                        logger.info(f"Campaign {campaign_id}: Loading emails from {len(table_names)} database tables: {', '.join(table_names)}")
                        self._log(
                            campaign_id,
                            'INFO',
                            f"Loading emails from {len(table_names)} database tables: {', '.join(table_names)}"
                        )
                        df = read_emails_from_tables(table_names, campaign.email_column)
                    else:
                        logger.info(f"Campaign {campaign_id}: Loading emails from database table: {table_names[0]}")
                        self._log(campaign_id, 'INFO', f'Loading emails from database table: {table_names[0]}')
                        df = read_emails_from_table(table_names[0], campaign.email_column)
                    
                    email_list = df['Email'].tolist() if 'Email' in df.columns else df[campaign.email_column].tolist()
                    logger.info(f"Campaign {campaign_id}: Loaded {len(email_list)} emails from database")
                elif campaign.csv_path:
                    logger.info(f"Campaign {campaign_id}: Loading emails from CSV: {campaign.csv_path}")
                    self._log(campaign_id, 'INFO', f'Loading emails from CSV: {campaign.csv_path}')
                    df = read_emails_from_csv(campaign.csv_path, campaign.email_column)
                    email_list = df[campaign.email_column].tolist()
                    logger.info(f"Campaign {campaign_id}: Loaded {len(email_list)} emails from CSV")
                else:
                    error_msg = "No data source specified (csv_path or database_table)"
                    logger.error(f"Campaign {campaign_id}: {error_msg}")
                    raise ValueError(error_msg)
            except Exception as e:
                error_msg = f"Failed to load emails: {str(e)}"
                logger.error(f"Campaign {campaign_id}: {error_msg}\n{traceback.format_exc()}")
                raise ValueError(error_msg) from e
            
            if not email_list:
                error_msg = "No emails found in data source"
                logger.warning(f"Campaign {campaign_id}: {error_msg}")
                raise ValueError(error_msg)
            
            # Step 3: Filter emails
            try:
                logger.info(f"Campaign {campaign_id}: Filtering {len(email_list)} emails...")
                self._log(campaign_id, 'INFO', f'Filtering {len(email_list)} emails...')
                valid_emails = self._filter_emails(email_list)
                logger.info(f"Campaign {campaign_id}: Filtered to {len(valid_emails)} valid emails")
            except Exception as e:
                error_msg = f"Failed to filter emails: {str(e)}"
                logger.error(f"Campaign {campaign_id}: {error_msg}\n{traceback.format_exc()}")
                raise ValueError(error_msg) from e
            
            if not valid_emails:
                error_msg = "No valid emails after filtering"
                logger.warning(f"Campaign {campaign_id}: {error_msg}")
                raise ValueError(error_msg)
            
            # Campaign is ready to start
            logger.info(f"Campaign {campaign_id}: Starting execution with {len(valid_emails)} valid emails")
            self._log(campaign_id, 'INFO', f'Campaign started. Total emails: {len(email_list)}, Valid: {len(valid_emails)}')
            self._update_campaign_status(campaign_id, 'running')
            delivery_rows = self._sync_campaign_deliveries(campaign_id, valid_emails)
            
            # Send campaign start notification to Telegram
            self._send_telegram_campaign_start(campaign_id, campaign.name, campaign.provider, len(valid_emails))
            
            # Step 4: Render HTML if needed
            try:
                if not html_body:
                    logger.info(f"Campaign {campaign_id}: Rendering HTML template...")
                    self._log(campaign_id, 'INFO', 'Rendering email template...')
                    html_body = self.template_engine.render(
                        vacancies_text=vacancies_text,
                        cta_subject=campaign.subject
                    )
                    logger.info(f"Campaign {campaign_id}: HTML template rendered successfully")
            except Exception as e:
                error_msg = f"Failed to render HTML template: {str(e)}"
                logger.error(f"Campaign {campaign_id}: {error_msg}\n{traceback.format_exc()}")
                raise ValueError(error_msg) from e
            
            # Process in batches using persisted per-email state.
            success_count = len([row for row in delivery_rows if row.status == 'sent'])
            error_count = len([row for row in delivery_rows if row.status == 'failed'])
            delivery_rows = [row for row in delivery_rows if row.status != 'sent']
            total_emails = len(valid_emails)
            
            batch_size = max(int(campaign.batch_size or 1), 1)
            delay_between_batches = max(int(campaign.delay_between_batches or 0), 0)
            pause_poll_interval = 2

            for i in range(0, len(delivery_rows), batch_size):
                # Check if campaign is paused before each batch
                if self._is_campaign_paused(campaign_id):
                    self._log(campaign_id, 'INFO', f'Campaign paused. Progress: {success_count} sent, {error_count} errors')
                    return  # Exit function, but keep campaign in paused state
                
                batch_rows = delivery_rows[i:i + batch_size]
                batch = [row.email for row in batch_rows]
                batch_num = i // batch_size + 1
                
                try:
                    result = mailer.send(
                        subject=campaign.subject,
                        html_body=html_body,
                        recipients=batch,
                        sender_email=campaign.sender_email
                    )

                    sent_emails, failed_emails = self._split_batch_delivery_result(batch, result)
                    error_message = result.get("message", "Unknown error")

                    if sent_emails:
                        success_count += len(sent_emails)
                        self._mark_delivery_result(campaign_id, sent_emails, 'sent')
                        self._log(campaign_id, 'SUCCESS', f'Batch {batch_num}: Sent to {len(sent_emails)} recipients')

                    if failed_emails:
                        error_count += len(failed_emails)
                        self._mark_delivery_result(campaign_id, failed_emails, 'failed', error_message)
                        self._log(campaign_id, 'ERROR', f'Batch {batch_num}: {error_message}')
                    
                    # Update progress
                    self._update_campaign_status(campaign_id, 'running', success_count, error_count)
                    
                    # Delay between batches (except last)
                    if i + batch_size < len(valid_emails) and delay_between_batches > 0:
                        # Check for pause during delay, but poll DB less frequently.
                        remaining_delay = delay_between_batches
                        while remaining_delay > 0:
                            sleep_for = min(pause_poll_interval, remaining_delay)
                            time.sleep(sleep_for)
                            remaining_delay -= sleep_for
                            if self._is_campaign_paused(campaign_id):
                                self._log(campaign_id, 'INFO', f'Campaign paused. Progress: {success_count} sent, {error_count} errors')
                                return
                
                except Exception as e:
                    error_count += len(batch)
                    self._mark_delivery_result(campaign_id, batch, 'failed', str(e))
                    self._log(campaign_id, 'ERROR', f'Batch {batch_num}: Exception - {str(e)}')
                    self._update_campaign_status(campaign_id, 'running', success_count, error_count)
            
            # Mark as completed
            self._update_campaign_status(campaign_id, 'completed', success_count, error_count)
            completion_message = f'Campaign completed. Success: {success_count}, Errors: {error_count}'
            self._log(campaign_id, 'INFO', completion_message)
            
            # Send completion summary to Telegram
            self._send_telegram_completion_summary(campaign_id, campaign.name, success_count, error_count, total_emails)
        
        except Exception as e:
            # Log full error with traceback
            error_msg = str(e)
            error_traceback = traceback.format_exc()
            logger.error(f"Campaign {campaign_id} failed: {error_msg}\n{error_traceback}")
            
            # Log error to campaign logs
            detailed_error = f'Campaign failed: {error_msg}'
            if campaign:
                detailed_error += f' (Provider: {campaign.provider}, Data Source: {campaign.database_table or campaign.csv_path})'
            self._log(campaign_id, 'ERROR', detailed_error)
            
            # Update status to failed
            self._update_campaign_status(campaign_id, 'failed')
            
            # Send failure notification to Telegram
            self._send_telegram_campaign_failure(campaign_id, error_msg)
        finally:
            if session:
                session.close()
    
    def _send_telegram_completion_summary(self, campaign_id: int, campaign_name: str, success: int, errors: int, total: int):
        """Send campaign completion summary to Telegram."""
        try:
            telegram_token, telegram_chat_id = self._get_telegram_settings_cached()
            if telegram_token and telegram_chat_id:
                message = (
                    f"✅ Campaign Completed\n\n"
                    f"Name: {campaign_name}\n"
                    f"ID: #{campaign_id}\n"
                    f"Total: {total}\n"
                    f"✅ Success: {success}\n"
                    f"❌ Errors: {errors}"
                )
                send_telegram_message(telegram_token, telegram_chat_id, message)
        except Exception as e:
            logger.warning(f"Telegram completion summary error for campaign {campaign_id}: {e}")
    
    def _send_telegram_campaign_failure(self, campaign_id: int, error_message: str):
        """Send campaign failure notification to Telegram."""
        try:
            telegram_token, telegram_chat_id = self._get_telegram_settings_cached()
            if telegram_token and telegram_chat_id:
                message = f"❌ Campaign Failed\n\nID: #{campaign_id}\nError: {error_message}"
                send_telegram_message(telegram_token, telegram_chat_id, message)
        except Exception as e:
            logger.warning(f"Telegram failure notification error for campaign {campaign_id}: {e}")
    
    def _send_telegram_campaign_start(self, campaign_id: int, campaign_name: str, provider: str, email_count: int):
        """Send campaign start notification to Telegram."""
        try:
            telegram_token, telegram_chat_id = self._get_telegram_settings_cached()
            if telegram_token and telegram_chat_id:
                message = (
                    f"🚀 Campaign Started\n\n"
                    f"Name: {campaign_name}\n"
                    f"ID: #{campaign_id}\n"
                    f"Provider: {provider}\n"
                    f"Recipients: {email_count}"
                )
                send_telegram_message(telegram_token, telegram_chat_id, message)
        except Exception as e:
            logger.warning(f"Telegram start notification error for campaign {campaign_id}: {e}")
