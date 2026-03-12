"""Template engine for rendering HTML emails from plain text vacancies."""
from jinja2 import Environment, FileSystemLoader, Template
from typing import Dict, Any
import os
import re
import html


class TemplateEngine:
    """Jinja2-based template engine for email rendering."""
    
    def __init__(self, template_dir: str = None):
        """
        Initialize template engine.
        
        Args:
            template_dir: Directory containing HTML templates (default: templates/)
        """
        if template_dir is None:
            # Default to templates/ in project root
            template_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'templates'
            )
        
        self.template_dir = template_dir
        self.env = Environment(loader=FileSystemLoader(template_dir))
        
        # Default template HTML if file not found
        self.default_template = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{{ cta_subject or 'ASAP Marine Update' }}</title>
    <style>
        body { font-family: Arial, sans-serif; font-size: 18px; line-height: 1.7; color: #333; max-width: 650px; margin: 0 auto; padding: 20px; }
        .header-logo { text-align: center; margin: 0 0 16px 0; }
        .content { background-color: #ffffff; padding: 20px; }
        .vacancy-block { background-color: #ecf0f1; padding: 15px; margin: 15px 0; border-left: 4px solid #3498db; border-radius: 4px; white-space: pre-wrap; }
        .footer { font-size: 0.9em; color: #7f8c8d; margin-top: 20px; padding-top: 15px; border-top: 1px solid #ecf0f1; }
    </style>
</head>
<body>
    <div class="header-logo">
        <img src="https://i.imgur.com/PUn562O.png" alt="A.S.A.P. Marine Crew" style="display:inline-block; max-width: 220px; width: 100%; height: auto; border: 0;" />
    </div>
    <div class="content">
        {% if cta_body %}
        <p>{{ cta_body }}</p>
        {% endif %}
        
        {% if vacancies %}
        <h2 style="color: #2c3e50; margin-top: 30px; margin-bottom: 20px;">We are looking for:</h2>
        <div class="vacancy-block">{{ vacancies }}</div>
        {% endif %}
        
        <div class="footer">
            <p><strong>Best regards,</strong><br>ASAP Marine Agency</p>
            <p style="margin-top: 15px; font-size: 0.85em;">
                If you no longer wish to receive emails, reply with <strong>UNSUBSCRIBE</strong>.
            </p>
        </div>
    </div>
</body>
</html>"""
    
    def load_template(self, template_name: str = 'template.html') -> Template:
        """
        Load template from file.
        
        Args:
            template_name: Name of template file
            
        Returns:
            Jinja2 Template object
        """
        try:
            return self.env.get_template(template_name)
        except Exception:
            # Fallback to default template
            return Template(self.default_template)
    
    def wrap_vacancies(self, plain_text: str) -> str:
        """
        Wrap plain text vacancies into HTML format.
        
        Preserves line breaks and basic formatting.
        
        Args:
            plain_text: Plain text vacancy description
            
        Returns:
            Formatted HTML string
        """
        if not plain_text:
            return ""

        text = plain_text.strip().replace('\r\n', '\n').replace('\r', '\n')
        blocks = [b.strip() for b in re.split(r'\n\s*\n+', text) if b.strip()]
        if not blocks:
            return ""

        rendered_blocks = []
        for block in blocks:
            safe_block = html.escape(block).replace('\n', '<br>')
            rendered_blocks.append(f'<div class="vacancy-block">{safe_block}</div>')

        return ''.join(rendered_blocks)

    def normalize_cta_body(self, cta_body: str) -> str:
        """
        Normalize CTA body to keep rendering style consistent.

        If HTML tags are present, keep as-is. Otherwise escape and preserve line breaks.
        """
        if not cta_body:
            return ""

        body = cta_body.strip()
        if not body:
            return ""

        has_html_tag = bool(re.search(r'<\s*[a-zA-Z][^>]*>', body))
        if has_html_tag:
            return body

        safe = html.escape(body)
        safe = self._linkify_urls(safe)
        return safe.replace('\n', '<br>')
    
    def render(
        self,
        vacancies_text: str = "",
        cta_subject: str = "ASAP Marine Update",
        cta_body: str = "Good day, Seafarers! 🌊<br><br>This is <strong>ASAP Marine Agency</strong>.<br><br>We are — leading crewing agency from Odesa, Ukraine — invites you to join our official Telegram channel 👉 <a href=\"https://t.me/asapcrewing\">https://t.me/asapcrewing</a><br><br>Stay updated with the latest job openings and urgent vacancies!",
        template_name: str = 'template.html'
    ) -> str:
        """
        Render HTML email from template and variables.
        
        Args:
            vacancies_text: Plain text vacancies (will be wrapped)
            cta_subject: Subject/heading text
            cta_body: Call-to-action body text (HTML allowed)
            template_name: Template file name
            
        Returns:
            Rendered HTML string
        """
        template = self.load_template(template_name)
        
        # Wrap vacancies if provided
        vacancies_html = self.wrap_vacancies(vacancies_text) if vacancies_text else ""
        
        normalized_cta_body = self.normalize_cta_body(cta_body)

        return template.render(
            vacancies=vacancies_html,
            cta_subject=cta_subject,
            cta_body=normalized_cta_body
        )
    
    def render_from_dict(self, context: Dict[str, Any], template_name: str = 'template.html') -> str:
        """
        Render template from context dictionary.
        
        Args:
            context: Dictionary with template variables
            template_name: Template file name
            
        Returns:
            Rendered HTML string
        """
        template = self.load_template(template_name)
        
        # Wrap vacancies if present as plain text
        if 'vacancies' in context and isinstance(context['vacancies'], str):
            context['vacancies'] = self.wrap_vacancies(context['vacancies'])
        
        return template.render(**context)
    def _linkify_urls(self, text: str) -> str:
        """Convert plain URLs to clickable links in already-escaped text."""
        url_pattern = re.compile(r'(https?://[^\s<]+)')
        return url_pattern.sub(r'<a href="\1">\1</a>', text)
