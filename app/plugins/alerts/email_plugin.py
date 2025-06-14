# ABOUTME: Email alert plugin for sending notifications via SMTP
# ABOUTME: Supports multiple email providers and HTML/text formatting

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.plugins.base import AlertPlugin, PluginConfigError


class EmailAlertPlugin(AlertPlugin):
    """Plugin for sending email alerts via SMTP."""

    @property
    def version(self) -> str:
        return "1.0.0"

    @property
    def description(self) -> str:
        return "Sends alert notifications via email using SMTP servers"

    def validate_config(self) -> None:
        """Validate email plugin configuration."""
        required_fields = [
            "smtp_server",
            "smtp_port",
            "username",
            "password",
            "from_email",
            "to_emails",
        ]

        for field in required_fields:
            if field not in self.config:
                raise PluginConfigError(f"Missing required field: {field}")

        # Validate email addresses
        to_emails = self.config.get("to_emails", [])
        if not isinstance(to_emails, list) or not to_emails:
            raise PluginConfigError("to_emails must be a non-empty list")

        # Validate SMTP port
        smtp_port = self.config.get("smtp_port")
        if not isinstance(smtp_port, int) or smtp_port <= 0:
            raise PluginConfigError("smtp_port must be a positive integer")

    def initialize(self) -> None:
        """Initialize the email alert plugin."""
        self.smtp_server = self.config["smtp_server"]
        self.smtp_port = self.config["smtp_port"]
        self.username = self.config["username"]
        self.password = self.config["password"]
        self.from_email = self.config["from_email"]
        self.to_emails = self.config["to_emails"]

        # Optional configuration
        self.use_tls = self.config.get("use_tls", True)
        self.use_ssl = self.config.get("use_ssl", False)
        self.timeout = self.config.get("timeout", 30)
        self.subject_prefix = self.config.get("subject_prefix", "[Glimpser Alert]")

        self.logger.info(
            f"Email plugin initialized (server: {self.smtp_server}:{self.smtp_port})"
        )

    def cleanup(self) -> None:
        """Clean up email plugin resources."""
        self.logger.info("Email alert plugin cleaned up")

    def send_alert(self, message: str, **kwargs) -> bool:
        """Send an email alert.

        Args:
            message: The alert message to send
            **kwargs: Additional email parameters
                - subject: Custom email subject
                - html: Whether message is HTML (default: False)
                - attachments: List of file paths to attach
                - priority: Email priority (high, normal, low)

        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.is_enabled():
            return False

        try:
            # Build email
            msg = self._build_email_message(message, **kwargs)

            # Send email
            return self._send_email(msg)

        except Exception as e:
            self.logger.error(f"Error sending email alert: {e}")
            return False

    def test_connection(self) -> bool:
        """Test the SMTP connection.

        Returns:
            True if connection is working, False otherwise
        """
        try:
            server = self._create_smtp_connection()
            server.quit()
            self.logger.info("SMTP connection test successful")
            return True

        except Exception as e:
            self.logger.error(f"SMTP connection test failed: {e}")
            return False

    def _build_email_message(self, message: str, **kwargs) -> MIMEMultipart:
        """Build the email message."""
        # Create message
        msg = MIMEMultipart("alternative")

        # Set headers
        subject = kwargs.get("subject", "Alert Notification")
        msg["Subject"] = f"{self.subject_prefix} {subject}"
        msg["From"] = self.from_email
        msg["To"] = ", ".join(self.to_emails)

        # Set priority if specified
        priority = kwargs.get("priority", "normal").lower()
        if priority == "high":
            msg["X-Priority"] = "1"
            msg["X-MSMail-Priority"] = "High"
        elif priority == "low":
            msg["X-Priority"] = "5"
            msg["X-MSMail-Priority"] = "Low"

        # Add message body
        is_html = kwargs.get("html", False)
        if is_html:
            html_part = MIMEText(message, "html")
            msg.attach(html_part)
        else:
            text_part = MIMEText(message, "plain")
            msg.attach(text_part)

        # Add attachments if provided
        attachments = kwargs.get("attachments", [])
        for attachment_path in attachments:
            self._add_attachment(msg, attachment_path)

        return msg

    def _add_attachment(self, msg: MIMEMultipart, file_path: str) -> None:
        """Add file attachment to email message."""
        try:
            import os
            from email import encoders
            from email.mime.base import MIMEBase

            if not os.path.exists(file_path):
                self.logger.warning(f"Attachment file not found: {file_path}")
                return

            with open(file_path, "rb") as attachment:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(attachment.read())

            encoders.encode_base64(part)

            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {os.path.basename(file_path)}",
            )

            msg.attach(part)

        except Exception as e:
            self.logger.error(f"Error adding attachment {file_path}: {e}")

    def _create_smtp_connection(self) -> smtplib.SMTP:
        """Create and authenticate SMTP connection."""
        if self.use_ssl:
            server = smtplib.SMTP_SSL(
                self.smtp_server, self.smtp_port, timeout=self.timeout
            )
        else:
            server = smtplib.SMTP(
                self.smtp_server, self.smtp_port, timeout=self.timeout
            )

            if self.use_tls:
                server.starttls()

        server.login(self.username, self.password)
        return server

    def _send_email(self, msg: MIMEMultipart) -> bool:
        """Send the email message."""
        try:
            server = self._create_smtp_connection()

            # Send email
            server.send_message(msg, self.from_email, self.to_emails)
            server.quit()

            self.logger.info(f"Email alert sent to {len(self.to_emails)} recipients")
            return True

        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False
