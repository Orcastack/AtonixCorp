from __future__ import annotations

from io import BytesIO

from django.core.files.base import ContentFile

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas


def _draw_header(pdf, title: str, subtitle: str):
    width, height = A4
    pdf.setFillColor(colors.HexColor('#102542'))
    pdf.rect(0, height - 45 * mm, width, 45 * mm, fill=1, stroke=0)
    pdf.setFillColor(colors.white)
    pdf.setFont('Helvetica-Bold', 22)
    pdf.drawString(18 * mm, height - 20 * mm, title)
    pdf.setFont('Helvetica', 10)
    pdf.drawString(18 * mm, height - 28 * mm, subtitle)
    return height - 55 * mm


def _draw_lines(pdf, lines, start_y):
    width, _ = A4
    y = start_y
    for label, value in lines:
        if y < 25 * mm:
            pdf.showPage()
            y = _draw_header(pdf, 'Ledgora Equity Management', 'Continued')
        pdf.setFillColor(colors.HexColor('#5B6C8B'))
        pdf.setFont('Helvetica-Bold', 9)
        pdf.drawString(18 * mm, y, label.upper())
        y -= 5 * mm
        pdf.setFillColor(colors.black)
        pdf.setFont('Helvetica', 11)
        text = pdf.beginText(18 * mm, y)
        text.setLeading(14)
        for part in str(value or '—').splitlines() or ['—']:
            text.textLine(part)
            y -= 5 * mm
        pdf.drawText(text)
        pdf.setStrokeColor(colors.HexColor('#D7DCE5'))
        pdf.line(18 * mm, y + 2 * mm, width - 18 * mm, y + 2 * mm)
        y -= 7 * mm
    return y


def build_grant_package_pdf(grant) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    y = _draw_header(pdf, f'Grant Package {grant.grant_number}', f'{grant.workspace.name} · {grant.shareholder.name}')
    lines = [
        ('Grant holder', grant.shareholder.name),
        ('Grant type', grant.get_grant_type_display()),
        ('Share class', grant.share_class.name),
        ('Total units', grant.total_units),
        ('Exercise price', grant.exercise_price),
        ('Grant date', grant.grant_date),
        ('Vesting start', grant.vesting_start_date),
        ('Cliff', f'{grant.cliff_months} months'),
        ('Term', f'{grant.vesting_months} months · {grant.get_vesting_interval_display()}'),
        ('Acceleration', grant.get_acceleration_type_display()),
        ('Termination treatment', grant.get_termination_treatment_display()),
        ('Notes', grant.notes or 'No additional notes recorded.'),
    ]
    _draw_lines(pdf, lines, y)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def build_certificate_pdf(certificate) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    y = _draw_header(pdf, f'Share Certificate {certificate.certificate_number}', f'{certificate.workspace.name} · {certificate.issued_to.name}')
    lines = [
        ('Certificate number', certificate.certificate_number),
        ('Issued to', certificate.issued_to.name),
        ('Grant number', certificate.grant.grant_number),
        ('Share class', certificate.share_class.name),
        ('Issued units', certificate.issued_units),
        ('Issue date', certificate.issue_date),
        ('Status', certificate.get_status_display()),
        ('Prepared by', getattr(certificate.issued_by, 'get_full_name', lambda: '')() or getattr(certificate.issued_by, 'username', 'System')),
        ('Certificate payload', '\n'.join(f'{key}: {value}' for key, value in (certificate.certificate_payload or {}).items()) or 'No supplemental payload.'),
    ]
    _draw_lines(pdf, lines, y)
    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def build_scenario_report_pdf(title: str, subtitle: str, analysis: dict) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    y = _draw_header(pdf, title, subtitle)

    financing = analysis.get('financing', {})
    baseline = analysis.get('baseline', {})
    summary_lines = [
        ('Pre-money valuation', financing.get('pre_money_valuation', '0.00')),
        ('Post-money valuation', financing.get('post_money_valuation', '0.00')),
        ('Price per share', financing.get('price_per_share', '0.0000')),
        ('New money shares', financing.get('new_money_shares', 0)),
        ('Pro-rata shares', financing.get('pro_rata_shares', 0)),
        ('Option pool top-up', financing.get('option_pool_top_up', 0)),
        ('Fully diluted base', baseline.get('fully_diluted_shares', 0)),
    ]
    y = _draw_lines(pdf, summary_lines, y)

    top_holders = analysis.get('post_cap_table', [])[:10]
    holder_lines = [
        ('Post-round holders', '\n'.join(
            f"{item.get('holder_name', 'Holder')} · {item.get('share_class_name', 'Class')} · {item.get('shares', 0)} shares · {item.get('ownership_percent', '0')}%"
            for item in top_holders
        ) or 'No holder rows available.')
    ]
    y = _draw_lines(pdf, holder_lines, y)

    waterfall_lines = []
    for waterfall in analysis.get('waterfalls', [])[:3]:
        distributions = '\n'.join(
            f"{row.get('share_class_name', 'Class')}: pref {row.get('preference_paid', '0.00')} / residual {row.get('residual_paid', '0.00')} / total {row.get('total_paid', '0.00')}"
            for row in waterfall.get('class_distributions', [])
        ) or 'No waterfall rows available.'
        waterfall_lines.append((f"Exit {waterfall.get('exit_value', '0.00')}", distributions))
    if waterfall_lines:
        _draw_lines(pdf, waterfall_lines, y)

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def ensure_grant_package_pdf(grant, force: bool = False):
    if grant.grant_package_file and not force:
        return grant
    grant.grant_package_file.save(
        f'grant-package-{grant.grant_number}.pdf',
        ContentFile(build_grant_package_pdf(grant)),
        save=False,
    )
    grant.save(update_fields=['grant_package_file', 'updated_at'])
    return grant


def ensure_certificate_pdf(certificate, force: bool = False):
    if certificate.pdf_file and not force:
        return certificate
    certificate.pdf_file.save(
        f'certificate-{certificate.certificate_number}.pdf',
        ContentFile(build_certificate_pdf(certificate)),
        save=False,
    )
    certificate.save(update_fields=['pdf_file', 'updated_at'])
    return certificate