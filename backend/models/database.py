"""SQLAlchemy database models for MailSenderZilla."""
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import os
import sys

Base = declarative_base()


class Settings(Base):
    """Application settings table."""
    __tablename__ = 'settings'
    
    key = Column(String, primary_key=True)
    value = Column(Text)


class Campaign(Base):
    """Campaign tracking table."""
    __tablename__ = 'campaigns'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    provider = Column(String, nullable=False)  # 'mailersend' or 'gmail'
    subject = Column(String, nullable=False)
    sender_email = Column(String, nullable=False)
    csv_path = Column(String)  # Path to uploaded CSV file (if using CSV)
    database_table = Column(Text)  # Database table names (JSON array if multiple tables)
    email_column = Column(String, default='email')  # Column name containing emails
    batch_size = Column(Integer, default=1)
    delay_between_batches = Column(Integer, default=45)  # seconds
    daily_limit = Column(Integer, default=2000)
    html_body = Column(Text)  # Stored HTML email content
    vacancies_text = Column(Text)  # Stored plain text vacancies
    start_ts = Column(DateTime)
    end_ts = Column(DateTime)
    success_cnt = Column(Integer, default=0)
    error_cnt = Column(Integer, default=0)
    status = Column(String, default='pending')  # pending, running, paused, completed, failed
    
    # Relationships
    logs = relationship("Log", back_populates="campaign", cascade="all, delete-orphan")


class Log(Base):
    """Campaign logs table."""
    __tablename__ = 'logs'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    campaign_id = Column(Integer, ForeignKey('campaigns.id'), nullable=False)
    ts = Column(DateTime, default=datetime.utcnow, nullable=False)
    level = Column(String, nullable=False)  # INFO, WARNING, ERROR, SUCCESS
    message = Column(Text, nullable=False)
    
    # Relationships
    campaign = relationship("Campaign", back_populates="logs")


class Blacklist(Base):
    """Email blacklist table."""
    __tablename__ = 'blacklist'
    
    email = Column(String, primary_key=True)
    reason = Column(String)  # 'unsubscribe', 'bounce', 'manual', etc.
    added_ts = Column(DateTime, default=datetime.utcnow)


class Template(Base):
    """Email template table."""
    __tablename__ = 'templates'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    html_body = Column(Text)  # HTML content
    vacancies_text = Column(Text)  # Plain text vacancies (optional)
    created_ts = Column(DateTime, default=datetime.utcnow)
    updated_ts = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# Database setup
DB_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    'Main_DataBase.db'
)

_engine = None
_SessionLocal = None


def get_engine():
    """Get SQLAlchemy engine."""
    global _engine
    if _engine is None:
        # check_same_thread=False allows per-thread sessions across Flask/SocketIO workers.
        _engine = create_engine(
            f'sqlite:///{DB_PATH}',
            echo=False,
            connect_args={"check_same_thread": False}
        )
    return _engine


def get_session():
    """Get database session."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine())
    return _SessionLocal()


def init_db():
    """Initialize database tables."""
    # Set UTF-8 encoding for Windows console
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except AttributeError:
            # Python < 3.7 fallback
            pass
    
    engine = get_engine()
    Base.metadata.create_all(engine)
    try:
        print(f"✅ Database initialized at {DB_PATH}")
    except UnicodeEncodeError:
        print(f"Database initialized at {DB_PATH}")
