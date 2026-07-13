from __future__ import annotations
from enum import Enum
from datetime import datetime, UTC
from typing import Any
from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    TIMEOUT = "timeout"
    BLOCKED = "blocked"


class TaskType(str, Enum):
    FORM_FILL = "form_fill"
    SCRAPE = "scrape"
    API_CALL = "api_call"
    NAVIGATE = "navigate"
    LOGIN = "login"
    REGISTER = "register"
    EXTRACT = "extract"
    VALIDATE = "validate"
    CUSTOM = "custom"
    HEALTH_CHECK = "health_check"
    SSL_CHECK = "ssl_check"
    DNS_CHECK = "dns_check"
    PORT_SCAN = "port_scan"
    LOAD_TEST = "load_test"
    UPTIME_MONITOR = "uptime_monitor"
    RESPONSE_TIME = "response_time"
    HEADER_CHECK = "header_check"
    CONTENT_CHECK = "content_check"
    CERT_CHECK = "cert_check"
    RATE_LIMIT_TEST = "rate_limit_test"
    CORS_CHECK = "cors_check"
    REDIRECT_CHECK = "redirect_check"
    ROBOTS_CHECK = "robots_check"
    LATENCY_PROBE = "latency_probe"
    WHOIS_LOOKUP = "whois_lookup"
    SUBDOMAIN_SCAN = "subdomain_scan"
    API_STRESS = "api_stress"
    ENDPOINT_FUZZ = "endpoint_fuzz"
    CACHE_CHECK = "cache_check"
    COMPRESS_CHECK = "compress_check"
    AUTH_TEST = "auth_test"
    SESSION_TEST = "session_test"
    WEBHOOK_TEST = "webhook_test"
    PROVISION_EMAIL = "provision_email"


class ToolType(str, Enum):
    HTTP_CLIENT = "http_client"
    BROWSER = "browser"
    FILESYSTEM = "filesystem"
    LLM = "llm"
    DNS = "dns"
    SSL = "ssl"
    PING = "ping"
    TRACEROUTE = "traceroute"
    CERTIFICATE = "certificate"
    NETWORK_SCAN = "network_scan"
    EMAIL_PROVISIONER = "email_provisioner"


class SubTask(BaseModel):
    id: str = ""
    agent_id: int = 0
    task_type: TaskType
    instruction: str
    target_url: str | None = None
    payload: dict[str, Any] = {}
    tools_required: list[ToolType] = []
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 60
    depends_on: list[str] = []


class AgentResult(BaseModel):
    agent_id: int
    status: AgentStatus
    actions_taken: list[str] = []
    result: str = ""
    result_data: dict[str, Any] = {}
    errors: list[str] = []
    started_at: str = ""
    completed_at: str = ""
    duration_ms: int = 0
    subtask_id: str = ""


class SwarmCommand(BaseModel):
    raw: str
    agent_count: int
    task_description: str
    target_url: str | None = None
    inferred_type: TaskType = TaskType.CUSTOM


class ProgressReport(BaseModel):
    agent_id: int
    status: AgentStatus
    message: str
    progress_pct: float = 0.0
    timestamp: str = ""


class AggregatedReport(BaseModel):
    command: str
    total_agents: int
    total_time_ms: int
    success_count: int
    failed_count: int
    timed_out_count: int
    block_count: int
    summary: str = ""
    agent_results: list[AgentResult] = []
    warnings: list[str] = []
    generated_at: str = ""
