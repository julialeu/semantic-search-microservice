import os
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

# --- Carga de Configuración SMTP ---
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")


class EmailService:
    """
    Servicio para el envío de emails transaccionales.
    """

    @staticmethod
    async def send_email(to_email: str, subject: str, html_content: str):
        """
        Método base para conectarse al servidor SMTP y enviar un email.
        """
        if not all([SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL]):
            print(
                "ADVERTENCIA: Faltan variables de entorno SMTP. El email no se enviará."
            )
            return

        message = MIMEMultipart("alternative")
        message["Subject"] = subject
        message["From"] = FROM_EMAIL
        message["To"] = to_email
        message.attach(MIMEText(html_content, "html"))

        try:
            await aiosmtplib.send(
                message,
                hostname=SMTP_HOST,
                port=SMTP_PORT,
                username=SMTP_USER,
                password=SMTP_PASSWORD,
                start_tls=True,
            )
        except Exception as e:
            print(f"Error al enviar email: {e}")
            raise

    @staticmethod
    async def send_verification_email(to_email: str, name: str, token: str):
        """
        Envía el email específico para la verificación de cuenta.
        """
        verification_url = f"{FRONTEND_URL}/verify-email?token={token}"
        subject = "¡Verifica tu cuenta!"
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Arial', sans-serif; line-height: 1.6; }}
                .container {{ width: 90%; margin: auto; padding: 20px; }}
                .button {{ background-color: #4285F4; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>¡Hola, {name}!</h2>
                <p>Gracias por registrarte. Por favor, haz clic en el botón de abajo para verificar tu dirección de email:</p>
                <p>
                    <a href="{verification_url}" class="button">Verificar Email</a>
                </p>
                <p>Si no puedes hacer clic, copia y pega este enlace en tu navegador:</p>
                <p>{verification_url}</p>
                <p>Si no te has registrado, por favor ignora este email.</p>
            </div>
        </body>
        </html>
        """
        await EmailService.send_email(to_email, subject, html_content)

    @staticmethod
    async def send_password_reset_email(to_email: str, name: str, token: str):
        """
        Envía el email específico para el reseteo de contraseña.
        """
        reset_url = f"{FRONTEND_URL}/reset-password?token={token}"
        subject = "Restablecimiento de Contraseña"
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Arial', sans-serif; line-height: 1.6; }}
                .container {{ width: 90%; margin: auto; padding: 20px; }}
                .button {{ background-color: #EA4335; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h2>¡Hola, {name}!</h2>
                <p>Hemos recibido una solicitud para restablecer tu contraseña. Haz clic en el botón de abajo para continuar:</p>
                <p>
                    <a href="{reset_url}" class="button">Restablecer Contraseña</a>
                </p>
                <p>Si no puedes hacer clic, copia y pega este enlace en tu navegador:</p>
                <p>{reset_url}</p>
                <p>Si no has solicitado esto, por favor ignora este email.</p>
            </div>
        </body>
        </html>
        """
        await EmailService.send_email(to_email, subject, html_content)
