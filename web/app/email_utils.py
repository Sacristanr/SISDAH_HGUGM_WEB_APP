import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from .models import ConfigApp, Equipo
from datetime import datetime


def enviar_resumen(destinatario: str, asunto: str, notas: str = "") -> tuple[bool, str]:
    smtp_host = ConfigApp.get("smtp_host", "")
    smtp_port = int(ConfigApp.get("smtp_port", "587"))
    smtp_user = ConfigApp.get("smtp_user", "")
    smtp_pass = ConfigApp.get("smtp_pass", "")

    if not smtp_host or not smtp_user:
        return False, "Configura el servidor SMTP en Administración → Configuración"

    # Estadísticas
    total     = Equipo.query.count()
    en_stock  = Equipo.query.filter_by(estado="en stock").count()
    retirados = Equipo.query.filter_by(estado="retirado").count()
    averias   = Equipo.query.filter_by(estado="averia").count()
    reservados= Equipo.query.filter_by(estado="reservado").count()

    cuerpo_html = f"""
    <html><body style="font-family:Segoe UI,sans-serif;color:#333;max-width:600px;margin:auto">
    <div style="background:#C8102E;padding:20px;border-radius:8px 8px 0 0">
      <h2 style="color:white;margin:0">SISDAH — Resumen de inventario</h2>
      <p style="color:rgba(255,255,255,.8);margin:4px 0 0">
        Hospital G.U. Gregorio Marañón · Departamento de Informática
      </p>
    </div>
    <div style="background:#f9f9f9;padding:20px;border-radius:0 0 8px 8px;border:1px solid #ddd">
      <p style="color:#666">Generado el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}</p>
      <table style="width:100%;border-collapse:collapse;margin:16px 0">
        <tr style="background:#C8102E;color:white">
          <th style="padding:8px;text-align:left">Estado</th>
          <th style="padding:8px;text-align:center">Equipos</th>
        </tr>
        <tr style="background:#fff"><td style="padding:8px">Total registrados</td>
            <td style="padding:8px;text-align:center;font-weight:bold">{total}</td></tr>
        <tr style="background:#E8F5E9"><td style="padding:8px">En stock</td>
            <td style="padding:8px;text-align:center;color:#1B5E20;font-weight:bold">{en_stock}</td></tr>
        <tr style="background:#fff"><td style="padding:8px">Retirados</td>
            <td style="padding:8px;text-align:center">{retirados}</td></tr>
        <tr style="background:#FFF8E1"><td style="padding:8px">En avería</td>
            <td style="padding:8px;text-align:center;color:#795548">{averias}</td></tr>
        <tr style="background:#fff"><td style="padding:8px">Reservados</td>
            <td style="padding:8px;text-align:center">{reservados}</td></tr>
      </table>
      {f'<p style="background:#f0f0f0;padding:12px;border-radius:4px"><strong>Notas:</strong> {notas}</p>' if notas else ''}
      <hr style="border:none;border-top:1px solid #ddd;margin:16px 0">
      <p style="color:#999;font-size:12px">
        Este correo ha sido generado automáticamente por SISDAH v3.0<br>
        Hospital General Universitario Gregorio Marañón
      </p>
    </div>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"]    = smtp_user
    msg["To"]      = destinatario
    msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as servidor:
            servidor.ehlo()
            servidor.starttls()
            if smtp_pass:
                servidor.login(smtp_user, smtp_pass)
            servidor.sendmail(smtp_user, destinatario, msg.as_string())
        return True, "Correo enviado correctamente"
    except Exception as e:
        return False, f"Error SMTP: {str(e)}"
