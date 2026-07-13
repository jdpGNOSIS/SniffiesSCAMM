import asyncio
import httpx


class HttpClientTool:
    def __init__(self):
        self._client: httpx.AsyncClient | None = None

    async def ensure(self):
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)

    async def get(self, url: str, **kwargs) -> dict:
        await self.ensure()
        resp = await self._client.get(url, **kwargs)
        return {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "body": resp.text[:5000],
            "url": str(resp.url),
        }

    async def post(self, url: str, data: dict | None = None, json: dict | None = None, **kwargs) -> dict:
        await self.ensure()
        resp = await self._client.post(url, data=data, json=json, **kwargs)
        return {
            "status": resp.status_code,
            "headers": dict(resp.headers),
            "body": resp.text[:5000],
            "url": str(resp.url),
        }

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()
