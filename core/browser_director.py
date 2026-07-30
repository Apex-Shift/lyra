from typing import Any, Optional
from playwright.async_api import async_playwright
from playwright_stealth import stealth_async


class BrowserDirector:
    """Gestionnaire de navigateurs headless invisibles et contournement d'anti-bots."""
    def __init__(self, network_director: Any) -> None:
        self.network_director = network_director
        self.playwright: Optional[Any] = None
        self.browser: Optional[Any] = None

    async def get_stealth_page(self) -> Any:
        if not self.playwright:
            self.playwright = await async_playwright().start()

        proxy_url = self.network_director.get_next_proxy()
        proxy_config = {"server": proxy_url} if proxy_url else None

        if not self.browser:
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-setuid-sandbox"
                ]
            )

        context = await self.browser.new_context(
            proxy=proxy_config,
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await stealth_async(page)  # Application des patchs JS anti-détection
        return page

    async def close(self) -> None:
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()