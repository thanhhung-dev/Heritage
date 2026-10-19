"""Email service for sending password reset emails via SMTP."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

log = logging.getLogger(__name__)


class EmailConfig:
    """SMTP configuration for sending emails."""
    
    def __init__(
        self,
        smtp_host: str,
        smtp_port: int,
        smtp_user: str,
        smtp_password: str,
        sender_email: str,
        sender_name: str = "Heritage Support",
        use_tls: bool = True,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password
        self.sender_email = sender_email
        self.sender_name = sender_name
        self.use_tls = use_tls


class EmailService:
    """Service for sending emails via SMTP."""
    
    def __init__(self, config: Optional[EmailConfig] = None):
        self.config = config
        self.enabled = config is not None
    
    def send_password_reset_email(
        self,
        to_email: str,
        reset_link: str,
        username: Optional[str] = None,
    ) -> bool:
        """Send password reset email to user.
        
        Args:
            to_email: Recipient email address
            reset_link: Password reset link with token
            username: Optional username for personalization
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.enabled:
            log.warning("Email service not configured. Reset link: %s", reset_link)
            return False
        
        subject = "Khôi phục mật khẩu - Heritage"
        html_body = self._get_html_template(reset_link, username)
        text_body = self._get_text_template(reset_link, username)
        
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.config.sender_name} <{self.config.sender_email}>"
            msg["To"] = to_email
            
            part1 = MIMEText(text_body, "plain", "utf-8")
            part2 = MIMEText(html_body, "html", "utf-8")
            msg.attach(part1)
            msg.attach(part2)
            
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                if self.config.use_tls:
                    server.starttls()
                server.login(self.config.smtp_user, self.config.smtp_password)
                server.send_message(msg)
            
            log.info(f"Password reset email sent to: {to_email}")
            return True
            
        except Exception as e:
            log.error(f"Failed to send email to {to_email}: {e}")
            return False
    
    def _get_html_template(self, reset_link: str, username: Optional[str]) -> str:
        """Get HTML email template."""
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #1E293B; background: #F8FAFC; margin: 0; padding: 0; }}
        .container {{ max-width: 600px; margin: 40px auto; background: #FFF; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%); padding: 32px 24px; text-align: center; }}
        .header h1 {{ color: #F8FAFC; font-size: 24px; font-weight: 600; margin: 0; }}
        .content {{ padding: 32px 24px; }}
        .greeting {{ font-size: 16px; color: #334155; margin-bottom: 16px; }}
        .message {{ font-size: 15px; color: #475569; margin-bottom: 24px; }}
        .button-container {{ text-align: center; margin: 32px 0; }}
        .button {{ display: inline-block; padding: 14px 32px; background: #38BDF8; color: #FFF !important; text-decoration: none; border-radius: 8px; font-weight: 600; font-size: 15px; }}
        .link-fallback {{ margin-top: 24px; padding: 16px; background: #F1F5F9; border-radius: 8px; font-size: 13px; color: #64748B; word-break: break-all; }}
        .link-fallback a {{ color: #0EA5E9; text-decoration: none; }}
        .security-notice {{ margin-top: 24px; padding: 16px; background: #FEF3C7; border-left: 4px solid #F59E0B; border-radius: 4px; font-size: 13px; color: #92400E; }}
        .footer {{ padding: 24px; background: #F8FAFC; border-top: 1px solid #E2E8F0; text-align: center; font-size: 13px; color: #94A3B8; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header"><h1>🏛️ Heritage</h1></div>
        <div class="content">
            <p class="greeting">Xin chào{f" {username}" if username else ""},</p>
            <p class="message">Chúng tôi nhận được yêu cầu khôi phục mật khẩu cho tài khoản của bạn. Nhấn vào nút bên dưới để đặt lại mật khẩu:</p>
            <div class="button-container"><a href="{reset_link}" class="button">Đặt lại mật khẩu</a></div>
            <div class="link-fallback"><strong>Link không hoạt động?</strong><br>Sao chép và dán URL sau vào trình duyệt:<br><a href="{reset_link}">{reset_link}</a></div>
            <div class="security-notice"><strong>⚠️ Lưu ý bảo mật:</strong><br>• Link này chỉ có hiệu lực trong <strong>30 phút</strong><br>• Nếu bạn không yêu cầu đặt lại mật khẩu, hãy bỏ qua email này<br>• Không chia sẻ link này với bất kỳ ai</div>
        </div>
        <div class="footer"><p>© 2024 Heritage - Hệ thống quản lý di sản văn hóa Đà Nẵng - Huế</p><p>Email này được gửi tự động, vui lòng không trả lời.</p></div>
    </div>
</body>
</html>"""
    
    def _get_text_template(self, reset_link: str, username: Optional[str]) -> str:
        """Get plain text email template."""
        return f"""Xin chào{f" {username}" if username else ""},

Chúng tôi nhận được yêu cầu khôi phục mật khẩu cho tài khoản của bạn.

Nhấn vào link sau để đặt lại mật khẩu:
{reset_link}

LƯU Ý BẢO MẬT:
- Link này chỉ có hiệu lực trong 30 phút
- Nếu bạn không yêu cầu đặt lại mật khẩu, hãy bỏ qua email này
- Không chia sẻ link này với bất kỳ ai

---
© 2024 Heritage - Hệ thống quản lý di sản văn hóa Đà Nẵng - Huế
Email này được gửi tự động, vui lòng không trả lời."""
    
    def test_connection(self) -> bool:
        """Test SMTP connection."""
        if not self.enabled:
            log.warning("Email service not configured")
            return False
        
        try:
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port, timeout=10) as server:
                if self.config.use_tls:
                    server.starttls()
                server.login(self.config.smtp_user, self.config.smtp_password)
            log.info("SMTP connection test successful")
            return True
        except Exception as e:
            log.error(f"SMTP connection test failed: {e}")
            return False


# Global email service instance
_email_service: Optional[EmailService] = None


def init_email_service(config: Optional[EmailConfig]) -> EmailService:
    """Initialize global email service with config."""
    global _email_service
    _email_service = EmailService(config)
    return _email_service


def get_email_service() -> EmailService:
    """Get global email service instance."""
    if _email_service is None:
        raise RuntimeError("Email service not initialized. Call init_email_service() first.")
    return _email_service


def send_reset_password_email(to_email: str, reset_link: str, username: Optional[str] = None) -> bool:
    """Convenience wrapper to send a password-reset email to any registered account.

    Always sends to the exact `to_email` address passed in (typically
    `account.email` from the database), so the reset link reaches
    whichever email the user registered with.

    Uses the globally configured SMTP connection when available (from
    `.env`). If SMTP is not configured or the send fails, the reset link
    is logged to the console instead so local/dev flows are not blocked.

    Args:
        to_email: Recipient email address (e.g. account.email).
        reset_link: Password reset link containing the reset token.
        username: Optional username for email personalization.

    Returns:
        True if the email was actually sent via SMTP, False if it fell
        back to console logging (SMTP disabled or send failed).
    """
    service = get_email_service()
    if not service.enabled:
        log.warning("SMTP not configured. Reset link for %s: %s", to_email, reset_link)
        return False
    return service.send_password_reset_email(
        to_email=to_email,
        reset_link=reset_link,
        username=username,
    )
