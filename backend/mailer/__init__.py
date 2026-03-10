# Mailer strategies package
from backend.mailer.base import BaseMailer
from backend.mailer.mailersend import MailerSendMailer
from backend.mailer.gmail import GmailMailer

__all__ = ['BaseMailer', 'MailerSendMailer', 'GmailMailer']
