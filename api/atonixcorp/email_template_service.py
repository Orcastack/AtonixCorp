"""Repository-backed transactional email rendering and delivery."""

from __future__ import annotations

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags


def render_email_template(template_name, context):
    """Return HTML and accessible plain-text bodies for a named email template."""
    template_context = {
        'brand_name': getattr(settings, 'EMAIL_BRAND_NAME', 'AtonixCorp'),
        'support_email': getattr(settings, 'EMAIL_SUPPORT_EMAIL', 'support@atonixcorp.com'),
        'support_url': getattr(settings, 'EMAIL_SUPPORT_URL', ''),
        **context,
    }
    html_body = render_to_string(f'email/{template_name}.html', template_context)
    text_body = render_to_string(f'email/{template_name}.txt', template_context)
    return html_body, text_body or strip_tags(html_body)


def send_templated_email(*, template_name, subject, recipient, context, from_email=None):
    """Render and send a branded multipart email with a plain-text fallback."""
    html_body, text_body = render_email_template(template_name, context)
    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        to=[recipient],
    )
    message.attach_alternative(html_body, 'text/html')
    return message.send(fail_silently=False)