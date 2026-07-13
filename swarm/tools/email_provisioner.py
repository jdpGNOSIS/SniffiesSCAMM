"""
Email Provisioner Tool — create business email accounts.

Supports:
  - Local catch-all SMTP (no external API, works offline)
  - Cloudflare Email Routing API (free, if configured)
  - Zoho Mail API (free tier up to 5 users, if configured)
  - Provider-agnostic alias management
  - Password generation and credential storage
"""

import asyncio
import json
import re
import secrets
import string
import logging
from pathlib import Path
from datetime import datetime, UTC

logger = logging.getLogger(__name__)

EMAIL_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "mailboxes"
CONFIG_FILE = EMAIL_DIR / "providers.json"
CRED_FILE = EMAIL_DIR / "credentials.json"

PROVIDER_TEMPLATES = {
    "local": {
        "name": "Local Catch-All SMTP",
        "type": "local",
        "setup_guide": "No setup needed. Runs on localhost:2525.",
        "requires_api_key": False,
        "requires_domain": False,
        "free_tier": True,
    },
    "cloudflare": {
        "name": "Cloudflare Email Routing",
        "type": "api",
        "setup_guide": (
            "1. Add your domain to Cloudflare\n"
            "2. Get a Cloudflare API token with Zone:Email:Write permissions\n"
            "3. Set CLOUDFLARE_API_TOKEN and CLOUDFLARE_ZONE_ID in data/mailboxes/providers.json"
        ),
        "requires_api_key": True,
        "requires_domain": True,
        "free_tier": True,
        "config_keys": ["api_token", "zone_id", "domain"],
    },
    "zoho": {
        "name": "Zoho Mail (Free Tier)",
        "type": "api",
        "setup_guide": (
            "1. Register your domain at https://mail.zoho.com\n"
            "2. Generate an app-specific password\n"
            "3. Set ZOHO_EMAIL and ZOHO_PASSWORD in data/mailboxes/providers.json"
        ),
        "requires_api_key": True,
        "requires_domain": True,
        "free_tier": True,
        "max_free_users": 5,
        "config_keys": ["email", "password", "domain"],
    },
    "improvmx": {
        "name": "ImprovMX (Free Email Forwarding)",
        "type": "api",
        "setup_guide": (
            "1. Add your domain at https://improvmx.com\n"
            "2. Get your API key from the dashboard\n"
            "3. Set IMPROVMX_API_KEY and IMPROVMX_DOMAIN in data/mailboxes/providers.json"
        ),
        "requires_api_key": True,
        "requires_domain": True,
        "free_tier": True,
        "config_keys": ["api_key", "domain"],
    },
}

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
USERNAME_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+$")


def _ensure_dirs():
    EMAIL_DIR.mkdir(parents=True, exist_ok=True)


def _load_json(path):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _save_json(path, data):
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def generate_password(length=16):
    chars = string.ascii_letters + string.digits + "!@#$%&"
    return "".join(secrets.choice(chars) for _ in range(length))


def validate_email(email: str) -> str | None:
    if not EMAIL_REGEX.match(email):
        return f"Invalid email format: {email}"
    return None


def validate_username(username: str) -> str | None:
    if not USERNAME_REGEX.match(username):
        return "Username can only contain letters, numbers, dots, hyphens, and underscores"
    if len(username) < 3:
        return "Username must be at least 3 characters"
    return None


class EmailProvisionerTool:
    def __init__(self):
        _ensure_dirs()
        self._smtp_server = None

    @property
    def name(self) -> str:
        return "email_provisioner"

    async def ensure(self):
        _ensure_dirs()

    def get_providers(self) -> dict:
        return dict(PROVIDER_TEMPLATES)

    def get_configured_providers(self) -> dict:
        config = _load_json(CONFIG_FILE)
        return config.get("providers", {})

    def save_provider_config(self, provider: str, config: dict):
        _ensure_dirs()
        data = _load_json(CONFIG_FILE)
        providers = data.get("providers", {})
        providers[provider] = config
        data["providers"] = providers
        _save_json(CONFIG_FILE, data)

    def create_mailbox_local(self, email: str, display_name: str = "", password: str = "") -> dict:
        err = validate_email(email)
        if err:
            return {"success": False, "error": err}
        username = email.split("@")[0]
        err2 = validate_username(username)
        if err2:
            return {"success": False, "error": err2}

        _ensure_dirs()
        creds = _load_json(CRED_FILE)
        if email in creds:
            return {"success": False, "error": f"Mailbox already exists: {email}"}

        password = password or generate_password()
        creds[email] = {
            "email": email,
            "username": username,
            "display_name": display_name or username,
            "password": password,
            "provider": "local",
            "created_at": datetime.now(UTC).isoformat(),
            "active": True,
        }
        _save_json(CRED_FILE, creds)

        mailbox_dir = EMAIL_DIR / username
        mailbox_dir.mkdir(parents=True, exist_ok=True)
        (mailbox_dir / "inbox").mkdir(exist_ok=True)
        (mailbox_dir / "sent").mkdir(exist_ok=True)

        return {
            "success": True,
            "email": email,
            "password": password,
            "provider": "local",
            "smtp_server": "localhost:2525",
            "imap_server": "localhost:2587",
            "message": f"Created {email} — credentials saved to {CRED_FILE}",
        }

    def list_mailboxes(self, provider: str = "") -> list[dict]:
        creds = _load_json(CRED_FILE)
        results = []
        for email, info in creds.items():
            if provider and info.get("provider") != provider:
                continue
            results.append(info)
        return results

    def delete_mailbox(self, email: str) -> dict:
        creds = _load_json(CRED_FILE)
        if email not in creds:
            return {"success": False, "error": f"Mailbox not found: {email}"}
        del creds[email]
        _save_json(CRED_FILE, creds)
        username = email.split("@")[0]
        mailbox_dir = EMAIL_DIR / username
        if mailbox_dir.exists():
            import shutil
            shutil.rmtree(mailbox_dir)
        return {"success": True, "message": f"Deleted {email}"}

    def bulk_create(self, emails: list[dict]) -> list[dict]:
        results = []
        for entry in emails:
            result = self.create_mailbox_local(
                email=entry.get("email", ""),
                display_name=entry.get("display_name", ""),
                password=entry.get("password", ""),
            )
            results.append(result)
        return results

    async def start_smtp_server(self, host="127.0.0.1", port=2525):
        if self._smtp_server:
            return {"success": True, "message": "SMTP server already running"}
        try:
            self._smtp_server = await asyncio.start_server(
                self._handle_smtp, host=host, port=port
            )
            logger.info(f"SMTP catch-all listening on {host}:{port}")
            return {"success": True, "message": f"SMTP server started on {host}:{port}"}
        except Exception as e:
            logger.warning(f"Could not start SMTP server: {e}")
            return {"success": False, "error": str(e)}

    async def stop_smtp_server(self):
        if self._smtp_server:
            self._smtp_server.close()
            await self._smtp_server.wait_closed()
            self._smtp_server = None
            logger.info("SMTP server stopped")

    async def _handle_smtp(self, reader, writer):
        try:
            writer.write(b"220 localhost SMTP Catch-All\r\n")
            await writer.drain()
            data = await asyncio.wait_for(reader.read(4096), timeout=5)
            msg = data.decode("utf-8", errors="replace")
            rcpt_to = None
            for line in msg.split("\r\n"):
                if line.upper().startswith("RCPT TO:"):
                    match = re.search(r"<([^>]+)>", line)
                    if match:
                        rcpt_to = match.group(1)
            if rcpt_to:
                username = rcpt_to.split("@")[0]
                inbox_dir = EMAIL_DIR / username / "inbox"
                inbox_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                (inbox_dir / f"{ts}.eml").write_text(msg, encoding="utf-8")
                logger.info(f"Caught email for {rcpt_to}")
            writer.write(b"250 OK\r\n")
            await writer.drain()
        except Exception:
            pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def send_email_smtp(self, from_addr: str, to_addr: str, subject: str, body: str) -> dict:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", 2525), timeout=5
            )
            await reader.read(1024)
            writer.write(f"EHLO localhost\r\n".encode())
            await writer.drain()
            await reader.read(1024)
            writer.write(f"MAIL FROM:<{from_addr}>\r\n".encode())
            await writer.drain()
            await reader.read(1024)
            writer.write(f"RCPT TO:<{to_addr}>\r\n".encode())
            await writer.drain()
            await reader.read(1024)
            writer.write(b"DATA\r\n")
            await writer.drain()
            await reader.read(1024)
            content = f"From: {from_addr}\r\nTo: {to_addr}\r\nSubject: {subject}\r\n\r\n{body}\r\n.\r\n"
            writer.write(content.encode())
            await writer.drain()
            await reader.read(1024)
            writer.write(b"QUIT\r\n")
            await writer.drain()
            writer.close()
            return {"success": True, "message": f"Email sent to {to_addr}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def provision_via_cloudflare(self, email: str, api_token: str, zone_id: str, domain: str) -> dict:
        err = validate_email(email)
        if err:
            return {"success": False, "error": err}
        local_part = email.split("@")[0]
        try:
            from swarm.tools.http_client import HttpClientTool
            http = HttpClientTool()
            await http.ensure()
            resp = await http.post(
                f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/addresses",
                headers={
                    "Authorization": f"Bearer {api_token}",
                    "Content-Type": "application/json",
                },
                json={"email": email, "enabled": True},
            )
            if resp.get("status") in (200, 201) and resp.get("json", {}).get("success"):
                creds = _load_json(CRED_FILE)
                creds[email] = {
                    "email": email,
                    "username": local_part,
                    "provider": "cloudflare",
                    "domain": domain,
                    "created_at": datetime.now(UTC).isoformat(),
                    "active": True,
                }
                _save_json(CRED_FILE, creds)
                return {"success": True, "email": email, "provider": "cloudflare"}
            return {"success": False, "error": f"Cloudflare API error: {resp}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
