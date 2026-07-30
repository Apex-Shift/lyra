import itertools
import random
from typing import Any, Dict, List, Optional
import httpx


class NetworkDirector:
    """Gestionnaire de trafic réseau : gère la rotation des identités, proxies et Tor."""
    def __init__(self) -> None:
        self._api_pools: Dict[str, Any] = {}
        self._raw_keys: Dict[str, List[str]] = {}
        self._proxies: List[str] = []
        self._proxy_pool: Optional[Any] = None
        self.tor_enabled: bool = False
        self.strict_anonymity: bool = False
        self.tor_proxy_url: str = "socks5://127.0.0.1:9050"

    def load_infrastructure(self, config: Dict[str, Any]) -> None:
        opsec = config.get("opsec", {})
        self.tor_enabled = opsec.get("use_tor", False)
        self.strict_anonymity = opsec.get("strict_anonymity", False)
        self.tor_proxy_url = opsec.get("tor_proxy_url", "socks5://127.0.0.1:9050")

        # Chargement des pools de clés API
        for service, keys in config.get("api_keys", {}).items():
            if keys:
                self._raw_keys[service] = list(keys)
                self._api_pools[service] = itertools.cycle(self._raw_keys[service])

        # Chargement des proxies SOCKS5 / HTTP
        self._proxies = config.get("proxies", [])
        if self._proxies:
            self._proxy_pool = itertools.cycle(self._proxies)

    def get_api_key(self, service: str) -> Optional[str]:
        pool = self._api_pools.get(service)
        return next(pool) if pool else None

    def get_next_proxy(self) -> Optional[str]:
        if self.tor_enabled:
            return self.tor_proxy_url
        if self._proxy_pool:
            return next(self._proxy_pool)
        
        # En mode STRICT_ANONYMITY, on refuse de sortir sans proxy/Tor
        if self.strict_anonymity:
            raise PermissionError("[-] OPSEC Fail-Closed: Strict anonymity is enabled but no proxy/Tor circuit is active.")
        return None

    def get_authenticated_client(self) -> httpx.AsyncClient:
        proxy_url = self.get_next_proxy()
        mounts = {"all": httpx.AsyncProxyTransport(proxy_url=proxy_url)} if proxy_url else None
        
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
        ]
        
        headers = {
            "User-Agent": random.choice(user_agents),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        }
        
        return httpx.AsyncClient(
            mounts=mounts,
            headers=headers,
            limits=httpx.Limits(max_keepalive_connections=5, max_connections=20),
            timeout=httpx.Timeout(15.0, connect=8.0)
        )