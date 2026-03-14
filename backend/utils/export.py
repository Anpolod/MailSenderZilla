"""Utilities for exporting campaign data."""
import csv
import io
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.models.database import get_session, Campaign, CampaignDelivery, Log


def extract_emails_from_logs(logs: List[Log]) -> Dict[str, List[str]]:
    """
    Extract email addresses from campaign logs.
    
    Returns:
        Dict with 'sent' and 'failed' lists of emails
    """
    sent_emails = []
    failed_emails = []
    
    # Pattern to extract emails from log messages
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    
    for log in logs:
        # Extract emails from log message
        emails = re.findall(email_pattern, log.message)
        
        if log.level == 'SUCCESS':
            sent_emails.extend(emails)
        elif log.level == 'ERROR':
            failed_emails.extend(emails)
    
    # Remove duplicates while preserving order
    sent_emails = list(dict.fromkeys(sent_emails))
    failed_emails = list(dict.fromkeys(failed_emails))
    
    return {
        'sent': sent_emails,
        'failed': failed_emails
    }


def export_logs_to_csv(campaign_id: int) -> str:
    """
    Export campaign logs to CSV format.
    
    Returns:
        CSV content as string
    """
    session = get_session()
    try:
        logs = session.query(Log).filter_by(campaign_id=campaign_id).order_by(Log.ts.asc()).all()
        campaign = session.query(Campaign).filter_by(id=campaign_id).first()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Timestamp', 'Level', 'Message'])
        
        # Campaign info as comments
        if campaign:
            writer.writerow(['# Campaign:', campaign.name])
            writer.writerow(['# Status:', campaign.status])
            writer.writerow(['# Success Count:', campaign.success_cnt])
            writer.writerow(['# Error Count:', campaign.error_cnt])
            writer.writerow([])
        
        # Log entries
        for log in logs:
            writer.writerow([
                log.ts.isoformat() if log.ts else '',
                log.level,
                log.message
            ])
        
        return output.getvalue()
    finally:
        session.close()


def export_sent_emails_to_csv(campaign_id: int) -> str:
    """
    Export successfully sent emails to CSV.
    
    Returns:
        CSV content as string
    """
    session = get_session()
    try:
        campaign = session.query(Campaign).filter_by(id=campaign_id).first()
        if not campaign:
            return ''
        
        deliveries = (
            session.query(CampaignDelivery)
            .filter_by(campaign_id=campaign_id, status='sent')
            .order_by(CampaignDelivery.sequence_no.asc())
            .all()
        )
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Email', 'Sent Date', 'Campaign ID', 'Campaign Name'])
        
        for delivery in deliveries:
            writer.writerow([
                delivery.email,
                delivery.sent_ts.isoformat() if delivery.sent_ts else '',
                campaign_id,
                campaign.name
            ])
        
        return output.getvalue()
    finally:
        session.close()


def export_failed_emails_to_csv(campaign_id: int) -> str:
    """
    Export failed emails to CSV.
    
    Returns:
        CSV content as string
    """
    session = get_session()
    try:
        campaign = session.query(Campaign).filter_by(id=campaign_id).first()
        if not campaign:
            return ''
        
        deliveries = (
            session.query(CampaignDelivery)
            .filter_by(campaign_id=campaign_id, status='failed')
            .order_by(CampaignDelivery.sequence_no.asc())
            .all()
        )
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Email', 'Error Date', 'Error Message', 'Campaign ID', 'Campaign Name'])
        
        for delivery in deliveries:
            writer.writerow([
                delivery.email,
                delivery.updated_ts.isoformat() if delivery.updated_ts else '',
                delivery.last_error or '',
                campaign_id,
                campaign.name
            ])
        
        return output.getvalue()
    finally:
        session.close()


def export_all_emails_to_csv(campaign_id: int) -> str:
    """
    Export all emails from campaign source with status.
    
    Returns:
        CSV content as string
    """
    session = get_session()
    try:
        campaign = session.query(Campaign).filter_by(id=campaign_id).first()
        if not campaign:
            return ''
        
        deliveries = (
            session.query(CampaignDelivery)
            .filter_by(campaign_id=campaign_id)
            .order_by(CampaignDelivery.sequence_no.asc())
            .all()
        )
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(['Email', 'Status', 'Last Action Date', 'Campaign ID', 'Campaign Name'])
        
        for delivery in deliveries:
            status = (delivery.status or 'pending').capitalize()
            last_action_date = ''
            if delivery.status == 'sent' and delivery.sent_ts:
                last_action_date = delivery.sent_ts.isoformat()
            elif delivery.updated_ts:
                last_action_date = delivery.updated_ts.isoformat()

            writer.writerow([
                delivery.email,
                status,
                last_action_date,
                campaign_id,
                campaign.name
            ])
        
        return output.getvalue()
    finally:
        session.close()


def export_statistics_to_csv(campaign_id: int) -> str:
    """
    Export campaign statistics to CSV.
    
    Returns:
        CSV content as string
    """
    session = get_session()
    try:
        campaign = session.query(Campaign).filter_by(id=campaign_id).first()
        if not campaign:
            return ''
        
        logs = session.query(Log).filter_by(campaign_id=campaign_id).all()
        deliveries = session.query(CampaignDelivery).filter_by(campaign_id=campaign_id).all()
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Campaign info
        writer.writerow(['Metric', 'Value'])
        writer.writerow(['Campaign ID', campaign_id])
        writer.writerow(['Campaign Name', campaign.name])
        writer.writerow(['Provider', campaign.provider])
        writer.writerow(['Status', campaign.status])
        writer.writerow(['Subject', campaign.subject])
        writer.writerow(['Sender Email', campaign.sender_email])
        writer.writerow(['Start Time', campaign.start_ts.isoformat() if campaign.start_ts else ''])
        writer.writerow(['End Time', campaign.end_ts.isoformat() if campaign.end_ts else ''])
        writer.writerow(['Success Count', campaign.success_cnt])
        writer.writerow(['Error Count', campaign.error_cnt])
        writer.writerow(['Tracked Deliveries', len(deliveries)])
        writer.writerow(['Sent Deliveries', len([d for d in deliveries if d.status == 'sent'])])
        writer.writerow(['Failed Deliveries', len([d for d in deliveries if d.status == 'failed'])])
        writer.writerow(['Pending Deliveries', len([d for d in deliveries if d.status == 'pending'])])
        writer.writerow(['Total Logs', len(logs)])
        writer.writerow(['Success Logs', len([l for l in logs if l.level == 'SUCCESS'])])
        writer.writerow(['Error Logs', len([l for l in logs if l.level == 'ERROR'])])
        writer.writerow(['Warning Logs', len([l for l in logs if l.level == 'WARNING'])])
        writer.writerow(['Info Logs', len([l for l in logs if l.level == 'INFO'])])
        
        # Calculate duration
        if campaign.start_ts and campaign.end_ts:
            duration = campaign.end_ts - campaign.start_ts
            writer.writerow(['Duration (seconds)', duration.total_seconds()])
            writer.writerow(['Duration (formatted)', str(duration)])
        elif campaign.start_ts:
            duration = datetime.utcnow() - campaign.start_ts
            writer.writerow(['Duration (seconds)', duration.total_seconds()])
            writer.writerow(['Duration (formatted)', str(duration)])
            writer.writerow(['Note', 'Campaign is still running'])
        
        # Success rate
        total = campaign.success_cnt + campaign.error_cnt
        if total > 0:
            success_rate = (campaign.success_cnt / total) * 100
            writer.writerow(['Success Rate (%)', f'{success_rate:.2f}'])
        
        return output.getvalue()
    finally:
        session.close()


def _get_emails_from_source(campaign: Campaign, limit: Optional[int] = None) -> List[str]:
    """
    Get emails from campaign source (CSV or database).
    
    Args:
        campaign: Campaign object
        limit: Optional limit on number of emails
    
    Returns:
        List of email addresses
    """
    try:
        from backend.utils.database import read_emails_from_table
        from backend.services.campaign_service import read_emails_from_csv
        
        emails = []
        
        if campaign.database_table:
            try:
                table_names = json.loads(campaign.database_table)
                if not isinstance(table_names, list):
                    table_names = [campaign.database_table]
            except (json.JSONDecodeError, TypeError):
                table_names = [campaign.database_table]

            if len(table_names) > 1:
                from backend.utils.database import read_emails_from_tables
                df = read_emails_from_tables(table_names, campaign.email_column)
            else:
                df = read_emails_from_table(table_names[0], campaign.email_column)
            email_col = 'Email' if 'Email' in df.columns else campaign.email_column
            emails = df[email_col].tolist()[:limit] if limit else df[email_col].tolist()
        elif campaign.csv_path and os.path.exists(campaign.csv_path):
            df = read_emails_from_csv(campaign.csv_path, campaign.email_column)
            email_col = campaign.email_column
            emails = df[email_col].tolist()[:limit] if limit else df[email_col].tolist()
        
        return emails
    except Exception:
        return []


import os
