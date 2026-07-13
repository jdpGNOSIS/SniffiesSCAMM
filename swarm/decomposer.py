"""
Break a high-level task into discrete sub-tasks for each agent.
Now supports global internet server testing.
"""

import uuid
from .schemas import SwarmCommand, SubTask, TaskType, ToolType


def decompose(command: SwarmCommand) -> list[SubTask]:
    n = command.agent_count
    task = command.task_description.lower()
    subs: list[SubTask] = []

    dispatch = {
        TaskType.REGISTER: _decompose_register,
        TaskType.SCRAPE: _decompose_scrape,
        TaskType.LOGIN: _decompose_login,
        TaskType.FORM_FILL: _decompose_form_fill,
        TaskType.API_CALL: _decompose_api,
        TaskType.NAVIGATE: _decompose_navigate,
        TaskType.VALIDATE: _decompose_validate,
        TaskType.HEALTH_CHECK: _decompose_health,
        TaskType.SSL_CHECK: _decompose_ssl,
        TaskType.DNS_CHECK: _decompose_dns,
        TaskType.PORT_SCAN: _decompose_port,
        TaskType.LOAD_TEST: _decompose_load,
        TaskType.UPTIME_MONITOR: _decompose_uptime,
        TaskType.RESPONSE_TIME: _decompose_latency,
        TaskType.HEADER_CHECK: _decompose_headers,
        TaskType.CONTENT_CHECK: _decompose_content,
        TaskType.CERT_CHECK: _decompose_cert,
        TaskType.RATE_LIMIT_TEST: _decompose_rate_limit,
        TaskType.CORS_CHECK: _decompose_cors,
        TaskType.REDIRECT_CHECK: _decompose_redirect,
        TaskType.ROBOTS_CHECK: _decompose_robots,
        TaskType.LATENCY_PROBE: _decompose_latency,
        TaskType.WHOIS_LOOKUP: _decompose_whois,
        TaskType.SUBDOMAIN_SCAN: _decompose_subdomain,
        TaskType.API_STRESS: _decompose_stress,
        TaskType.ENDPOINT_FUZZ: _decompose_fuzz,
        TaskType.CACHE_CHECK: _decompose_cache,
        TaskType.COMPRESS_CHECK: _decompose_compress,
        TaskType.AUTH_TEST: _decompose_auth,
        TaskType.SESSION_TEST: _decompose_session,
        TaskType.WEBHOOK_TEST: _decompose_webhook,
        TaskType.PROVISION_EMAIL: _decompose_email_provision,
        TaskType.CUSTOM: _decompose_custom,
    }

    fn = dispatch.get(command.inferred_type, _decompose_custom)
    subs = fn(command, n)

    for i, s in enumerate(subs):
        s.id = str(uuid.uuid4())[:8]
        s.agent_id = i + 1

    return subs


def _decompose_register(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.REGISTER,
        instruction=f"Create account #{i+1} on {cmd.target_url or 'target site'} — generate unique credentials and submit registration form",
        target_url=cmd.target_url,
        payload={"username": f"testuser_{i+1}_{uuid.uuid4().hex[:6]}", "email": f"testuser_{i+1}@mail.test", "password": "TestPass_123!", "iteration": i+1},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_scrape(cmd: SwarmCommand, n: int) -> list[SubTask]:
    urls = [f"{cmd.target_url}" if cmd.target_url else f"target_{i+1}" for i in range(n)]
    return [SubTask(
        task_type=TaskType.SCRAPE,
        instruction=f"Scrape and summarize content from {urls[i]}",
        target_url=urls[i],
        tools_required=[ToolType.HTTP_CLIENT, ToolType.LLM],
    ) for i in range(n)]


def _decompose_login(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.LOGIN,
        instruction=f"Test login flow #{i+1} on {cmd.target_url} — submit credentials and verify session",
        target_url=cmd.target_url,
        payload={"variant": i + 1},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_form_fill(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.FORM_FILL,
        instruction=f"Fill and submit form variant #{i+1} on {cmd.target_url}",
        target_url=cmd.target_url,
        payload={"variant": i + 1},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_api(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.API_CALL,
        instruction=f"Send API test request #{i+1} to {cmd.target_url or 'endpoint'} — measure status and response time",
        target_url=cmd.target_url,
        payload={"request_id": i + 1},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_navigate(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.NAVIGATE,
        instruction=f"Navigate to {cmd.target_url} — verify page loads, check status code, report title and meta",
        target_url=cmd.target_url,
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_validate(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.VALIDATE,
        instruction=f"Validation #{i+1}: {cmd.task_description} on {cmd.target_url}",
        target_url=cmd.target_url,
        payload={"checkpoint": i + 1},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_health(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.HEALTH_CHECK,
        instruction=f"Agent #{i+1}: Ping health endpoint on {cmd.target_url} — check HTTP status, response time, body presence",
        target_url=cmd.target_url,
        payload={"agent_index": i, "total": n},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_ssl(cmd: SwarmCommand, n: int) -> list[SubTask]:
    endpoints = [f"{cmd.target_url}" for i in range(n)]
    return [SubTask(
        task_type=TaskType.SSL_CHECK,
        instruction=f"Check SSL/TLS certificate for {endpoints[i]} — validate expiry, issuer, cipher, protocol",
        target_url=endpoints[i],
        payload={"check_id": i + 1},
        tools_required=[ToolType.HTTP_CLIENT, ToolType.SSL],
    ) for i in range(n)]


def _decompose_dns(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.DNS_CHECK,
        instruction=f"DNS probe #{i+1}: Resolve {cmd.target_url} — check A, AAAA, CNAME, MX records",
        target_url=cmd.target_url,
        payload={"record_type": ["A", "AAAA", "CNAME", "MX", "TXT", "NS"][i % 6]},
        tools_required=[ToolType.DNS],
    ) for i in range(n)]


def _decompose_port(cmd: SwarmCommand, n: int) -> list[SubTask]:
    common_ports = [21, 22, 25, 53, 80, 110, 143, 443, 465, 587, 993, 995, 1433, 1521, 2049, 2375, 3306, 3389, 5432, 6379, 8080, 8443, 9090, 27017]
    ports_to_check = common_ports[:n] if n <= len(common_ports) else common_ports + [8000 + i for i in range(n - len(common_ports))]
    return [SubTask(
        task_type=TaskType.PORT_SCAN,
        instruction=f"Check if port {ports_to_check[i]} is open on {cmd.target_url}",
        target_url=cmd.target_url,
        payload={"port": ports_to_check[i]},
        tools_required=[ToolType.NETWORK_SCAN],
    ) for i in range(n)]


def _decompose_load(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.LOAD_TEST,
        instruction=f"Load test #{i+1}: Send concurrent request to {cmd.target_url} — measure throughput and latency",
        target_url=cmd.target_url,
        payload={"concurrency": i + 1, "total_requests": n * 10},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_uptime(cmd: SwarmCommand, n: int) -> list[SubTask]:
    intervals = [0, 5, 10, 30, 60, 120, 300, 600]
    return [SubTask(
        task_type=TaskType.UPTIME_MONITOR,
        instruction=f"Uptime check #{i+1}: Probe {cmd.target_url} — measure availability and response",
        target_url=cmd.target_url,
        payload={"probe_id": i + 1, "interval": intervals[i % len(intervals)]},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_latency(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.LATENCY_PROBE,
        instruction=f"Latency probe #{i+1}: Measure response time for {cmd.target_url} from different regions",
        target_url=cmd.target_url,
        payload={"probe_id": i + 1},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_headers(cmd: SwarmCommand, n: int) -> list[SubTask]:
    checks = ["security-headers", "caching-headers", "content-type", "cors", "server", "cookies"]
    return [SubTask(
        task_type=TaskType.HEADER_CHECK,
        instruction=f"Inspect HTTP headers #{i+1}: Check {checks[i % len(checks)]} on {cmd.target_url}",
        target_url=cmd.target_url,
        payload={"header_group": checks[i % len(checks)]},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_content(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.CONTENT_CHECK,
        instruction=f"Content validation #{i+1}: Analyze response body from {cmd.target_url} for correctness",
        target_url=cmd.target_url,
        payload={"check_id": i + 1},
        tools_required=[ToolType.HTTP_CLIENT, ToolType.LLM],
    ) for i in range(n)]


def _decompose_cert(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.CERT_CHECK,
        instruction=f"Certificate deep-check #{i+1}: Validate full certificate chain for {cmd.target_url}",
        target_url=cmd.target_url,
        payload={"depth": i + 1},
        tools_required=[ToolType.CERTIFICATE, ToolType.SSL],
    ) for i in range(n)]


def _decompose_rate_limit(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.RATE_LIMIT_TEST,
        instruction=f"Rate limit test #{i+1}: Send rapid requests to {cmd.target_url} — detect throttling",
        target_url=cmd.target_url,
        payload={"burst": (i + 1) * 5},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_cors(cmd: SwarmCommand, n: int) -> list[SubTask]:
    origins = ["https://example.com", "null", "https://evil.com", "https://attacker.com", "*"]
    return [SubTask(
        task_type=TaskType.CORS_CHECK,
        instruction=f"CORS test #{i+1}: Check cross-origin policy for {origins[i % len(origins)]} on {cmd.target_url}",
        target_url=cmd.target_url,
        payload={"origin": origins[i % len(origins)]},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_redirect(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.REDIRECT_CHECK,
        instruction=f"Redirect check #{i+1}: Trace redirect chain for {cmd.target_url} — detect loops and final destination",
        target_url=cmd.target_url,
        payload={"follow": i < n // 2},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_robots(cmd: SwarmCommand, n: int) -> list[SubTask]:
    paths = ["/robots.txt", "/sitemap.xml", "/sitemap_index.xml", "/.well-known/", "/security.txt", "/humans.txt"]
    return [SubTask(
        task_type=TaskType.ROBOTS_CHECK,
        instruction=f"Crawl #{i+1}: Fetch {paths[i % len(paths)]} from {cmd.target_url} — parse and report",
        target_url=f"{cmd.target_url.rstrip('/')}{paths[i % len(paths)]}" if cmd.target_url else None,
        payload={"path": paths[i % len(paths)]},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_whois(cmd: SwarmCommand, n: int) -> list[SubTask]:
    domain = cmd.target_url.replace("https://", "").replace("http://", "").split("/")[0] if cmd.target_url else "example.com"
    return [SubTask(
        task_type=TaskType.WHOIS_LOOKUP,
        instruction=f"WHOIS lookup #{i+1}: Query domain registration for {domain}",
        target_url=domain,
        payload={"query_id": i + 1},
        tools_required=[ToolType.DNS],
    ) for i in range(n)]


def _decompose_subdomain(cmd: SwarmCommand, n: int) -> list[SubTask]:
    prefixes = ["www", "api", "admin", "mail", "dev", "staging", "test", "blog", "portal", "app"]
    domain = cmd.target_url.replace("https://", "").replace("http://", "").split("/")[0] if cmd.target_url else "example.com"
    return [SubTask(
        task_type=TaskType.SUBDOMAIN_SCAN,
        instruction=f"Subdomain probe #{i+1}: Check if {prefixes[i % len(prefixes)]}.{domain} resolves",
        target_url=f"{prefixes[i % len(prefixes)]}.{domain}",
        payload={"prefix": prefixes[i % len(prefixes)], "domain": domain},
        tools_required=[ToolType.DNS, ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_stress(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.API_STRESS,
        instruction=f"Stress test #{i+1}: Flood {cmd.target_url} with {10*(i+1)} concurrent requests — measure degradation",
        target_url=cmd.target_url,
        payload={"concurrent_users": 10 * (i + 1), "duration_sec": 5},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_fuzz(cmd: SwarmCommand, n: int) -> list[SubTask]:
    paths = ["/admin", "/api/users", "/.env", "/config", "/backup", "/wp-admin", "/phpmyadmin", "/debug", "/test", "/api"]
    return [SubTask(
        task_type=TaskType.ENDPOINT_FUZZ,
        instruction=f"Endpoint discovery #{i+1}: Probe {paths[i % len(paths)]} on {cmd.target_url} — log response codes",
        target_url=f"{cmd.target_url.rstrip('/')}{paths[i % len(paths)]}" if cmd.target_url else None,
        payload={"path": paths[i % len(paths)]},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_cache(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.CACHE_CHECK,
        instruction=f"Cache analysis #{i+1}: Check caching headers and CDN presence for {cmd.target_url}",
        target_url=cmd.target_url,
        payload={"check_id": i + 1},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_compress(cmd: SwarmCommand, n: int) -> list[SubTask]:
    encodings = ["gzip", "deflate", "br", "identity", "compress"]
    return [SubTask(
        task_type=TaskType.COMPRESS_CHECK,
        instruction=f"Compression test #{i+1}: Check if {cmd.target_url} supports {encodings[i % len(encodings)]} encoding",
        target_url=cmd.target_url,
        payload={"encoding": encodings[i % len(encodings)]},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_auth(cmd: SwarmCommand, n: int) -> list[SubTask]:
    auth_types = ["basic", "bearer", "oauth2", "jwt", "session-cookie", "api-key"]
    return [SubTask(
        task_type=TaskType.AUTH_TEST,
        instruction=f"Auth test #{i+1}: Test {auth_types[i % len(auth_types)]} authentication on {cmd.target_url}",
        target_url=cmd.target_url,
        payload={"auth_type": auth_types[i % len(auth_types)]},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_session(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.SESSION_TEST,
        instruction=f"Session test #{i+1}: Test cookie/session handling for {cmd.target_url} — persistence and expiry",
        target_url=cmd.target_url,
        payload={"test_id": i + 1},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_webhook(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.WEBHOOK_TEST,
        instruction=f"Webhook test #{i+1}: Send test payload to {cmd.target_url} and verify delivery",
        target_url=cmd.target_url,
        payload={"event": "test.ping", "delivery_id": i + 1},
        tools_required=[ToolType.HTTP_CLIENT],
    ) for i in range(n)]


def _decompose_email_provision(cmd: SwarmCommand, n: int) -> list[SubTask]:
    domain = "mybusiness.com"
    prefix = "contact"
    parts = cmd.task_description.split()
    for p in parts:
        if "@" in p:
            domain = p.split("@")[1]
            prefix = p.split("@")[0]
            break
    for p in parts:
        if p.startswith("prefix="):
            prefix = p.split("=")[1]
        elif p.startswith("domain="):
            domain = p.split("=")[1]
    usernames = [f"{prefix}{i+1}" for i in range(n)]
    return [SubTask(
        task_type=TaskType.PROVISION_EMAIL,
        instruction=f"Create email account #{i+1}: {u}@{domain}",
        target_url=f"{u}@{domain}",
        payload={
            "email": f"{u}@{domain}",
            "username": u,
            "display_name": f"{prefix.title()} {i+1}",
            "provider": "local",
        },
        tools_required=[ToolType.EMAIL_PROVISIONER],
    ) for i, u in enumerate(usernames)]


def _decompose_custom(cmd: SwarmCommand, n: int) -> list[SubTask]:
    return [SubTask(
        task_type=TaskType.CUSTOM,
        instruction=f"Agent #{i+1}: {cmd.task_description}",
        target_url=cmd.target_url,
        payload={"agent_index": i, "total_agents": n},
        tools_required=[ToolType.HTTP_CLIENT, ToolType.LLM],
    ) for i in range(n)]
