"""Flask application bootstrap for MailSenderZilla."""
from flask import Flask, request, jsonify, send_from_directory
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import os
import uuid
import re
import logging
import traceback
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
_bootstrapped = False


def _to_bool(value: str, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def load_environment() -> str:
    """Load environment variables from env files based on APP_ENV/ENV_FILE."""
    app_env = os.getenv('APP_ENV', 'development').strip().lower()
    explicit_env_file = os.getenv('ENV_FILE', '').strip()

    env_files = []
    if explicit_env_file:
        env_files.append(explicit_env_file)
    else:
        if app_env == 'production':
            env_files.append('.env.production')
        else:
            env_files.append('.env.development')
        env_files.append('.env')

    for env_file in env_files:
        env_path = env_file if os.path.isabs(env_file) else os.path.join(PROJECT_ROOT, env_file)
        if os.path.exists(env_path):
            load_dotenv(env_path, override=False)

    return os.getenv('APP_ENV', app_env).strip().lower()

from backend.models.database import init_db, get_session, Campaign, Log, Settings, Blacklist, Template
from backend.services.campaign_service import CampaignService
from backend.services.template_engine import TemplateEngine
from backend.utils.database import get_all_tables, get_table_columns, preview_table_emails, detect_email_column
from backend.utils.export import (
    export_logs_to_csv, 
    export_sent_emails_to_csv, 
    export_failed_emails_to_csv,
    export_all_emails_to_csv,
    export_statistics_to_csv
)
from backend.utils.backup import create_backup, list_backups, restore_backup, delete_backup

# Initialize template engine for previews
template_engine = TemplateEngine()

# Initialize Flask app
app = Flask(__name__, static_folder='../frontend/dist', static_url_path='')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'uploads')

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Enable CORS
CORS(app)

# Thread pool for running campaigns
executor = ThreadPoolExecutor(max_workers=5)
campaign_task_lock = threading.Lock()
campaign_tasks = {}

# Campaign log callbacks (campaign_id -> socketio room)
campaign_log_rooms = {}


def register_campaign_task(campaign_id: int, future) -> None:
    """Track campaign future so stale running statuses can be detected."""
    with campaign_task_lock:
        campaign_tasks[campaign_id] = future

    def _cleanup(done_future):
        with campaign_task_lock:
            current = campaign_tasks.get(campaign_id)
            if current is done_future:
                campaign_tasks.pop(campaign_id, None)

    future.add_done_callback(_cleanup)


def is_campaign_task_active(campaign_id: int) -> bool:
    """Return True if campaign has an active in-process future."""
    with campaign_task_lock:
        future = campaign_tasks.get(campaign_id)
        if future is None:
            return False
        if future.done():
            campaign_tasks.pop(campaign_id, None)
            return False
        return True


def _extract_valid_total_from_logs(log_rows) -> Optional[int]:
    """Parse total valid recipients from campaign start log."""
    for row in log_rows:
        msg = row.message or ''
        match = re.search(r'Valid:\s*(\d+)', msg)
        if match:
            return int(match.group(1))
    return None


def _extract_sent_count_from_success_log(message: str) -> int:
    """Parse sent recipients count from success batch message."""
    match = re.search(r'Sent to\s+(\d+)\s+recipients', message or '')
    if not match:
        return 0
    return int(match.group(1))


@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection."""
    emit('connected', {'message': 'Connected to MailSenderZilla'})


@socketio.on('join_campaign')
def handle_join_campaign(data):
    """Join campaign log room."""
    from flask_socketio import join_room
    campaign_id = data.get('campaign_id')
    if campaign_id:
        room = f'campaign_{campaign_id}'
        join_room(room)
        campaign_log_rooms[campaign_id] = True
        emit('joined', {'campaign_id': campaign_id})


def log_callback(campaign_id: int, level: str, message: str):
    """Callback for campaign logs - emits to WebSocket."""
    room = f'campaign_{campaign_id}'
    socketio.emit('campaign_log', {
        'campaign_id': campaign_id,
        'level': level,
        'message': message,
        'timestamp': datetime.utcnow().isoformat()
    }, room=room)


def bootstrap_application() -> None:
    """Initialize database and run non-destructive migrations once per process."""
    global _bootstrapped
    if _bootstrapped:
        return

    init_db()
    migrations = [
        ('backend.migrate_add_database_table', 'migrate_add_database_table', 'Migration check failed'),
        ('backend.migrate_add_email_content', 'migrate_add_email_content', 'Email content migration check failed'),
        ('backend.migrate_add_templates', 'migrate_add_templates', 'Templates migration check failed'),
        ('backend.migrate_multi_table', 'migrate_multi_table', 'Multi-table migration check failed'),
    ]
    for module_path, fn_name, warning_prefix in migrations:
        try:
            module = __import__(module_path, fromlist=[fn_name])
            getattr(module, fn_name)()
        except Exception as e:
            logger.warning(f"{warning_prefix}: {e}")

    _bootstrapped = True


# API Routes
@app.route('/api/settings', methods=['GET'])
def get_settings():
    """Get application settings."""
    session = get_session()
    try:
        settings = session.query(Settings).all()
        result = {s.key: s.value for s in settings}
        return jsonify(result)
    finally:
        session.close()


@app.route('/api/settings', methods=['PUT'])
def update_settings():
    """Update application settings."""
    data = request.json
    session = get_session()
    try:
        for key, value in data.items():
            setting = session.query(Settings).filter_by(key=key).first()
            if setting:
                setting.value = str(value)
            else:
                setting = Settings(key=key, value=str(value))
                session.add(setting)
        session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()


@app.route('/api/campaigns', methods=['GET'])
def list_campaigns():
    """List all campaigns."""
    session = get_session()
    try:
        campaigns = session.query(Campaign).order_by(Campaign.start_ts.desc()).all()
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        result = []
        for c in campaigns:
            try:
                start_logs = (
                    session.query(Log.message)
                    .filter(
                        Log.campaign_id == c.id,
                        Log.level == 'INFO',
                        Log.message.like('Campaign started. Total emails:%')
                    )
                    .order_by(Log.ts.desc())
                    .all()
                )
                total_recipients = _extract_valid_total_from_logs(start_logs)

                today_success_logs = (
                    session.query(Log.message)
                    .filter(
                        Log.campaign_id == c.id,
                        Log.level == 'SUCCESS',
                        Log.ts >= today_start
                    )
                    .all()
                )
                sent_today = sum(_extract_sent_count_from_success_log(row.message) for row in today_success_logs)

                processed_total = (c.success_cnt or 0) + (c.error_cnt or 0)
                remaining_total = None
                if total_recipients is not None:
                    remaining_total = max(total_recipients - processed_total, 0)

                result.append({
                    'id': c.id,
                    'name': c.name,
                    'provider': c.provider,
                    'subject': c.subject,
                    'status': c.status,
                    'start_ts': c.start_ts.isoformat() if c.start_ts else None,
                    'end_ts': c.end_ts.isoformat() if c.end_ts else None,
                    'success_cnt': c.success_cnt,
                    'error_cnt': c.error_cnt,
                    'daily_limit': c.daily_limit,
                    'sent_today': sent_today,
                    'total_recipients': total_recipients,
                    'remaining_total': remaining_total
                })
            except Exception as e:
                # Skip campaigns that cause errors (e.g., missing columns)
                print(f"Warning: Error serializing campaign {c.id}: {e}")
                continue
        return jsonify(result)
    except Exception as e:
        print(f"Error listing campaigns: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()


@app.route('/api/campaigns', methods=['POST'])
def create_campaign():
    """Create and start a new campaign."""
    data = request.json
    
    # Validate required fields
    required = ['name', 'provider', 'subject', 'sender_email', 'provider_config']
    for field in required:
        if field not in data:
            return jsonify({'success': False, 'error': f'Missing required field: {field}'}), 400
    
    # Validate data source (either csv_path or database_table must be provided)
    if not data.get('csv_path') and not data.get('database_table'):
        return jsonify({'success': False, 'error': 'Either csv_path or database_table must be provided'}), 400
    
    # Create campaign service
    service = CampaignService(log_callback=log_callback)
    
    # Create campaign
    try:
        # Get email content
        html_body = data.get('html_body')
        vacancies_text = data.get('vacancies_text', '')
        
        # Log content saving
        if html_body:
            logger.info(f"Campaign {data['name']}: Saving HTML body ({len(html_body)} chars)")
        if vacancies_text:
            logger.info(f"Campaign {data['name']}: Saving vacancies text ({len(vacancies_text)} chars)")
        
        campaign_id = service.create_campaign(
            name=data['name'],
            provider=data['provider'],
            subject=data['subject'],
            sender_email=data['sender_email'],
            csv_path=data.get('csv_path'),
            database_table=data.get('database_table'),
            email_column=data.get('email_column'),
            batch_size=data.get('batch_size', 1),
            delay_between_batches=data.get('delay_between_batches', 45),
            daily_limit=data.get('daily_limit', 2000),
            html_body=html_body,
            vacancies_text=vacancies_text,
            provider_config=data['provider_config']
        )
        
        logger.info(f"Campaign {campaign_id} created and content saved")
        
        # Start campaign in background thread
        
        logger.info(f"Creating campaign {campaign_id}: {data['name']}")
        logger.info(f"Campaign {campaign_id}: Provider={data['provider']}, Data Source={'database_table' if data.get('database_table') else 'csv_path'}")
        
        try:
            future = executor.submit(
                service.run_campaign,
                campaign_id,
                html_body,
                data['provider_config'],
                vacancies_text
            )
            register_campaign_task(campaign_id, future)
            logger.info(f"Campaign {campaign_id} submitted to executor successfully")
        except Exception as e:
            logger.error(f"Failed to submit campaign {campaign_id} to executor: {e}\n{traceback.format_exc()}")
            # Update campaign status to failed
            session = get_session()
            try:
                campaign = session.query(Campaign).filter_by(id=campaign_id).first()
                if campaign:
                    campaign.status = 'failed'
                    session.commit()
                    service._log(campaign_id, 'ERROR', f'Failed to start campaign: {str(e)}')
            except Exception as update_error:
                logger.error(f"Failed to update campaign {campaign_id} status: {update_error}")
            finally:
                session.close()
            return jsonify({'success': False, 'error': f'Failed to start campaign: {str(e)}'}), 500
        
        return jsonify({'success': True, 'campaign_id': campaign_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/campaigns/<int:campaign_id>', methods=['GET'])
def get_campaign(campaign_id):
    """Get campaign details."""
    session = get_session()
    try:
        campaign = session.query(Campaign).filter_by(id=campaign_id).first()
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # Handle missing database_table column gracefully
        try:
            database_table = campaign.database_table
        except AttributeError:
            database_table = None
        
        return jsonify({
            'id': campaign.id,
            'name': campaign.name,
            'provider': campaign.provider,
            'subject': campaign.subject,
            'sender_email': campaign.sender_email,
            'status': campaign.status,
            'start_ts': campaign.start_ts.isoformat() if campaign.start_ts else None,
            'end_ts': campaign.end_ts.isoformat() if campaign.end_ts else None,
            'success_cnt': campaign.success_cnt,
            'error_cnt': campaign.error_cnt,
            'batch_size': campaign.batch_size,
            'delay_between_batches': campaign.delay_between_batches,
            'daily_limit': campaign.daily_limit,
            'csv_path': getattr(campaign, 'csv_path', None),
            'database_table': database_table,
            'email_column': getattr(campaign, 'email_column', 'email'),
            'html_body': getattr(campaign, 'html_body', None),
            'vacancies_text': getattr(campaign, 'vacancies_text', None)
        })
    finally:
        session.close()


@app.route('/api/campaigns/<int:campaign_id>/logs', methods=['GET'])
def get_campaign_logs(campaign_id):
    """Get campaign logs."""
    session = get_session()
    try:
        logs = session.query(Log).filter_by(campaign_id=campaign_id).order_by(Log.ts.asc()).all()
        result = [{
            'id': l.id,
            'ts': l.ts.isoformat(),
            'level': l.level,
            'message': l.message
        } for l in logs]
        return jsonify(result)
    finally:
        session.close()


@app.route('/api/campaigns/<int:campaign_id>/html', methods=['GET'])
def get_campaign_html(campaign_id):
    """Download rendered HTML email."""
    session = get_session()
    try:
        campaign = session.query(Campaign).filter_by(id=campaign_id).first()
        if not campaign:
            return jsonify({'error': 'Campaign not found'}), 404
        
        # TODO: Store rendered HTML in campaign or regenerate
        # For now, return a placeholder
        template_engine = TemplateEngine()
        html = template_engine.render(cta_subject=campaign.subject)
        
        return html, 200, {'Content-Type': 'text/html'}
    finally:
        session.close()


@app.route('/api/campaigns/<int:campaign_id>/start', methods=['POST'])
def start_campaign(campaign_id):
    """Manually start a pending campaign."""
    session = get_session()
    try:
        campaign = session.query(Campaign).filter_by(id=campaign_id).first()
        if not campaign:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
        
        # Only allow starting pending campaigns
        if campaign.status != 'pending':
            return jsonify({'success': False, 'error': f'Cannot start campaign with status: {campaign.status}'}), 400
        
        # Get provider config from request body or settings
        data = request.json or {}
        provider_config = data.get('provider_config')
        
        if not provider_config:
            # Try to get from settings
            if campaign.provider == 'mailersend':
                mailersend_token = session.query(Settings).filter_by(key='mailersend_api_token').first()
                if mailersend_token and mailersend_token.value:
                    provider_config = {'api_token': mailersend_token.value}
            elif campaign.provider == 'gmail':
                gmail_password = session.query(Settings).filter_by(key='gmail_app_password').first()
                if gmail_password and gmail_password.value:
                    provider_config = {'app_password': gmail_password.value}
        
        if not provider_config:
            return jsonify({
                'success': False, 
                'error': f'Provider credentials required. Please provide provider_config or save credentials in Settings.'
            }), 400
        
        # Get email content from request body or use stored content from campaign
        html_body = data.get('html_body') or getattr(campaign, 'html_body', None)
        vacancies_text = data.get('vacancies_text') or getattr(campaign, 'vacancies_text', None) or ''
        
        logger.info(f"Campaign {campaign_id} start: Using stored content - html_body={'Yes' if html_body else 'No'}, vacancies_text={'Yes' if vacancies_text else 'No'}")
        
        if not html_body and not vacancies_text:
            logger.warning(f"Campaign {campaign_id}: No email content found (neither html_body nor vacancies_text)")
        
        # Create campaign service and start campaign
        service = CampaignService(log_callback=log_callback)
        
        logger.info(f"Manually starting campaign {campaign_id}: {campaign.name}")
        try:
            future = executor.submit(
                service.run_campaign,
                campaign_id,
                html_body,
                provider_config,
                vacancies_text
            )
            register_campaign_task(campaign_id, future)
            logger.info(f"Campaign {campaign_id} submitted to executor successfully")
            return jsonify({'success': True, 'message': 'Campaign started successfully'})
        except Exception as e:
            logger.error(f"Failed to submit campaign {campaign_id} to executor: {e}\n{traceback.format_exc()}")
            # Update campaign status to failed
            campaign.status = 'failed'
            session.commit()
            service._log(campaign_id, 'ERROR', f'Failed to start campaign: {str(e)}')
            return jsonify({'success': False, 'error': f'Failed to start campaign: {str(e)}'}), 500
            
    except Exception as e:
        session.rollback()
        logger.error(f"Error starting campaign {campaign_id}: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()


@app.route('/api/campaigns/<int:campaign_id>/pause', methods=['POST'])
def pause_campaign(campaign_id):
    """Pause a running campaign."""
    session = get_session()
    try:
        campaign = session.query(Campaign).filter_by(id=campaign_id).first()
        if not campaign:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
        
        # Only allow pausing running campaigns
        if campaign.status != 'running':
            return jsonify({'success': False, 'error': f'Cannot pause campaign with status: {campaign.status}'}), 400
        
        # Set status to paused
        campaign.status = 'paused'
        session.commit()
        
        logger.info(f"Campaign {campaign_id} paused")
        return jsonify({'success': True, 'message': 'Campaign paused successfully'})
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to pause campaign {campaign_id}: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()


@app.route('/api/campaigns/<int:campaign_id>/resume', methods=['POST'])
def resume_campaign(campaign_id):
    """Resume a paused campaign."""
    session = get_session()
    try:
        campaign = session.query(Campaign).filter_by(id=campaign_id).first()
        if not campaign:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
        
        # Only allow resuming paused campaigns
        if campaign.status != 'paused':
            return jsonify({'success': False, 'error': f'Cannot resume campaign with status: {campaign.status}'}), 400
        
        # Get provider config from settings or request
        data = request.json or {}
        provider_config = data.get('provider_config')
        
        if not provider_config:
            # Try to get from settings
            if campaign.provider == 'mailersend':
                mailersend_token = session.query(Settings).filter_by(key='mailersend_api_token').first()
                if mailersend_token and mailersend_token.value:
                    provider_config = {'api_token': mailersend_token.value}
            elif campaign.provider == 'gmail':
                gmail_password = session.query(Settings).filter_by(key='gmail_app_password').first()
                if gmail_password and gmail_password.value:
                    provider_config = {'app_password': gmail_password.value}
        
        if not provider_config:
            return jsonify({
                'success': False, 
                'error': 'Provider credentials required. Please provide provider_config or save credentials in Settings.'
            }), 400
        
        # Get stored email content
        html_body = getattr(campaign, 'html_body', None)
        vacancies_text = getattr(campaign, 'vacancies_text', None) or ''
        
        if not html_body and not vacancies_text:
            return jsonify({
                'success': False,
                'error': 'Email content not found. Cannot resume campaign without content.'
            }), 400
        
        # Change status back to running and resume
        campaign.status = 'running'
        session.commit()
        
        # Create campaign service and resume
        service = CampaignService(log_callback=log_callback)
        try:
            future = executor.submit(
                service.run_campaign,
                campaign_id,
                html_body,
                provider_config,
                vacancies_text
            )
            register_campaign_task(campaign_id, future)
            logger.info(f"Campaign {campaign_id} resumed successfully")
            return jsonify({'success': True, 'message': 'Campaign resumed successfully'})
        except Exception as e:
            # Mark as failed if resume fails
            campaign.status = 'failed'
            session.commit()
            logger.error(f"Failed to resume campaign {campaign_id}: {e}\n{traceback.format_exc()}")
            return jsonify({'success': False, 'error': f'Failed to resume campaign: {str(e)}'}), 500
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to resume campaign {campaign_id}: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()


@app.route('/api/campaigns/<int:campaign_id>/clone', methods=['POST'])
def clone_campaign(campaign_id):
    """Clone an existing campaign."""
    session = get_session()
    try:
        source_campaign = session.query(Campaign).filter_by(id=campaign_id).first()
        if not source_campaign:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
        
        # Get optional new name from request
        data = request.json or {}
        new_name = data.get('name') or f"{source_campaign.name} (Copy)"
        
        # Create new campaign with same settings
        new_campaign = Campaign(
            name=new_name,
            provider=source_campaign.provider,
            subject=source_campaign.subject,
            sender_email=source_campaign.sender_email,
            csv_path=source_campaign.csv_path,
            database_table=source_campaign.database_table,
            email_column=source_campaign.email_column,
            batch_size=source_campaign.batch_size,
            delay_between_batches=source_campaign.delay_between_batches,
            daily_limit=source_campaign.daily_limit,
            html_body=source_campaign.html_body,
            vacancies_text=source_campaign.vacancies_text,
            status='pending',
            start_ts=None,
            end_ts=None,
            success_cnt=0,
            error_cnt=0
        )
        
        session.add(new_campaign)
        session.commit()
        
        new_campaign_id = new_campaign.id
        logger.info(f"Campaign {campaign_id} cloned to {new_campaign_id}")
        
        return jsonify({
            'success': True,
            'id': new_campaign_id,
            'message': 'Campaign cloned successfully'
        })
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to clone campaign {campaign_id}: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()


@app.route('/api/campaigns/<int:campaign_id>/restart', methods=['POST'])
def restart_campaign(campaign_id):
    """Restart a completed or failed campaign."""
    session = get_session()
    try:
        campaign = session.query(Campaign).filter_by(id=campaign_id).first()
        if not campaign:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
        
        # Allow restart for stale "running" campaigns (no active executor task).
        if campaign.status == 'running':
            if is_campaign_task_active(campaign_id):
                return jsonify({'success': False, 'error': 'Cannot restart an active running campaign'}), 400
            logger.warning(f"Campaign {campaign_id} has stale running status without active task, allowing restart.")
            campaign.status = 'failed'
            session.commit()
        
        # Get provider config from settings
        if campaign.provider == 'mailersend':
            mailersend_token = session.query(Settings).filter_by(key='mailersend_api_token').first()
            provider_config = {'api_token': mailersend_token.value} if mailersend_token and mailersend_token.value else None
        elif campaign.provider == 'gmail':
            gmail_password = session.query(Settings).filter_by(key='gmail_app_password').first()
            provider_config = {'app_password': gmail_password.value} if gmail_password and gmail_password.value else None
        else:
            provider_config = None
        
        if not provider_config:
            # Reset campaign status only if no saved credentials
            campaign.status = 'pending'
            campaign.start_ts = datetime.utcnow()
            campaign.end_ts = None
            campaign.success_cnt = 0
            campaign.error_cnt = 0
            session.commit()
            return jsonify({
                'success': True, 
                'warning': 'Campaign reset. To fully restart, ensure provider credentials are saved in Settings. Email content will need to be provided manually.'
            })
        
        # Reset campaign status
        campaign.status = 'pending'
        campaign.start_ts = datetime.utcnow()
        campaign.end_ts = None
        campaign.success_cnt = 0
        campaign.error_cnt = 0
        session.commit()
        
        # Get stored email content
        html_body = getattr(campaign, 'html_body', None)
        vacancies_text = getattr(campaign, 'vacancies_text', None) or ''
        
        logger.info(f"Campaign {campaign_id} restart: Using stored content - html_body={'Yes' if html_body else 'No'}, vacancies_text={'Yes' if vacancies_text else 'No'}")
        
        # Try to restart if we have provider config and email content
        if provider_config and (html_body or vacancies_text):
            # Create campaign service and restart
            service = CampaignService(log_callback=log_callback)
            try:
                future = executor.submit(
                    service.run_campaign,
                    campaign_id,
                    html_body,
                    provider_config,
                    vacancies_text
                )
                register_campaign_task(campaign_id, future)
                logger.info(f"Campaign {campaign_id} restarted successfully")
                return jsonify({'success': True, 'message': 'Campaign restarted successfully'})
            except Exception as e:
                logger.error(f"Failed to restart campaign {campaign_id}: {e}\n{traceback.format_exc()}")
                return jsonify({'success': False, 'error': f'Failed to restart campaign: {str(e)}'}), 500
        else:
            # Just reset status
            return jsonify({
                'success': True, 
                'message': 'Campaign reset. To fully restart, ensure provider credentials are saved in Settings and email content is available.'
            })
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()


@app.route('/api/campaigns/<int:campaign_id>/export/logs', methods=['GET'])
def export_campaign_logs(campaign_id):
    """Export campaign logs to CSV."""
    try:
        csv_content = export_logs_to_csv(campaign_id)
        if not csv_content:
            return jsonify({'success': False, 'error': 'Campaign not found or no logs'}), 404
        
        from flask import Response
        response = Response(csv_content, mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename=campaign_{campaign_id}_logs.csv'
        return response
    except Exception as e:
        logger.error(f"Failed to export logs for campaign {campaign_id}: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/campaigns/<int:campaign_id>/export/sent', methods=['GET'])
def export_campaign_sent(campaign_id):
    """Export successfully sent emails to CSV."""
    try:
        csv_content = export_sent_emails_to_csv(campaign_id)
        if not csv_content:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
        
        from flask import Response
        response = Response(csv_content, mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename=campaign_{campaign_id}_sent.csv'
        return response
    except Exception as e:
        logger.error(f"Failed to export sent emails for campaign {campaign_id}: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/campaigns/<int:campaign_id>/export/failed', methods=['GET'])
def export_campaign_failed(campaign_id):
    """Export failed emails to CSV."""
    try:
        csv_content = export_failed_emails_to_csv(campaign_id)
        if not csv_content:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
        
        from flask import Response
        response = Response(csv_content, mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename=campaign_{campaign_id}_failed.csv'
        return response
    except Exception as e:
        logger.error(f"Failed to export failed emails for campaign {campaign_id}: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/campaigns/<int:campaign_id>/export/all', methods=['GET'])
def export_campaign_all(campaign_id):
    """Export all emails from campaign source with status to CSV."""
    try:
        csv_content = export_all_emails_to_csv(campaign_id)
        if not csv_content:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
        
        from flask import Response
        response = Response(csv_content, mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename=campaign_{campaign_id}_all_emails.csv'
        return response
    except Exception as e:
        logger.error(f"Failed to export all emails for campaign {campaign_id}: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/campaigns/<int:campaign_id>/export/statistics', methods=['GET'])
def export_campaign_statistics(campaign_id):
    """Export campaign statistics to CSV."""
    try:
        csv_content = export_statistics_to_csv(campaign_id)
        if not csv_content:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
        
        from flask import Response
        response = Response(csv_content, mimetype='text/csv')
        response.headers['Content-Disposition'] = f'attachment; filename=campaign_{campaign_id}_statistics.csv'
        return response
    except Exception as e:
        logger.error(f"Failed to export statistics for campaign {campaign_id}: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/campaigns/<int:campaign_id>', methods=['DELETE'])
def delete_campaign(campaign_id):
    """Delete a campaign and its logs."""
    session = get_session()
    try:
        campaign = session.query(Campaign).filter_by(id=campaign_id).first()
        if not campaign:
            return jsonify({'success': False, 'error': 'Campaign not found'}), 404
        
        # Block deletion only for active running campaigns.
        if campaign.status == 'running':
            if is_campaign_task_active(campaign_id):
                return jsonify({'success': False, 'error': 'Cannot delete an active running campaign. Please wait for it to complete.'}), 400
            logger.warning(f"Campaign {campaign_id} has stale running status without active task, allowing delete.")
        
        # Delete campaign (logs will be cascade deleted due to relationship)
        session.delete(campaign)
        session.commit()
        
        return jsonify({'success': True, 'message': 'Campaign deleted successfully'})
    except Exception as e:
        session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()


@app.route('/api/upload', methods=['POST'])
def upload_csv():
    """Upload CSV file."""
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'File must be a CSV'}), 400
    
    # Create uploads directory if not exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Save file
    filename = secure_filename(f"{uuid.uuid4()}_{file.filename}")
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)
    
    return jsonify({'success': True, 'path': filepath, 'filename': filename})


@app.route('/api/blacklist', methods=['GET'])
def get_blacklist():
    """Get blacklist."""
    session = get_session()
    try:
        blacklist = session.query(Blacklist).all()
        result = [{'email': b.email, 'reason': b.reason, 'added_ts': b.added_ts.isoformat()} for b in blacklist]
        return jsonify(result)
    finally:
        session.close()


@app.route('/api/blacklist', methods=['POST'])
def add_to_blacklist():
    """Add email to blacklist."""
    data = request.json
    email = data.get('email')
    reason = data.get('reason', 'manual')
    
    if not email:
        return jsonify({'error': 'Email required'}), 400
    
    session = get_session()
    try:
        existing = session.query(Blacklist).filter_by(email=email).first()
        if existing:
            return jsonify({'success': True, 'message': 'Already in blacklist'})
        
        blacklist_entry = Blacklist(email=email, reason=reason)
        session.add(blacklist_entry)
        session.commit()
        return jsonify({'success': True})
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        session.close()


@app.route('/api/database/tables', methods=['GET'])
def get_database_tables():
    """Get list of all tables in the database."""
    try:
        tables = get_all_tables()
        return jsonify({'success': True, 'tables': tables})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/database/tables/<table_name>/columns', methods=['GET'])
def get_table_columns_api(table_name):
    """Get columns for a specific table."""
    try:
        columns = get_table_columns(table_name)
        email_column = detect_email_column(table_name, columns)
        return jsonify({
            'success': True,
            'columns': columns,
            'email_column': email_column
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/database/tables/<table_name>/preview', methods=['GET'])
def preview_table(table_name):
    """Preview emails from a table."""
    email_column = request.args.get('email_column')
    limit = int(request.args.get('limit', 10))
    
    try:
        result = preview_table_emails(table_name, email_column, limit)
        if 'error' in result:
            return jsonify({'success': False, 'error': result['error']}), 400
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400




# Templates API
@app.route('/api/templates', methods=['GET'])
def list_templates():
    """List all email templates."""
    session = get_session()
    try:
        templates = session.query(Template).order_by(Template.updated_ts.desc()).all()
        result = [{
            'id': t.id,
            'name': t.name,
            'subject': t.subject,
            'html_body': t.html_body,
            'vacancies_text': t.vacancies_text,
            'created_ts': t.created_ts.isoformat() if t.created_ts else None,
            'updated_ts': t.updated_ts.isoformat() if t.updated_ts else None
        } for t in templates]
        return jsonify(result)
    finally:
        session.close()


@app.route('/api/templates/<int:template_id>', methods=['GET'])
def get_template(template_id):
    """Get a single template by ID."""
    session = get_session()
    try:
        template = session.query(Template).filter_by(id=template_id).first()
        if not template:
            return jsonify({'error': 'Template not found'}), 404
        
        return jsonify({
            'id': template.id,
            'name': template.name,
            'subject': template.subject,
            'html_body': template.html_body,
            'vacancies_text': template.vacancies_text,
            'created_ts': template.created_ts.isoformat() if template.created_ts else None,
            'updated_ts': template.updated_ts.isoformat() if template.updated_ts else None
        })
    finally:
        session.close()


@app.route('/api/templates', methods=['POST'])
def create_template():
    """Create a new email template."""
    session = get_session()
    try:
        data = request.json
        
        # Validate required fields
        if not data.get('name') or not data.get('subject'):
            return jsonify({'success': False, 'error': 'Name and subject are required'}), 400
        
        template = Template(
            name=data['name'],
            subject=data['subject'],
            html_body=data.get('html_body'),
            vacancies_text=data.get('vacancies_text'),
            created_ts=datetime.utcnow(),
            updated_ts=datetime.utcnow()
        )
        session.add(template)
        session.commit()
        
        return jsonify({
            'success': True,
            'id': template.id,
            'message': 'Template created successfully'
        })
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to create template: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()


@app.route('/api/templates/<int:template_id>', methods=['PUT'])
def update_template(template_id):
    """Update an existing template."""
    session = get_session()
    try:
        template = session.query(Template).filter_by(id=template_id).first()
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
        
        data = request.json
        
        if 'name' in data:
            template.name = data['name']
        if 'subject' in data:
            template.subject = data['subject']
        if 'html_body' in data:
            template.html_body = data['html_body']
        if 'vacancies_text' in data:
            template.vacancies_text = data['vacancies_text']
        
        template.updated_ts = datetime.utcnow()
        session.commit()
        
        return jsonify({'success': True, 'message': 'Template updated successfully'})
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to update template {template_id}: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()


@app.route('/api/templates/<int:template_id>', methods=['DELETE'])
def delete_template(template_id):
    """Delete a template."""
    session = get_session()
    try:
        template = session.query(Template).filter_by(id=template_id).first()
        if not template:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
        
        session.delete(template)
        session.commit()
        
        return jsonify({'success': True, 'message': 'Template deleted successfully'})
    except Exception as e:
        session.rollback()
        logger.error(f"Failed to delete template {template_id}: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 400
    finally:
        session.close()


# Backup API
@app.route('/api/backup', methods=['POST'])
def create_db_backup():
    """Create a backup of the database."""
    try:
        backup_path = create_backup()
        return jsonify({
            'success': True,
            'message': 'Backup created successfully',
            'path': backup_path
        })
    except Exception as e:
        logger.error(f"Failed to create backup: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/backup', methods=['GET'])
def list_db_backups():
    """List all database backups."""
    try:
        backups = list_backups()
        return jsonify({
            'success': True,
            'backups': backups
        })
    except Exception as e:
        logger.error(f"Failed to list backups: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/backup/restore', methods=['POST'])
def restore_db_backup():
    """Restore database from backup."""
    data = request.json
    backup_path = data.get('path')
    
    if not backup_path:
        return jsonify({'success': False, 'error': 'Backup path is required'}), 400
    
    try:
        restore_backup(backup_path)
        return jsonify({
            'success': True,
            'message': 'Database restored successfully'
        })
    except Exception as e:
        logger.error(f"Failed to restore backup: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/backup/<path:backup_path>', methods=['DELETE'])
def delete_db_backup(backup_path):
    """Delete a backup file."""
    try:
        delete_backup(backup_path)
        return jsonify({
            'success': True,
            'message': 'Backup deleted successfully'
        })
    except Exception as e:
        logger.error(f"Failed to delete backup: {e}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/preview/email', methods=['POST'])
def preview_email():
    """Preview rendered HTML email."""
    data = request.json or {}
    vacancies_text = data.get('vacancies_text', '')
    subject = data.get('subject', 'ASAP Marine Update')
    html_body = data.get('html_body', '')
    
    try:
        if html_body:
            # If only a fragment is provided, wrap it into a full HTML document for stable iframe preview.
            has_html_tag = bool(re.search(r'<\s*html[\s>]', html_body, flags=re.IGNORECASE))
            has_body_tag = bool(re.search(r'<\s*body[\s>]', html_body, flags=re.IGNORECASE))
            if has_html_tag or has_body_tag:
                rendered_html = html_body
            else:
                rendered_html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{subject}</title>
</head>
<body>
{html_body}
</body>
</html>"""
        else:
            # Render using template engine
            rendered_html = template_engine.render(
                vacancies_text=vacancies_text,
                cta_subject=subject
            )
        
        return jsonify({'success': True, 'html': rendered_html})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/openapi.json', methods=['GET'])
def openapi_spec():
    """OpenAPI spec for quick API testing with Swagger UI."""
    host_url = request.host_url.rstrip('/')
    spec = {
        "openapi": "3.0.3",
        "info": {
            "title": "MailSenderZilla API",
            "version": "1.0.0",
            "description": "API for campaigns, settings, templates, blacklist and backups."
        },
        "servers": [{"url": host_url}],
        "paths": {
            "/api/settings": {
                "get": {"summary": "Get settings", "responses": {"200": {"description": "OK"}}},
                "put": {"summary": "Update settings", "responses": {"200": {"description": "OK"}}}
            },
            "/api/campaigns": {
                "get": {"summary": "List campaigns", "responses": {"200": {"description": "OK"}}},
                "post": {"summary": "Create campaign", "responses": {"200": {"description": "OK"}}}
            },
            "/api/campaigns/{campaign_id}": {
                "get": {
                    "summary": "Get campaign details",
                    "parameters": [{"name": "campaign_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "OK"}, "404": {"description": "Not found"}}
                },
                "delete": {
                    "summary": "Delete campaign",
                    "parameters": [{"name": "campaign_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "Deleted"}, "400": {"description": "Cannot delete"}}
                }
            },
            "/api/campaigns/{campaign_id}/logs": {
                "get": {
                    "summary": "Get campaign logs",
                    "parameters": [{"name": "campaign_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "OK"}}
                }
            },
            "/api/campaigns/{campaign_id}/start": {
                "post": {
                    "summary": "Start campaign",
                    "parameters": [{"name": "campaign_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "OK"}, "400": {"description": "Bad request"}}
                }
            },
            "/api/campaigns/{campaign_id}/pause": {
                "post": {
                    "summary": "Pause campaign",
                    "parameters": [{"name": "campaign_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "OK"}}
                }
            },
            "/api/campaigns/{campaign_id}/resume": {
                "post": {
                    "summary": "Resume campaign",
                    "parameters": [{"name": "campaign_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "OK"}}
                }
            },
            "/api/campaigns/{campaign_id}/restart": {
                "post": {
                    "summary": "Restart campaign",
                    "parameters": [{"name": "campaign_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "OK"}}
                }
            },
            "/api/campaigns/{campaign_id}/clone": {
                "post": {
                    "summary": "Clone campaign",
                    "parameters": [{"name": "campaign_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                    "responses": {"200": {"description": "OK"}}
                }
            },
            "/api/upload": {
                "post": {"summary": "Upload CSV", "responses": {"200": {"description": "OK"}}}
            },
            "/api/blacklist": {
                "get": {"summary": "Get blacklist", "responses": {"200": {"description": "OK"}}},
                "post": {"summary": "Add to blacklist", "responses": {"200": {"description": "OK"}}}
            },
            "/api/database/tables": {
                "get": {"summary": "Get DB tables", "responses": {"200": {"description": "OK"}}}
            },
            "/api/database/tables/{table_name}/columns": {
                "get": {
                    "summary": "Get table columns",
                    "parameters": [{"name": "table_name", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "OK"}}
                }
            },
            "/api/database/tables/{table_name}/preview": {
                "get": {
                    "summary": "Preview table emails",
                    "parameters": [{"name": "table_name", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "OK"}}
                }
            },
            "/api/preview/email": {
                "post": {"summary": "Preview email HTML", "responses": {"200": {"description": "OK"}}}
            },
            "/api/backup": {
                "get": {"summary": "List backups", "responses": {"200": {"description": "OK"}}},
                "post": {"summary": "Create backup", "responses": {"200": {"description": "OK"}}}
            },
            "/api/backup/restore": {
                "post": {"summary": "Restore backup", "responses": {"200": {"description": "OK"}}}
            },
            "/api/backup/{backup_path}": {
                "delete": {
                    "summary": "Delete backup",
                    "parameters": [{"name": "backup_path", "in": "path", "required": True, "schema": {"type": "string"}}],
                    "responses": {"200": {"description": "OK"}}
                }
            }
        }
    }
    return jsonify(spec)


@app.route('/api/docs', methods=['GET'])
def swagger_docs():
    """Swagger UI page for API testing."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8" />
      <title>MailSenderZilla API Docs</title>
      <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
      <style>
        body { margin: 0; background: #f8f5ef; }
        #swagger-ui { max-width: 1200px; margin: 0 auto; }
      </style>
    </head>
    <body>
      <div id="swagger-ui"></div>
      <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
      <script>
        window.ui = SwaggerUIBundle({
          url: '/api/openapi.json',
          dom_id: '#swagger-ui',
          deepLinking: true,
          presets: [SwaggerUIBundle.presets.apis]
        });
      </script>
    </body>
    </html>
    """


# Serve React app
@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve_react_app(path):
    """Serve React application."""
    # Check if frontend is built
    if not os.path.exists(app.static_folder) or not os.path.isdir(app.static_folder):
        # Frontend not built - show API info page
        if path.startswith('api') or path.startswith('socket.io'):
            # Let API routes pass through
            return jsonify({'error': 'Not found'}), 404
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>MailSenderZilla - Backend API</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 800px; margin: 50px auto; padding: 20px; }}
                h1 {{ color: #333; }}
                .info {{ background: #f0f0f0; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .api-link {{ color: #0066cc; text-decoration: none; }}
                .api-link:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <h1>🚀 MailSenderZilla Backend API</h1>
            <div class="info">
                <p><strong>Backend is running!</strong></p>
                <p>The frontend has not been built yet. To use the web interface:</p>
                <ol>
                    <li>Install Node.js from <a href="https://nodejs.org/">nodejs.org</a></li>
                    <li>Restart your terminal</li>
                    <li>Run: <code>cd frontend && npm install && npm run build</code></li>
                    <li>Or for development: <code>cd frontend && npm run dev</code> (runs on port 3000)</li>
                </ol>
            </div>
            <h2>Available API Endpoints:</h2>
            <ul>
                <li><a href="/api/settings" class="api-link">GET /api/settings</a> - Get settings</li>
                <li><a href="/api/campaigns" class="api-link">GET /api/campaigns</a> - List campaigns</li>
                <li><a href="/api/blacklist" class="api-link">GET /api/blacklist</a> - Get blacklist</li>
            </ul>
            <p><em>Backend running on port 5000</em></p>
        </body>
        </html>
        """, 200
    
    # Serve built React app
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    else:
        index_path = os.path.join(app.static_folder, 'index.html')
        if os.path.exists(index_path):
            return send_from_directory(app.static_folder, 'index.html')
        else:
            return jsonify({'error': 'Frontend not built. Run: cd frontend && npm run build'}), 503


if __name__ == '__main__':
    app_env = load_environment()
    bootstrap_application()

    default_debug = app_env == 'development'
    debug_mode = _to_bool(os.getenv('MAILSENDER_DEBUG'), default=default_debug)
    allow_unsafe_werkzeug = _to_bool(os.getenv('ALLOW_UNSAFE_WERKZEUG'), default=True)

    socketio.run(
        app,
        host=os.getenv('HOST', '0.0.0.0'),
        port=int(os.getenv('PORT', '5000')),
        debug=debug_mode,
        use_reloader=debug_mode,
        allow_unsafe_werkzeug=allow_unsafe_werkzeug
    )
