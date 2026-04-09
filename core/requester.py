from typing import Optional, Dict
from curl_cffi.requests import AsyncSession
from curl_cffi import Response


class Requester:
    def __init__(
        self,
        referrer: str,
        cookies: Optional[Dict[str, str]] = None,
        proxy: Optional[str] = None,
    ) -> None:
        self._session: Optional[AsyncSession] = None
        self.cookies = cookies or {}
        self.proxy = proxy
        self.headers = {
            "Accept": "*/*",
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/142.0.0.0 Safari/537.36"
            ),
            "Referer": referrer,
        }

    async def __aenter__(self) -> "Requester":
        params = {"allow_redirects": True, "timeout": 60}
        self._session = AsyncSession(
            impersonate="chrome142",
            http_version="v2",
            headers=self.headers,
            proxy=self.proxy,
            **params
        )
        await self._session.__aenter__()
        if self.cookies:
            self._session.cookies.update(self.cookies)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._session:
            await self._session.__aexit__(exc_type, exc_val, exc_tb)
            self._session = None

    async def fetch_get(self, url: str) -> Optional[Response]:
        if not self._session:
            raise RuntimeError("Session not initialized. Use 'async with Requester(...)' context.")
        try:
            response = await self._session.get(url)
            return response
        except Exception:
            return None
