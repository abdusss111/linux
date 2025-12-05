import os
import logging
from typing import Optional, Dict, Any
from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from jinja2 import Template
from pydantic import EmailStr

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        """Initialize email service with configuration from environment variables"""
        self.config = ConnectionConfig(
            MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
            MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
            MAIL_FROM=os.getenv("MAIL_FROM", "noreply@dapmeet.com"),
            MAIL_PORT=int(os.getenv("MAIL_PORT", "587")),
            MAIL_SERVER=os.getenv("MAIL_SERVER", "smtp.gmail.com"),
            MAIL_FROM_NAME=os.getenv("MAIL_FROM_NAME", "DapMeet"),
            MAIL_STARTTLS=os.getenv("MAIL_STARTTLS", "true").lower() == "true",
            MAIL_SSL_TLS=os.getenv("MAIL_SSL_TLS", "false").lower() == "true",
            USE_CREDENTIALS=os.getenv("USE_CREDENTIALS", "true").lower() == "true",
            VALIDATE_CERTS=os.getenv("VALIDATE_CERTS", "true").lower() == "true",
        )
        self.fastmail = FastMail(self.config)
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        template: Optional[str] = None,
        template_vars: Optional[Dict[str, Any]] = None,
        html_content: Optional[str] = None,
        text_content: Optional[str] = None
    ) -> bool:
        """
        Send email to a user with template support
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            template: Jinja2 template string (optional)
            template_vars: Variables to pass to template (optional)
            html_content: Direct HTML content (optional)
            text_content: Direct text content (optional)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # If template is provided, render it with variables
            if template:
                jinja_template = Template(template)
                rendered_content = jinja_template.render(template_vars or {})
                html_content = rendered_content
            
            # Create message
            message = MessageSchema(
                subject=subject,
                recipients=[to_email],
                body=text_content or html_content,
                subtype="html" if html_content else "plain"
            )
            
            # Send email
            await self.fastmail.send_message(message)
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    async def send_welcome_email(self, user_email: str, user_name: str = "") -> bool:
        """
        Send welcome email to new user
        
        Args:
            user_email: User's email address
            user_name: User's name (optional)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        welcome_template = """
        <!DOCTYPE html>
        <html lang="ru">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Добро пожаловать в dapmeet!</title>
            <style>
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    background-color: #f8f9fa;
                    padding: 20px;
                }
                .container {
                    background-color: white;
                    border-radius: 12px;
                    padding: 40px 30px;
                    box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                }
                .logo {
                    text-align: center;
                    margin-bottom: 30px;
                }
                .logo h1 {
                    color: #03224f;
                    font-size: 28px;
                    margin: 0;
                    font-weight: 700;
                    letter-spacing: -1px;
                }
                .greeting {
                    font-size: 18px;
                    margin-bottom: 25px;
                    color: #1f2937;
                }
                .content {
                    margin-bottom: 30px;
                    font-size: 16px;
                    line-height: 1.7;
                }
                .highlight {
                    background-color: #fef3c7;
                    padding: 15px;
                    border-left: 4px solid #f59e0b;
                    border-radius: 6px;
                    margin: 20px 0;
                }
                .button-container {
                    text-align: center;
                    margin: 35px 0;
                }
                .install-button {
                    display: inline-block;
                    background-color: #03224f;
                    color: white !important;
                    padding: 16px 32px;
                    text-decoration: none;
                    border-radius: 8px;
                    font-weight: 600;
                    font-size: 16px;
                    transition: all 0.3s ease;
                    box-shadow: 0 4px 12px rgba(3, 34, 79, 0.3);
                }
                .install-button:hover {
                    background-color: #041d42;
                    transform: translateY(-2px);
                    box-shadow: 0 6px 16px rgba(3, 34, 79, 0.4);
                }
                .install-button .icon {
                    color: white;
                    margin-right: 8px;
                }
                .requirements {
                    background-color: #e7f3ff;
                    border: 1px solid #bfdbfe;
                    border-radius: 8px;
                    padding: 15px;
                    margin: 20px 0;
                    font-size: 14px;
                }
                .requirements strong {
                    color: #03224f;
                }
                .footer {
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid #e5e7eb;
                    text-align: center;
                    font-size: 14px;
                    color: #6b7280;
                }
                .feature-list {
                    background-color: #f0f9ff;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                }
                .feature-list ul {
                    margin: 0;
                    padding-left: 20px;
                }
                .feature-list li {
                    margin-bottom: 12px;
                    color: #03224f;
                    line-height: 1.5;
                }
                .icon {
                    color: #03224f;
                    font-weight: bold;
                    margin-right: 8px;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">
                    <h1>dapmeet</h1>
                </div>
                
                <div class="greeting">
                    Добро пожаловать, <strong>{{ user_name or "друг" }}</strong>!
                </div>
                
                <div class="content">
                    <p>Спасибо за регистрацию в <strong>dapmeet</strong> — вашем надежном помощнике транскрибации встреч и последующим анализом с помощью AI!</p>
                    
                    <p>Чтобы начать пользоваться всеми возможностями сервиса, вам необходимо установить наше расширение для браузера Google Chrome.</p>
                </div>

                <div class="requirements">
                    <strong><span class="icon">⚠</span> Важные требования для установки:</strong><br>
                    • Установка должна производиться <strong>с компьютера</strong><br>
                    • Обязательно используйте браузер <strong>Google Chrome</strong>
                </div>

                <div class="button-container">
                    <a href="https://chromewebstore.google.com/detail/dapmeet/lldjmemepbogdgfdeeodbipoggpbkcgg?utm_source=ext_app_menu" class="install-button" target="_blank">
                        <span class="icon">⊞</span> Установить расширение dapmeet
                    </a>
                </div>

                <div class="feature-list">
                    <strong>После установки расширения:</strong>
                    <ul>
                        <li><strong><span class="icon">⚬</span> Поддержка Google Meet:</strong> работает с самой популярной платформой видеоконференций</li>
                        <li><strong><span class="icon">✎</span> Автоматическая запись:</strong> транскрипты всех встреч без дополнительных действий</li>
                        <li><strong><span class="icon">◉</span> AI-анализ встреч:</strong> получайте краткое или подробное резюме, задавайте любые вопросы по встрече и получайте мгновенные ответы с результатами, готовыми сразу после встречи</li>
                    </ul>
                </div>

                <div class="highlight">
                    <strong><span class="icon">●</span> Это займет всего 2 минуты!</strong><br>
                    После установки расширение автоматически начнет работать, и вы сможете получать транскрипты всех ваших встреч без дополнительных настроек.
                </div>

                <div class="footer">
                    <p>С уважением,<br><strong>Команда dapmeet</strong></p>
                    <p style="font-size: 12px; margin-top: 15px;">
                        Если у вас возникли вопросы, мы всегда готовы помочь!
                    </p>
                </div>
            </div>
        </body>
        </html>
        """
        
        template_vars = {
            "user_name": (user_name or "").strip(),
            "user_email": user_email
        }
        
        return await self.send_email(
            to_email=user_email,
            subject="Добро пожаловать в dapmeet!",
            template=welcome_template,
            template_vars=template_vars
        )
    
    async def send_custom_email(
        self, 
        to_email: str, 
        subject: str, 
        template: str, 
        template_vars: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Send custom email with template
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            template: Jinja2 template string
            template_vars: Variables to pass to template
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            template=template,
            template_vars=template_vars
        )
    
    async def send_simple_email(
        self, 
        to_email: str, 
        subject: str, 
        content: str, 
        is_html: bool = True
    ) -> bool:
        """
        Send simple email without template
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            content: Email content
            is_html: Whether content is HTML (default: True)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        return await self.send_email(
            to_email=to_email,
            subject=subject,
            html_content=content if is_html else None,
            text_content=content if not is_html else None
        )


# Global email service instance
email_service = EmailService()
