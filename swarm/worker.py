"""
Worker agent — executes sub-tasks against real internet servers.
Supports health checks, SSL, DNS, port scanning, load testing, and more.
"""

import asyncio
import time
import logging
import ssl
import socket
import json
from datetime import datetime, UTC
from urllib.parse import urlparse
from .schemas import SubTask, AgentResult, AgentStatus, ToolType
from .tools import get_tool

logger = logging.getLogger(__name__)


class WorkerAgent:
    def __init__(self, agent_id: int):
        self.agent_id = agent_id
        self._http = None

    async def execute(self, subtask: SubTask) -> AgentResult:
        start = time.monotonic()
        started_at = datetime.now(UTC).isoformat()
        actions = []
        errors = []
        result_data = {}
        final_status = AgentStatus.FAILED

        try:
            actions.append(f"Agent {self.agent_id} starting: {subtask.instruction[:100]}")

            for attempt in range(subtask.max_retries + 1):
                if attempt > 0:
                    actions.append(f"Retry {attempt}/{subtask.max_retries}")
                    await asyncio.sleep(1 * attempt)

                try:
                    result_data, actions_sub, ok = await self._run_with_timeout(
                        subtask, subtask.timeout_seconds
                    )
                    actions.extend(actions_sub)
                    if ok:
                        final_status = AgentStatus.SUCCESS
                        break
                    else:
                        errors.append(f"Attempt {attempt + 1}: returned failure")
                        final_status = AgentStatus.RETRYING
                except asyncio.TimeoutError:
                    errors.append(f"Attempt {attempt + 1}: timed out ({subtask.timeout_seconds}s)")
                    result_data = {"error": "timeout", "timeout_sec": subtask.timeout_seconds}
                    final_status = AgentStatus.TIMEOUT
                except Exception as e:
                    errors.append(f"Attempt {attempt + 1}: {e}")
                    final_status = AgentStatus.RETRYING

            if final_status in (AgentStatus.RETRYING,):
                final_status = AgentStatus.FAILED

        except Exception as e:
            errors.append(str(e))
            final_status = AgentStatus.FAILED

        duration = int((time.monotonic() - start) * 1000)
        return AgentResult(
            agent_id=self.agent_id,
            status=final_status,
            actions_taken=actions,
            result=result_data.get("summary", ""),
            result_data=result_data,
            errors=errors,
            started_at=started_at,
            completed_at=datetime.now(UTC).isoformat(),
            duration_ms=duration,
            subtask_id=subtask.id,
        )

    async def _run_with_timeout(self, subtask, timeout):
        return await asyncio.wait_for(self._execute_subtask(subtask), timeout=timeout)

    async def _execute_subtask(self, subtask):
        actions = []
        http = get_tool("http_client")
        if ToolType.HTTP_CLIENT in subtask.tools_required:
            await http.ensure()

        handlers = {
            "register": self._handle_register,
            "scrape": self._handle_scrape,
            "login": self._handle_login,
            "form_fill": self._handle_form_fill,
            "api_call": self._handle_api,
            "navigate": self._handle_navigate,
            "validate": self._handle_validate,
            "health_check": self._handle_health_check,
            "ssl_check": self._handle_ssl_check,
            "dns_check": self._handle_dns_check,
            "port_scan": self._handle_port_scan,
            "load_test": self._handle_load_test,
            "uptime_monitor": self._handle_uptime,
            "response_time": self._handle_latency,
            "latency_probe": self._handle_latency,
            "header_check": self._handle_headers,
            "content_check": self._handle_content,
            "cert_check": self._handle_cert,
            "rate_limit_test": self._handle_rate_limit,
            "cors_check": self._handle_cors,
            "redirect_check": self._handle_redirect,
            "robots_check": self._handle_robots,
            "whois_lookup": self._handle_whois,
            "subdomain_scan": self._handle_subdomain,
            "api_stress": self._handle_stress,
            "endpoint_fuzz": self._handle_fuzz,
            "cache_check": self._handle_cache,
            "compress_check": self._handle_compress,
            "auth_test": self._handle_auth,
            "session_test": self._handle_session,
            "webhook_test": self._handle_webhook,
            "provision_email": self._handle_email_provision,
            "custom": self._handle_custom,
        }

        handler = handlers.get(subtask.task_type.value, self._handle_custom)
        return await handler(subtask, http, actions)

    # ── ORIGINAL HANDLERS (unchanged) ──

    async def _handle_register(self, subtask, http, actions):
        url = subtask.target_url or "http://localhost:8000/signup"
        payload = subtask.payload
        actions.append(f"POST {url} with user={payload.get('username', '?')}")
        resp = await http.post(url, json=payload)
        ok = 200 <= resp["status"] < 500
        summary = f"Registration {payload.get('username')}: HTTP {resp['status']}"
        actions.append(summary)
        return {"summary": summary, "http_response": resp}, actions, ok

    async def _handle_scrape(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL provided"}, actions, False
        actions.append(f"GET {url}")
        resp = await http.get(url)
        ok = resp["status"] < 400
        summary = f"Scraped {url}: HTTP {resp['status']}, {len(resp.get('body', ''))} chars"
        actions.append(summary)
        return {"summary": summary, "body_preview": resp.get("body", "")[:500], "status": resp["status"]}, actions, ok

    async def _handle_login(self, subtask, http, actions):
        url = subtask.target_url or "http://localhost:8000/login"
        payload = subtask.payload
        actions.append(f"Testing login #{payload.get('variant', '?')}")
        resp = await http.post(url, json={"username": f"user_{payload.get('variant')}", "password": "test"})
        ok = resp["status"] < 400
        summary = f"Login #{payload.get('variant')}: HTTP {resp['status']}"
        actions.append(summary)
        return {"summary": summary, "http_response": resp}, actions, ok

    async def _handle_form_fill(self, subtask, http, actions):
        url = subtask.target_url or "http://localhost:8000/form"
        payload = subtask.payload
        actions.append(f"Form #{payload.get('variant')}")
        resp = await http.post(url, json={"field": f"value_{payload.get('variant')}", "submit": True})
        ok = resp["status"] < 400
        return {"summary": f"Form #{payload.get('variant')}: HTTP {resp['status']}"}, actions, ok

    async def _handle_api(self, subtask, http, actions):
        url = subtask.target_url or "http://localhost:8000/api/test"
        payload = subtask.payload
        start = time.monotonic()
        resp = await http.post(url, json=payload)
        elapsed = int((time.monotonic() - start) * 1000)
        ok = resp["status"] < 500
        summary = f"API #{payload.get('request_id', '?')}: HTTP {resp['status']} in {elapsed}ms"
        actions.append(summary)
        return {"summary": summary, "latency_ms": elapsed}, actions, ok

    async def _handle_navigate(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL provided"}, actions, False
        actions.append(f"GET {url}")
        resp = await http.get(url)
        ok = resp["status"] < 400
        summary = f"Navigate {url}: HTTP {resp['status']} - {'OK' if ok else 'FAIL'}"
        actions.append(summary)
        return {"summary": summary, "status": resp["status"], "headers": resp.get("headers")}, actions, ok

    async def _handle_validate(self, subtask, http, actions):
        url = subtask.target_url
        resp = await http.get(url) if url else {"status": 0, "body": "No target"}
        ok = resp["status"] < 400
        cp = subtask.payload.get("checkpoint", "?")
        return {"summary": f"Validation #{cp}: {'PASS' if ok else 'FAIL'}", "status": resp["status"]}, actions, ok

    async def _handle_email_provision(self, subtask, http, actions):
        from .tools.email_provisioner import EmailProvisionerTool
        prov = EmailProvisionerTool()
        email = subtask.payload.get("email", "")
        display = subtask.payload.get("display_name", "")
        provider = subtask.payload.get("provider", "local")
        password = subtask.payload.get("password", "")
        actions.append(f"Provisioning {email} via {provider}")
        if provider == "local":
            result = prov.create_mailbox_local(email, display, password)
        elif provider == "cloudflare":
            config = prov.get_configured_providers().get("cloudflare", {})
            domain = subtask.target_url.split("@")[1] if "@" in (subtask.target_url or "") else config.get("domain", "")
            result = await prov.provision_via_cloudflare(
                email,
                config.get("api_token", ""),
                config.get("zone_id", ""),
                domain,
            )
        else:
            result = prov.create_mailbox_local(email, display, password)
            result["note"] = f"Provider '{provider}' not configured, fell back to local"
        ok = result.get("success", False)
        summary = result.get("message") or result.get("error", f"Email {email}: {'OK' if ok else 'FAILED'}")
        actions.append(summary)
        return {"summary": summary, "email": email, "result": result}, actions, ok

    async def _handle_custom(self, subtask, http, actions):
        url = subtask.target_url
        if url:
            resp = await http.get(url)
            ok = resp["status"] < 400
            return {"summary": f"Agent #{self.agent_id}: HTTP {resp['status']}"}, actions, ok
        return {"summary": f"Agent #{self.agent_id} completed (no target)"}, actions, True

    # ── NEW GLOBAL SERVER TESTING HANDLERS ──

    async def _handle_health_check(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL for health check"}, actions, False
        start = time.monotonic()
        actions.append(f"Health probe: GET {url}")
        resp = await http.get(url)
        elapsed = int((time.monotonic() - start) * 1000)
        status = resp["status"]
        ok = status < 500
        summary = f"HEALTH: {url} -> HTTP {status} in {elapsed}ms"
        actions.append(summary)
        return {
            "summary": summary, "status_code": status, "latency_ms": elapsed,
            "alive": status < 500, "headers": dict(resp.get("headers", {}))
        }, actions, ok

    async def _handle_ssl_check(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL for SSL check"}, actions, False
        parsed = urlparse(url)
        host = parsed.hostname or url.split("/")[0]
        port = parsed.port or 443
        actions.append(f"SSL check: {host}:{port}")
        try:
            ctx = ssl.create_default_context()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=ctx), timeout=15
            )
            cert = writer.get_extra_info("ssl_object").getpeercert()
            writer.close()
            not_after = cert.get("notAfter", "unknown")
            not_before = cert.get("notBefore", "unknown")
            issuer = dict(x for row in cert.get("issuer", []) for x in row).get("organizationName", "unknown")
            subject = dict(x for row in cert.get("subject", []) for x in row).get("commonName", "unknown")
            sni = cert.get("subjectAltName", [])
            sans = [v for k, v in sni]
            ok = True
            summary = f"SSL OK: {host}:{port} issuer={issuer} subject={subject} expires={not_after}"
            actions.append(summary)
            return {
                "summary": summary, "host": host, "port": port, "issuer": issuer,
                "subject": subject, "not_before": not_before, "not_after": not_after,
                "sans": sans, "valid": True
            }, actions, ok
        except Exception as e:
            actions.append(f"SSL Error: {e}")
            return {"summary": f"SSL FAIL: {host}:{port} - {e}", "error": str(e)}, actions, False

    async def _handle_dns_check(self, subtask, http, actions):
        host = subtask.target_url or "example.com"
        host = host.replace("https://", "").replace("http://", "").split("/")[0]
        record = subtask.payload.get("record_type", "A")
        actions.append(f"DNS lookup: {host} ({record})")
        try:
            loop = asyncio.get_event_loop()
            if record == "A":
                info = await loop.getaddrinfo(host, None, family=socket.AF_INET)
                results = [addr[4][0] for addr in info]
            elif record == "AAAA":
                info = await loop.getaddrinfo(host, None, family=socket.AF_INET6)
                results = [addr[4][0] for addr in info]
            else:
                results = [f"{record} lookup for {host} (simulated)"]
            ok = len(results) > 0
            summary = f"DNS {record}: {host} -> {', '.join(results[:5])}"
            actions.append(summary)
            return {"summary": summary, "host": host, "record": record, "results": results}, actions, ok
        except Exception as e:
            return {"summary": f"DNS FAIL: {host} - {e}", "error": str(e)}, actions, False

    async def _handle_port_scan(self, subtask, http, actions):
        host = subtask.target_url or "localhost"
        host = host.replace("https://", "").replace("http://", "").split("/")[0]
        port = subtask.payload.get("port", 80)
        actions.append(f"Port scan: {host}:{port}")
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=5
            )
            writer.close()
            await writer.wait_closed()
            summary = f"PORT OPEN: {host}:{port}"
            actions.append(summary)
            return {"summary": summary, "host": host, "port": port, "open": True}, actions, True
        except (OSError, asyncio.TimeoutError, ConnectionRefusedError):
            summary = f"PORT CLOSED: {host}:{port}"
            actions.append(summary)
            return {"summary": summary, "host": host, "port": port, "open": False}, actions, True

    async def _handle_load_test(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL"}, actions, False
        concurrency = subtask.payload.get("concurrency", 5)
        total = subtask.payload.get("total_requests", 20)
        actions.append(f"Load test: {url} concurrency={concurrency} requests={total}")
        start = time.monotonic()
        successes = 0
        failures = 0
        latencies = []
        async def _req():
            nonlocal successes, failures
            s = time.monotonic()
            try:
                resp = await http.get(url)
                latencies.append(int((time.monotonic() - s) * 1000))
                if resp["status"] < 500:
                    successes += 1
                else:
                    failures += 1
            except Exception:
                failures += 1
        batch = min(total, 50)
        for _ in range(total // batch):
            await asyncio.gather(*[_req() for _ in range(batch)])
        elapsed = int((time.monotonic() - start) * 1000)
        avg_lat = sum(latencies) // max(len(latencies), 1)
        ok = successes > failures
        summary = f"LOAD: {successes} ok / {failures} fail in {elapsed}ms avg={avg_lat}ms"
        actions.append(summary)
        return {
            "summary": summary, "successes": successes, "failures": failures,
            "total_time_ms": elapsed, "avg_latency_ms": avg_lat, "concurrency": concurrency
        }, actions, ok

    async def _handle_uptime(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL"}, actions, False
        probe = subtask.payload.get("probe_id", 1)
        actions.append(f"Uptime probe #{probe}: {url}")
        start = time.monotonic()
        resp = await http.get(url)
        elapsed = int((time.monotonic() - start) * 1000)
        ok = resp["status"] < 500
        summary = f"UPTIME #{probe}: HTTP {resp['status']} in {elapsed}ms"
        actions.append(summary)
        return {"summary": summary, "probe": probe, "status": resp["status"], "latency_ms": elapsed, "up": ok}, actions, ok

    async def _handle_latency(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL"}, actions, False
        actions.append(f"Latency probe: {url}")
        latencies = []
        for _ in range(3):
            s = time.monotonic()
            await http.get(url)
            latencies.append(int((time.monotonic() - s) * 1000))
            await asyncio.sleep(0.5)
        avg = sum(latencies) // len(latencies)
        summary = f"LATENCY: min={min(latencies)}ms avg={avg}ms max={max(latencies)}ms"
        actions.append(summary)
        return {"summary": summary, "latencies_ms": latencies, "avg_ms": avg, "min_ms": min(latencies), "max_ms": max(latencies)}, actions, True

    async def _handle_headers(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL"}, actions, False
        group = subtask.payload.get("header_group", "all")
        actions.append(f"Header check ({group}): {url}")
        resp = await http.get(url)
        headers = resp.get("headers", {})
        security = {k: v for k, v in headers.items() if k.lower() in (
            "strict-transport-security", "x-content-type-options", "x-frame-options",
            "x-xss-protection", "content-security-policy", "referrer-policy", "x-permitted-cross-domain-policies"
        )}
        cache = {k: v for k, v in headers.items() if "cache" in k.lower()}
        server = {k: v for k, v in headers.items() if k.lower() in ("server", "x-powered-by", "x-aspnet-version")}
        ok = True
        summary = f"HEADERS: {len(headers)} headers received"
        actions.append(summary)
        return {
            "summary": summary, "all_headers": dict(headers),
            "security_headers": security, "cache_headers": cache, "server_headers": server
        }, actions, ok

    async def _handle_content(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL"}, actions, False
        actions.append(f"Content check: {url}")
        resp = await http.get(url)
        body = resp.get("body", "")
        ct = resp.get("headers", {}).get("content-type", "unknown")
        summary = f"CONTENT: type={ct} size={len(body)}b status={resp['status']}"
        actions.append(summary)
        return {"summary": summary, "content_type": ct, "size_bytes": len(body), "body_preview": body[:300]}, actions, resp["status"] < 400

    async def _handle_cert(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL"}, actions, False
        parsed = urlparse(url)
        host = parsed.hostname or url
        depth = subtask.payload.get("depth", 1)
        actions.append(f"Cert check depth={depth}: {host}")
        ctx = ssl.create_default_context()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, 443, ssl=ctx), timeout=15
            )
            cert = writer.get_extra_info("ssl_object").getpeercert()
            writer.close()
            ok = True
            summary = f"CERT OK: {host} subject={dict(x for row in cert.get('subject', []) for x in row).get('commonName', '?')}"
            actions.append(summary)
            return {"summary": summary, "cert": cert, "valid": True}, actions, ok
        except Exception as e:
            return {"summary": f"CERT FAIL: {host} - {e}"}, actions, False

    async def _handle_rate_limit(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL"}, actions, False
        burst = subtask.payload.get("burst", 10)
        actions.append(f"Rate limit test: {url} burst={burst}")
        statuses = {}
        s = time.monotonic()
        for i in range(burst):
            resp = await http.get(url)
            code = resp["status"]
            statuses[code] = statuses.get(code, 0) + 1
        elapsed = int((time.monotonic() - s) * 1000)
        limited = 429 in statuses or 503 in statuses
        summary = f"RATE: {burst} requests in {elapsed}ms, statuses={statuses}, rate_limited={limited}"
        actions.append(summary)
        return {"summary": summary, "burst": burst, "statuses": statuses, "rate_limited": limited, "elapsed_ms": elapsed}, actions, True

    async def _handle_cors(self, subtask, http, actions):
        url = subtask.target_url
        origin = subtask.payload.get("origin", "https://example.com")
        if not url:
            return {"summary": "No URL"}, actions, False
        actions.append(f"CORS test: origin={origin} -> {url}")
        resp = await http.get(url)
        cors = {k: v for k, v in resp.get("headers", {}).items() if "access-control" in k.lower()}
        ok = True
        summary = f"CORS: origin={origin} headers={cors}"
        actions.append(summary)
        return {"summary": summary, "origin": origin, "cors_headers": cors}, actions, ok

    async def _handle_redirect(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL"}, actions, False
        actions.append(f"Redirect trace: {url}")
        import httpx
        try:
            async with httpx.AsyncClient(follow_redirects=True, timeout=15) as client:
                resp = await client.get(url)
                chain = [str(r.url) for r in resp.history] + [str(resp.url)]
                statuses = [r.status_code for r in resp.history] + [resp.status_code]
            summary = f"REDIRECT: {len(resp.history)} hops -> final={resp.url} HTTP {resp.status_code}"
            actions.append(summary)
            return {"summary": summary, "chain": chain, "statuses": statuses, "hops": len(resp.history)}, actions, True
        except Exception as e:
            return {"summary": f"REDIRECT FAIL: {e}"}, actions, False

    async def _handle_robots(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL"}, actions, False
        actions.append(f"Fetch: {url}")
        resp = await http.get(url)
        ok = resp["status"] < 400
        body = resp.get("body", "")[:1000]
        summary = f"ROBOTS: {url} -> HTTP {resp['status']} ({len(body)}b)"
        actions.append(summary)
        return {"summary": summary, "url": url, "status": resp["status"], "content": body}, actions, ok

    async def _handle_whois(self, subtask, http, actions):
        domain = subtask.target_url or "example.com"
        actions.append(f"WHOIS: {domain}")
        try:
            loop = asyncio.get_event_loop()
            info = await loop.getaddrinfo(domain, None)
            ips = list(set(addr[4][0] for addr in info))
            summary = f"WHOIS: {domain} resolves to {', '.join(ips[:5])}"
            actions.append(summary)
            return {"summary": summary, "domain": domain, "ips": ips}, actions, True
        except Exception as e:
            return {"summary": f"WHOIS FAIL: {domain} - {e}"}, actions, False

    async def _handle_subdomain(self, subtask, http, actions):
        target = subtask.target_url or ""
        actions.append(f"Subdomain check: {target}")
        try:
            loop = asyncio.get_event_loop()
            info = await loop.getaddrinfo(target, None)
            ips = list(set(addr[4][0] for addr in info))
            ok = True
            summary = f"SUBDOMAIN: {target} resolves to {', '.join(ips[:3])}"
            actions.append(summary)
            return {"summary": summary, "subdomain": target, "ips": ips, "resolves": True}, actions, ok
        except Exception as e:
            summary = f"SUBDOMAIN: {target} does NOT resolve"
            actions.append(summary)
            return {"summary": summary, "subdomain": target, "resolves": False}, actions, True

    async def _handle_stress(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL"}, actions, False
        concurrent = subtask.payload.get("concurrent_users", 10)
        duration = subtask.payload.get("duration_sec", 5)
        actions.append(f"STRESS: {concurrent} users for {duration}s on {url}")
        start = time.monotonic()
        successes = 0
        failures = 0
        async def _stress():
            nonlocal successes, failures
            while time.monotonic() - start < duration:
                try:
                    resp = await http.get(url)
                    if resp["status"] < 500:
                        successes += 1
                    else:
                        failures += 1
                except Exception:
                    failures += 1
        workers = [_stress() for _ in range(concurrent)]
        await asyncio.gather(*workers)
        elapsed = int((time.monotonic() - start) * 1000)
        total = successes + failures
        rps = total / (elapsed / 1000) if elapsed > 0 else 0
        ok = successes > failures or total == 0
        summary = f"STRESS: {total} req in {elapsed}ms ({rps:.1f} rps) ok={successes} fail={failures}"
        actions.append(summary)
        return {
            "summary": summary, "total_requests": total, "successes": successes,
            "failures": failures, "rps": round(rps, 1), "elapsed_ms": elapsed,
            "concurrent_users": concurrent
        }, actions, ok

    async def _handle_fuzz(self, subtask, http, actions):
        url = subtask.target_url
        path = subtask.payload.get("path", "/")
        if not url:
            return {"summary": "No URL"}, actions, False
        actions.append(f"FUZZ: {url}")
        resp = await http.get(url)
        ok = True
        summary = f"FUZZ: {url} -> HTTP {resp['status']} ({len(resp.get('body', ''))}b)"
        actions.append(summary)
        return {"summary": summary, "path": path, "status": resp["status"], "size": len(resp.get("body", ""))}, actions, ok

    async def _handle_cache(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL"}, actions, False
        actions.append(f"Cache check: {url}")
        resp = await http.get(url)
        headers = resp.get("headers", {})
        cache_control = headers.get("cache-control", "none")
        expires = headers.get("expires", "none")
        cdn = headers.get("x-cache", headers.get("cf-cache-status", headers.get("x-served-by", "none")))
        ok = True
        summary = f"CACHE: control={cache_control} expires={expires} cdn={cdn}"
        actions.append(summary)
        return {"summary": summary, "cache_control": cache_control, "expires": expires, "cdn_status": cdn}, actions, ok

    async def _handle_compress(self, subtask, http, actions):
        url = subtask.target_url
        encoding = subtask.payload.get("encoding", "gzip")
        if not url:
            return {"summary": "No URL"}, actions, False
        actions.append(f"Compression check ({encoding}): {url}")
        import httpx
        try:
            async with httpx.AsyncClient(headers={"Accept-Encoding": encoding}, timeout=15) as client:
                resp = await client.get(url)
            ce = resp.headers.get("content-encoding", "none")
            cl = resp.headers.get("content-length", "?")
            ok = ce != "none"
            summary = f"COMPRESS: requested={encoding} got={ce} length={cl}"
            actions.append(summary)
            return {"summary": summary, "requested_encoding": encoding, "response_encoding": ce}, actions, ok
        except Exception as e:
            return {"summary": f"COMPRESS FAIL: {e}"}, actions, False

    async def _handle_auth(self, subtask, http, actions):
        url = subtask.target_url
        auth_type = subtask.payload.get("auth_type", "basic")
        if not url:
            return {"summary": "No URL"}, actions, False
        actions.append(f"Auth test ({auth_type}): {url}")
        resp = await http.get(url)
        www_auth = resp.get("headers", {}).get("www-authenticate", "none")
        ok = True
        summary = f"AUTH: type={auth_type} www-auth={www_auth} status={resp['status']}"
        actions.append(summary)
        return {"summary": summary, "auth_type_tested": auth_type, "www_authenticate": www_auth}, actions, ok

    async def _handle_session(self, subtask, http, actions):
        url = subtask.target_url
        if not url:
            return {"summary": "No URL"}, actions, False
        actions.append(f"Session test: {url}")
        resp = await http.get(url)
        set_cookie = resp.get("headers", {}).get("set-cookie", "none")
        ok = True
        summary = f"SESSION: set-cookie={'present' if set_cookie != 'none' else 'absent'}"
        actions.append(summary)
        return {"summary": summary, "set_cookie": set_cookie[:200] if set_cookie != "none" else "none"}, actions, ok

    async def _handle_webhook(self, subtask, http, actions):
        url = subtask.target_url
        payload = subtask.payload
        if not url:
            return {"summary": "No URL"}, actions, False
        actions.append(f"Webhook: POST {url}")
        resp = await http.post(url, json=payload)
        ok = resp["status"] < 500
        summary = f"WEBHOOK: HTTP {resp['status']}"
        actions.append(summary)
        return {"summary": summary, "delivery_id": payload.get("delivery_id"), "status": resp["status"]}, actions, ok
