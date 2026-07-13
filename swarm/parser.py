"""
bots <number> <task description>
"""

import re
from .schemas import SwarmCommand, TaskType

COMMAND_RE = re.compile(r"^bots?\s+(\d+)\s+(.+)$", re.IGNORECASE)

AUTH_KEYWORDS = [
    "login", "password", "credential", "auth", "bypass",
    "crack", "hack", "exploit", "breach", "steal",
]

BLOCKED_KEYWORDS = [
    "captcha", "bypass captcha", "crack captcha",
    "sql injection", "xss", "exploit",
]


def parse_command(raw: str) -> SwarmCommand | str:
    raw = raw.strip()
    m = COMMAND_RE.match(raw)
    if not m:
        return "Invalid format. Use: bots <number> <task description>"

    count = int(m.group(1))
    task = m.group(2).strip()

    if count < 1:
        return "Number of bots must be at least 1."
    if count > 50:
        return "Maximum 50 bots allowed per command."

    lower = task.lower()

    for kw in BLOCKED_KEYWORDS:
        if kw in lower:
            return f"Task blocked: '{kw}' is not permitted by safety rules."

    for kw in AUTH_KEYWORDS:
        if kw in lower and "@" not in task and "my " not in lower:
            return "requires user clarification — target must be a user-owned or authorized system."

    target_url = None
    url_match = re.search(r"https?://[^\s]+", task)
    if url_match:
        target_url = url_match.group(0)

    inferred = _infer_type(task)

    return SwarmCommand(
        raw=raw,
        agent_count=count,
        task_description=task,
        target_url=target_url,
        inferred_type=inferred,
    )


def _infer_type(task: str) -> TaskType:
    lower = task.lower()
    if any(w in lower for w in ["scrape", "extract", "collect", "gather"]):
        return TaskType.SCRAPE
    if any(w in lower for w in ["create account", "register", "signup", "sign up"]):
        return TaskType.REGISTER
    if any(w in lower for w in ["login", "sign in"]):
        return TaskType.LOGIN
    if any(w in lower for w in ["fill", "form", "submit"]):
        return TaskType.FORM_FILL
    if any(w in lower for w in ["api", "endpoint", "rest"]):
        if any(w in lower for w in ["stress", "load", "flood", "benchmark"]):
            return TaskType.API_STRESS
        if any(w in lower for w in ["rate", "limit", "throttle"]):
            return TaskType.RATE_LIMIT_TEST
        return TaskType.API_CALL
    if any(w in lower for w in ["navigate", "goto", "visit"]):
        return TaskType.NAVIGATE
    if any(w in lower for w in ["validate", "verify"]):
        return TaskType.VALIDATE
    if any(w in lower for w in ["health", "ping", "alive", "heartbeat", "status"]):
        return TaskType.HEALTH_CHECK
    if any(w in lower for w in ["ssl", "tls", "certificate", "cert"]):
        return TaskType.SSL_CHECK
    if any(w in lower for w in ["dns", "resolve", "nameserver"]):
        return TaskType.DNS_CHECK
    if any(w in lower for w in ["port", "open port"]):
        return TaskType.PORT_SCAN
    if any(w in lower for w in ["uptime", "monitor", "watch"]):
        return TaskType.UPTIME_MONITOR
    if any(w in lower for w in ["latency", "response time", "speed", "performance"]):
        return TaskType.RESPONSE_TIME
    if any(w in lower for w in ["header", "http header", "response header"]):
        return TaskType.HEADER_CHECK
    if any(w in lower for w in ["content", "body", "contains", "has text"]):
        return TaskType.CONTENT_CHECK
    if any(w in lower for w in ["cors", "cross-origin"]):
        return TaskType.CORS_CHECK
    if any(w in lower for w in ["redirect", "301", "302", "rewrite"]):
        return TaskType.REDIRECT_CHECK
    if any(w in lower for w in ["robots", "robots.txt", "sitemap"]):
        return TaskType.ROBOTS_CHECK
    if any(w in lower for w in ["whois", "domain lookup"]):
        return TaskType.WHOIS_LOOKUP
    if any(w in lower for w in ["subdomain", "sub-domain"]):
        return TaskType.SUBDOMAIN_SCAN
    if any(w in lower for w in ["cache", "caching", "cdn"]):
        return TaskType.CACHE_CHECK
    if any(w in lower for w in ["compress", "gzip", "brotli"]):
        return TaskType.COMPRESS_CHECK
    if any(w in lower for w in ["auth", "authentication", "token", "jwt", "oauth"]):
        return TaskType.AUTH_TEST
    if any(w in lower for w in ["session", "cookie"]):
        return TaskType.SESSION_TEST
    if any(w in lower for w in ["webhook", "callback"]):
        return TaskType.WEBHOOK_TEST
    if any(w in lower for w in ["fuzz", "brute", "discover"]):
        return TaskType.ENDPOINT_FUZZ
    if any(w in lower for w in ["create email", "provision email", "make email", "new email",
                                "create mailbox", "provision mailbox", "email account",
                                "create address", "email address", "setup email"]):
        return TaskType.PROVISION_EMAIL
    return TaskType.CUSTOM
