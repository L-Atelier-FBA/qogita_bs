import asyncio
import logging
from typing import Dict
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class QogitaLogin:
    def __init__(self, email: str, password: str, headless: bool = True):
        self.login_url = "https://www.qogita.com/login/"
        self.email = email
        self.password = password
        self.headless = headless

    async def _run(self) -> Dict[str, str]:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=self.headless,
                args=["--disable-blink-features=AutomationControlled"]
            )
            context = await browser.new_context()
            page = await context.new_page()

            try:
                await page.goto(self.login_url, timeout=60000)
                await page.wait_for_load_state("networkidle")

                try:
                    await page.locator("button:has-text('Accept')").click(timeout=5000)
                except PlaywrightTimeoutError:
                    pass

                await page.fill("input[type='email']", self.email)
                await page.fill("input[type='password']", self.password)
                await page.click("button[type='submit']")

                await page.wait_for_load_state("load")
                await page.wait_for_timeout(10000)

                cookies = await context.cookies()
                return {c["name"]: c["value"] for c in cookies}

            finally:
                await browser.close()

    async def login(self, retries: int = 3):
        for attempt in range(1, retries + 1):
            try:
                logging.info(f"Login attempt {attempt}")
                return await self._run()
            except Exception as e:
                logging.warning(f"Login attempt {attempt} failed: {e}")
                if attempt == retries:
                    raise
                await asyncio.sleep(2 ** attempt)
        return None
