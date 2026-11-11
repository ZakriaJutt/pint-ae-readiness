"""Outgoing e-mail behind one interface (B2). SMTP only: locally the Mailpit inbox at
127.0.0.1:1025 without authentication; a production provider later through the same SMTP
interface, selected by settings. E-mail carries invitations and reset links only; it is never
an authentication factor (TRD 8.1, ASVS 6.3.6). Bodies are never logged.
"""

from __future__ import annotations

import logging
import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

from pintae_core.config import Settings, get_settings
from pintae_core.logging import log_event

log = logging.getLogger("pintae.mail")


@dataclass(frozen=True)
class Message:
    to: str
    subject: str
    body: str
    kind: str  # invite, password_reset, notice: logged instead of the content


class Mailer(Protocol):
    def send(self, msg: Message) -> None: ...


class SmtpMailer:
    def __init__(self, cfg: Settings) -> None:
        self.cfg = cfg

    def send(self, msg: Message) -> None:
        em = EmailMessage()
        em["From"] = self.cfg.mail_from
        em["To"] = msg.to
        em["Subject"] = msg.subject
        em.set_content(msg.body)
        with smtplib.SMTP(self.cfg.smtp_host, self.cfg.smtp_port, timeout=10) as smtp:
            if self.cfg.smtp_starttls:
                smtp.starttls(context=ssl.create_default_context())
            if self.cfg.smtp_username and self.cfg.smtp_password:
                smtp.login(self.cfg.smtp_username, self.cfg.smtp_password)
            smtp.send_message(em)
        log_event(log, "mail.sent", reason_code=msg.kind)


def default_mailer() -> Mailer:
    return SmtpMailer(get_settings())


def invite_message(to: str, firm_name: str, role: str, link: str, hours: int) -> Message:
    return Message(
        to=to,
        subject="Your invitation to PINT AE Readiness Desk",
        body=(
            f"You have been invited to {firm_name} on PINT AE Readiness Desk as {role}.\n\n"
            f"Open this link to choose a password and set up your authenticator app:\n{link}\n\n"
            f"The link works once and expires in {hours} hours. If you did not expect this "
            "invitation, ignore this message.\n"
        ),
        kind="invite",
    )


def reset_message(to: str, link: str, minutes: int) -> Message:
    return Message(
        to=to,
        subject="Reset your PINT AE Readiness Desk password",
        body=(
            "A password reset was requested for this address.\n\n"
            f"Open this link to choose a new password:\n{link}\n\n"
            f"The link works once and expires in {minutes} minutes. You will still need your "
            "authenticator code or a recovery code. If you did not ask for this, ignore it.\n"
        ),
        kind="password_reset",
    )
