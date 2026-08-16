#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FreeLLM Studio - University Edition
-----------------------------------
A lightweight desktop manager for:
- Local GGUF LLMs via llama.cpp / llama-server
- Cloud OpenAI-compatible providers (Groq, OpenRouter, Gemini, OpenAI, DeepSeek, Together, Custom)
- Provider testing and model discovery
- A local OpenAI-compatible bridge for FreeLLMAPI
- FreeLLMAPI process launch/health checks
- Cline-ready connection information

Design goals:
- Windows-first, CPU-friendly
- No Docker required for the local model path
- No PyTorch / Transformers dependency
- Model/runtime downloaded only on demand
- API keys are stored only in the local app-data directory and are never committed to source

Python: 3.10+
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import faulthandler
import json
import logging
import os
import platform
import queue
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import webbrowser
import zipfile
from dataclasses import asdict, dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse
from urllib.request import getproxies

try:
    import requests
except Exception:
    requests = None  # type: ignore

APP_NAME = "FreeLLM Studio"
APP_VERSION = "1.2.1"
APP_ORG = "University Project"
DEFAULT_BRIDGE_KEY = "freellm-studio-local"
DEFAULT_LOCAL_MODEL_REPO = "Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF"
DEFAULT_LOCAL_MODEL_QUANT = "Q4_K_M"
DEFAULT_LOCAL_ALIAS = "local-qwen-lite"
GITHUB_LLAMA_RELEASE_API = "https://api.github.com/repos/ggerganov/llama.cpp/releases/latest"
HF_MODEL_API = "https://huggingface.co/api/models/{repo}"
HF_RESOLVE_URL = "https://huggingface.co/{repo}/resolve/main/{filename}?download=true"

# -----------------------------
# Paths / config
# -----------------------------


def app_data_root() -> Path:
    if os.name == "nt":
        base = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        return Path(base) / "FreeLLMStudio"
    return Path.home() / ".freellm_studio"


@dataclass
class AppPaths:
    root: Path = field(default_factory=app_data_root)

    @property
    def config(self) -> Path:
        return self.root / "config"

    @property
    def runtime(self) -> Path:
        return self.root / "runtime"

    @property
    def models(self) -> Path:
        return self.root / "models"

    @property
    def logs(self) -> Path:
        return self.root / "logs"

    @property
    def downloads(self) -> Path:
        return self.root / "downloads"

    def ensure(self) -> None:
        for p in (self.root, self.config, self.runtime, self.models, self.logs, self.downloads):
            p.mkdir(parents=True, exist_ok=True)


PATHS = AppPaths()
PATHS.ensure()

# Keep a persistent crash trace.  This is especially useful on Windows where a native
# dependency failure can otherwise make a GUI window disappear without a Python traceback.
CRASH_LOG_FILE = PATHS.logs / "crash.log"
try:
    _CRASH_STREAM = CRASH_LOG_FILE.open("a", encoding="utf-8", buffering=1)
    faulthandler.enable(_CRASH_STREAM, all_threads=True)
except Exception:
    _CRASH_STREAM = None

SETTINGS_FILE = PATHS.config / "settings.json"
SECRETS_FILE = PATHS.config / "secrets.json"
PROVIDERS_FILE = PATHS.config / "providers.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "local_model_repo": DEFAULT_LOCAL_MODEL_REPO,
    "local_model_quant": DEFAULT_LOCAL_MODEL_QUANT,
    "local_model_alias": DEFAULT_LOCAL_ALIAS,
    "local_port": 8080,
    "local_context": 4096,
    "local_threads": max(2, (os.cpu_count() or 4) - 1),
    "bridge_host": "127.0.0.1",
    "bridge_port": 8899,
    "bridge_api_key": DEFAULT_BRIDGE_KEY,
    "active_provider": "Local Model",
    "freellm_project_dir": "",
    "freellm_start_command": "",
    "freellm_base_url": "http://127.0.0.1:3001/v1",
    "freellm_api_key": "",
    "freellm_model": "freellm-studio",
    "freellm_dashboard_url": "http://127.0.0.1:3001",
    # Network routing for cloud APIs. Auto mode honors Windows/system and env proxies,
    # then falls back to direct/TUN networking and common local VPN proxy ports.
    "network_proxy_mode": "auto",
    "network_proxy_url": "",
}


class JsonStore:
    @staticmethod
    def load(path: Path, default: Any) -> Any:
        try:
            if path.exists():
                with path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(default, dict) and isinstance(data, dict):
                    merged = dict(default)
                    merged.update(data)
                    return merged
                return data
        except Exception:
            logging.exception("Failed to load JSON: %s", path)
        return default.copy() if isinstance(default, dict) else default

    @staticmethod
    def save(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)


# -----------------------------
# Secret storage (portable / crash-safe)
# -----------------------------


class SecretStore:
    """Crash-safe local secret storage with no PowerShell/.NET/native crypto dependency.

    The university/demo build prioritizes predictable execution on arbitrary Windows
    installations. Secrets are stored outside the repository under the per-user app-data
    directory and are lightly obfuscated to avoid accidental plain-text exposure. This is
    deliberately not presented as a hardware-backed credential vault; users who need that
    level of protection should use a dedicated OS credential manager.

    Legacy DPAPI entries from older builds are ignored safely and the user is asked to
    re-enter the key once. Importantly, reading or writing a key can no longer launch
    PowerShell or call .NET/Win32 crypto APIs, so this code path cannot crash the Qt process.
    """

    PREFIX = "local1:"

    def __init__(self, path: Path):
        self.path = path
        self.data: Dict[str, str] = JsonStore.load(path, {})
        self._cache: Dict[str, str] = {}
        self._lock = threading.RLock()

    @staticmethod
    def _machine_mask() -> bytes:
        # Stable per Windows/user profile for casual at-rest obfuscation only.
        identity = "|".join([
            APP_NAME,
            os.environ.get("USERNAME", ""),
            os.environ.get("USERDOMAIN", ""),
            platform.node(),
            str(Path.home()),
        ]).encode("utf-8", errors="ignore")
        return hashlib.sha256(identity).digest()

    @classmethod
    def _protect(cls, text: str) -> str:
        raw = text.encode("utf-8")
        key = cls._machine_mask()
        enc = bytes(b ^ key[i % len(key)] for i, b in enumerate(raw))
        return cls.PREFIX + base64.urlsafe_b64encode(enc).decode("ascii")

    @classmethod
    def _unprotect(cls, value: str) -> str:
        if not value:
            return ""
        if value.startswith(cls.PREFIX):
            enc = base64.urlsafe_b64decode(value[len(cls.PREFIX):].encode("ascii"))
            key = cls._machine_mask()
            raw = bytes(b ^ key[i % len(key)] for i, b in enumerate(enc))
            return raw.decode("utf-8")
        if value.startswith("plain:"):
            # Compatibility with a brief fallback format used by an older build.
            return base64.b64decode(value[6:]).decode("utf-8")
        if value.startswith(("dpapi:", "dpapi2:")):
            logger.warning("Legacy DPAPI secret detected; re-enter this API key once for migration")
            return ""
        return ""

    def _save(self) -> None:
        JsonStore.save(self.path, self.data)
        try:
            os.chmod(self.path, 0o600)
        except Exception:
            pass

    def get(self, name: str, default: str = "") -> str:
        with self._lock:
            if name in self._cache:
                return self._cache[name] or default
            try:
                value = self._unprotect(self.data.get(name, ""))
                if value:
                    self._cache[name] = value
                return value or default
            except Exception:
                logger.exception("Could not decode local secret %s", name)
                return default

    def set(self, name: str, value: str) -> None:
        with self._lock:
            if not value:
                self.data.pop(name, None)
                self._cache.pop(name, None)
            else:
                self.data[name] = self._protect(value)
                self._cache[name] = value
            self._save()


SECRETS = SecretStore(SECRETS_FILE)


# -----------------------------
# Logging
# -----------------------------


class QueueLogHandler(logging.Handler):
    def __init__(self, q: queue.Queue[str]):
        super().__init__()
        self.q = q

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.q.put(self.format(record))
        except Exception:
            pass


LOG_QUEUE: queue.Queue[str] = queue.Queue()
logger = logging.getLogger("freellm_studio")
logger.setLevel(logging.INFO)
logger.propagate = False

if not logger.handlers:
    fmt = logging.Formatter("%(asctime)s  %(levelname)s  %(message)s", "%H:%M:%S")
    qh = QueueLogHandler(LOG_QUEUE)
    qh.setFormatter(fmt)
    logger.addHandler(qh)
    fh = logging.FileHandler(PATHS.logs / "studio.log", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logger.addHandler(fh)


# -----------------------------
# Smart network routing (VPN / proxy aware)
# -----------------------------


class NetworkRouteError(RuntimeError):
    """Raised when every safe network route failed before an HTTP response was received."""


class SmartHTTPClient:
    """Requests wrapper that understands Windows/system proxies and common VPN layouts.

    Why this exists:
    - ``requests`` reads environment proxies, but it does not reliably mirror every
      Windows WinINet/System Proxy configuration used by VPN clients.
    - Some VPN applications expose a local HTTP/SOCKS proxy instead of changing the
      machine-wide DNS resolver. A browser can work while Python gets ``getaddrinfo failed``.
    - Localhost traffic must NEVER be sent through a VPN/proxy.

    The client learns a working route per remote host. GET/model-discovery establishes
    the route first, then non-idempotent chat POSTs reuse that same route to avoid
    duplicate requests.
    """

    COMMON_HTTP_PROXY_PORTS = (7890, 7897, 10809, 10811, 2080)
    COMMON_SOCKS_PROXY_PORTS = (10808, 1080, 7891)

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self._lock = threading.RLock()
        self._route_cache: Dict[str, Tuple[str, Optional[str], bool]] = {}

    @staticmethod
    def _host(url: str) -> str:
        return (urlparse(url).hostname or "").lower()

    @classmethod
    def _is_local(cls, url: str) -> bool:
        host = cls._host(url)
        return host in {"127.0.0.1", "localhost", "::1"} or host.endswith(".localhost")

    @staticmethod
    def _normalize_proxy(value: str) -> str:
        value = (value or "").strip()
        if not value:
            return ""
        if "://" not in value:
            value = "http://" + value
        # socks5h delegates DNS to the VPN proxy itself, which is exactly what we want
        # when Windows/Python DNS is blocked while the VPN is otherwise connected.
        if value.lower().startswith("socks5://"):
            value = "socks5h://" + value[len("socks5://"):]
        return value

    def _system_proxy_urls(self) -> List[str]:
        found: List[str] = []
        try:
            raw = getproxies() or {}
            for key in ("https", "http", "all"):
                val = raw.get(key)
                if val:
                    v = self._normalize_proxy(str(val))
                    if v and v not in found:
                        found.append(v)
        except Exception as e:
            logger.debug("Could not read system proxies: %s", e)
        return found

    @staticmethod
    def _environment_proxy_present() -> bool:
        return any(os.getenv(k) for k in (
            "HTTPS_PROXY", "https_proxy", "HTTP_PROXY", "http_proxy", "ALL_PROXY", "all_proxy"
        ))

    @staticmethod
    def _port_open(port: int, timeout: float = 0.08) -> bool:
        try:
            with socket.create_connection(("127.0.0.1", int(port)), timeout=timeout):
                return True
        except OSError:
            return False

    def _common_local_routes(self) -> List[Tuple[str, Optional[str], bool]]:
        if os.name != "nt":
            return []
        blocked = {
            int(self.settings.get("local_port", 8080) or 8080),
            int(self.settings.get("bridge_port", 8899) or 8899),
        }
        routes: List[Tuple[str, Optional[str], bool]] = []
        for port in self.COMMON_HTTP_PROXY_PORTS:
            if port not in blocked and self._port_open(port):
                routes.append((f"Detected HTTP VPN proxy 127.0.0.1:{port}", f"http://127.0.0.1:{port}", False))
        # PySocks is tiny and included in requirements. socks5h is intentional: the proxy
        # resolves the provider hostname remotely, bypassing broken local DNS.
        for port in self.COMMON_SOCKS_PROXY_PORTS:
            if port not in blocked and self._port_open(port):
                routes.append((f"Detected SOCKS VPN proxy 127.0.0.1:{port}", f"socks5h://127.0.0.1:{port}", False))
        return routes

    def _candidate_routes(self, url: str) -> List[Tuple[str, Optional[str], bool]]:
        if self._is_local(url):
            return [("Direct local", None, False)]

        mode = str(self.settings.get("network_proxy_mode") or "auto").lower()
        manual = self._normalize_proxy(str(self.settings.get("network_proxy_url") or ""))
        host = self._host(url)
        routes: List[Tuple[str, Optional[str], bool]] = []
        with self._lock:
            cached = self._route_cache.get(host)
        if cached:
            routes.append(cached)

        if mode == "direct":
            routes.append(("Direct / VPN tunnel", None, False))
        elif mode == "manual":
            if manual:
                routes.append(("Manual proxy", manual, False))
            else:
                routes.append(("Direct / VPN tunnel", None, False))
        else:
            if manual:
                routes.append(("Manual proxy", manual, False))
            for proxy in self._system_proxy_urls():
                routes.append(("Windows/System proxy", proxy, False))
            if self._environment_proxy_present():
                routes.append(("Environment proxy", None, True))
            # A TUN/WireGuard style VPN normally works as a direct connection because the
            # operating system routes it through the tunnel.
            routes.append(("Direct / VPN tunnel", None, False))
            if mode == "auto":
                routes.extend(self._common_local_routes())

        # Stable de-duplication. Route identity includes trust_env because an empty proxy
        # with trust_env=True is not the same as a truly direct connection.
        out: List[Tuple[str, Optional[str], bool]] = []
        seen: set[Tuple[Optional[str], bool]] = set()
        for route in routes:
            key = (route[1], route[2])
            if key not in seen:
                seen.add(key); out.append(route)
        return out

    @staticmethod
    def _session(proxy_url: Optional[str], trust_env: bool) -> "requests.Session":
        s = requests.Session()
        s.trust_env = trust_env
        s.headers.update({"User-Agent": f"{APP_NAME}/{APP_VERSION}"})
        if proxy_url:
            s.proxies.update({"http": proxy_url, "https": proxy_url})
        return s

    @staticmethod
    def _retryable_network_error(exc: Exception) -> bool:
        if requests is None:
            return False
        return isinstance(exc, (
            requests.exceptions.ConnectionError,
            requests.exceptions.ProxyError,
            requests.exceptions.ConnectTimeout,
            requests.exceptions.SSLError,
            requests.exceptions.InvalidSchema,
        ))

    def has_route(self, url: str) -> bool:
        with self._lock:
            return self._host(url) in self._route_cache

    def route_label(self, url: str) -> str:
        if self._is_local(url):
            return "Direct local"
        with self._lock:
            route = self._route_cache.get(self._host(url))
        return route[0] if route else "Auto (not learned yet)"

    def request(self, method: str, url: str, **kwargs: Any) -> "requests.Response":
        if requests is None:
            raise RuntimeError("The requests package is not installed")
        method = method.upper()
        routes = self._candidate_routes(url)
        failures: List[str] = []
        host = self._host(url)
        last_exc: Optional[Exception] = None

        for idx, route in enumerate(routes):
            label, proxy_url, trust_env = route
            session = self._session(proxy_url, trust_env)
            keep_session = False
            try:
                logger.info("Network route %s -> %s %s", label, method, host)
                response = session.request(method, url, **kwargs)
                with self._lock:
                    self._route_cache[host] = route
                logger.info("Network route selected for %s: %s", host, label)
                if bool(kwargs.get("stream", False)):
                    # Keep the underlying pool alive until the caller consumes/closes the
                    # streamed response. Bridge streaming relies on this.
                    setattr(response, "_freellm_session", session)
                    keep_session = True
                return response
            except Exception as e:
                last_exc = e
                short = str(e).replace("\n", " ")[:280]
                failures.append(f"{label}: {short}")
                logger.warning("Network route failed for %s via %s: %s", host, label, short)
                # HTTP/application exceptions are not routing failures. Also do not fan out
                # arbitrary POST failures unless they are clearly connection/proxy failures.
                if not self._retryable_network_error(e):
                    raise
                if method not in {"GET", "HEAD", "OPTIONS"} and idx > 0:
                    break
            finally:
                if not keep_session:
                    session.close()

        detail = " | ".join(failures[-5:])
        if last_exc and ("getaddrinfo failed" in str(last_exc).lower() or "nameresolution" in str(last_exc).lower()):
            prefix = (
                f"Could not resolve {host} through the available Windows/VPN routes. "
                "The app automatically tried system proxy, VPN tunnel and detected local proxy routes."
            )
        else:
            prefix = f"Could not connect to {host} through the available Windows/VPN routes."
        raise NetworkRouteError(prefix + (f"\n\nRoutes tried:\n{detail}" if detail else "")) from last_exc

    def warm_route(self, url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 12) -> None:
        """Learn a safe route using an idempotent GET before chat POSTs."""
        if self._is_local(url) or self.has_route(url):
            return
        r = self.request("GET", url, headers=headers or {}, timeout=timeout)
        # Any HTTP response proves transport/routing worked, including 401/404.
        _ = r.status_code


def friendly_error(value: Any) -> str:
    """Turn low-level requests/Qt tracebacks into an actionable user-facing message."""
    text = str(value or "")
    low = text.lower()
    if isinstance(value, NetworkRouteError):
        return text
    if "getaddrinfo failed" in low or "nameresolutionerror" in low or "failed to resolve" in low:
        return (
            "DNS/VPN routing failed before the request reached the provider.\n\n"
            "FreeLLM Studio will automatically try the Windows proxy, environment proxy, "
            "direct VPN tunnel, and common local VPN proxy ports. If this still appears, "
            "open Settings and enter your VPN's HTTP/SOCKS proxy URL manually."
        )
    if "proxyerror" in low or "cannot connect to proxy" in low:
        return "The configured VPN/proxy is not reachable. Check the VPN connection or proxy address in Settings."
    if "401" in text or "unauthorized" in low:
        return "Authentication failed (HTTP 401). Check the API key and try again."
    if "403" in text or "forbidden" in low:
        return "The provider refused access (HTTP 403). Check account/region/model permissions or your VPN route."
    if "429" in text or "rate limit" in low:
        return "The provider rate limit or quota was reached (HTTP 429). Wait briefly or check your account quota."
    if "timed out" in low or "timeout" in low:
        return "The provider connection timed out. The VPN/proxy may be slow or unreachable."
    if "ssl" in low or "certificate" in low:
        return "TLS/SSL connection failed. Check the VPN/proxy and system date/time; certificate verification was not disabled."
    # Keep popups concise; full technical detail remains in studio.log.
    return text[-1800:]


# -----------------------------
# Provider management
# -----------------------------


@dataclass
class ProviderConfig:
    name: str
    base_url: str
    model: str = ""
    api_key_secret: str = ""
    kind: str = "openai"
    enabled: bool = True
    notes: str = ""


PROVIDER_PRESETS: Dict[str, Dict[str, str]] = {
    "Local Model": {
        "base_url": "http://127.0.0.1:8080/v1",
        "model": DEFAULT_LOCAL_ALIAS,
        "kind": "local",
    },
    "Groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "",
        "kind": "openai",
    },
    "OpenRouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "model": "",
        "kind": "openai",
    },
    "Gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai",
        "model": "",
        "kind": "openai",
    },
    "OpenAI": {
        "base_url": "https://api.openai.com/v1",
        "model": "",
        "kind": "openai",
    },
    "DeepSeek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "",
        "kind": "openai",
    },
    "Together": {
        "base_url": "https://api.together.xyz/v1",
        "model": "",
        "kind": "openai",
    },
    "Custom": {
        "base_url": "",
        "model": "",
        "kind": "openai",
    },
}


def normalize_base_url(url: str) -> str:
    return url.strip().rstrip("/")


def validate_http_url(url: str, allow_localhost: bool = True) -> Tuple[bool, str]:
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https") or not p.netloc:
            return False, "Base URL must start with http:// or https://"
        if not allow_localhost and p.hostname in ("127.0.0.1", "localhost", "::1"):
            return False, "Local URL is not allowed here"
        return True, ""
    except Exception as e:
        return False, str(e)


class ProviderManager:
    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self._lock = threading.RLock()
        self.providers: Dict[str, ProviderConfig] = {}
        self.http = SmartHTTPClient(settings)
        self.load()
        self.ensure_presets()
        self.refresh_local_provider()

    def load(self) -> None:
        raw = JsonStore.load(PROVIDERS_FILE, {})
        for name, item in raw.items():
            try:
                self.providers[name] = ProviderConfig(**item)
            except Exception:
                logger.warning("Skipped invalid provider config: %s", name)

    def save(self) -> None:
        with self._lock:
            JsonStore.save(PROVIDERS_FILE, {k: asdict(v) for k, v in self.providers.items()})

    def ensure_presets(self) -> None:
        changed = False
        for name, p in PROVIDER_PRESETS.items():
            if name not in self.providers:
                self.providers[name] = ProviderConfig(
                    name=name,
                    base_url=p["base_url"],
                    model=p["model"],
                    kind=p["kind"],
                    api_key_secret=f"provider:{name}:api_key",
                )
                changed = True
        if changed:
            self.save()

    def refresh_local_provider(self) -> None:
        with self._lock:
            p = self.providers.get("Local Model")
            if p:
                p.base_url = f"http://127.0.0.1:{int(self.settings['local_port'])}/v1"
                p.model = str(self.settings.get("local_model_alias") or DEFAULT_LOCAL_ALIAS)
                p.api_key_secret = "provider:Local Model:api_key"
                self.save()

    def names(self) -> List[str]:
        with self._lock:
            return list(self.providers.keys())

    def get(self, name: str) -> Optional[ProviderConfig]:
        with self._lock:
            p = self.providers.get(name)
            return ProviderConfig(**asdict(p)) if p else None

    def upsert(self, config: ProviderConfig, api_key: Optional[str] = None) -> None:
        if not config.api_key_secret:
            config.api_key_secret = f"provider:{config.name}:api_key"
        with self._lock:
            self.providers[config.name] = config
            self.save()
        if api_key is not None:
            SECRETS.set(config.api_key_secret, api_key)

    def api_key(self, config: ProviderConfig) -> str:
        if config.kind == "local":
            return SECRETS.get(config.api_key_secret, "local") or "local"
        return SECRETS.get(config.api_key_secret, "")

    def headers(self, config: ProviderConfig, api_key: Optional[str] = None) -> Dict[str, str]:
        key = api_key if api_key is not None else self.api_key(config)
        h = {"Content-Type": "application/json", "Accept": "application/json"}
        if key:
            h["Authorization"] = f"Bearer {key}"
        if config.name == "OpenRouter":
            h["HTTP-Referer"] = "http://127.0.0.1"
            h["X-Title"] = APP_NAME
        return h

    def fetch_models(self, config: ProviderConfig, api_key: Optional[str] = None, timeout: int = 15) -> List[str]:
        if requests is None:
            raise RuntimeError("The requests package is not installed")
        base = normalize_base_url(config.base_url)
        ok, err = validate_http_url(base)
        if not ok:
            raise ValueError(err)
        r = self.http.request("GET", base + "/models", headers=self.headers(config, api_key), timeout=timeout)
        r.raise_for_status()
        data = r.json()
        models = []
        items = data.get("data", []) if isinstance(data, dict) else []
        for item in items:
            if isinstance(item, dict) and item.get("id"):
                models.append(str(item["id"]))
        return models

    def chat_once(
        self,
        config: ProviderConfig,
        messages: List[Dict[str, str]],
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60,
        max_tokens: int = 512,
        temperature: float = 0.2,
    ) -> Dict[str, Any]:
        if requests is None:
            raise RuntimeError("The requests package is not installed")
        base = normalize_base_url(config.base_url)
        ok, err = validate_http_url(base)
        if not ok:
            raise ValueError(err)
        chosen_model = model or config.model
        if config.kind == "local":
            # Ask llama.cpp what it actually loaded. This also tolerates builds where
            # --alias is ignored or represented differently in /v1/models.
            try:
                local_models = self.fetch_models(config, api_key=api_key, timeout=5)
                if local_models:
                    chosen_model = local_models[0]
            except Exception as e:
                logger.debug("Could not discover local model id before chat: %s", e)
        elif not chosen_model:
            # Cloud providers are allowed to start with an empty model field.  Resolve the
            # first model dynamically so Chat can recover even if the user tested the
            # provider before explicitly pressing Save.
            try:
                cloud_models = self.fetch_models(config, api_key=api_key, timeout=15)
                if cloud_models:
                    chosen_model = cloud_models[0]
                    logger.info("Auto-selected model for %s: %s", config.name, chosen_model)
            except Exception as e:
                logger.warning("Could not auto-discover a model for %s: %s", config.name, e)
        if not chosen_model:
            raise ValueError("No model is selected and no model could be discovered automatically")
        payload = {
            "model": chosen_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }
        # Establish/learn the VPN route with an idempotent request before a chat POST.
        # This avoids retrying a non-idempotent completion across multiple proxies.
        if config.kind != "local" and not self.http.has_route(base):
            try:
                self.http.warm_route(base + "/models", headers=self.headers(config, api_key), timeout=min(12, timeout))
            except Exception as e:
                logger.debug("Provider route warm-up failed; chat request will report the route error: %s", e)
        started = time.perf_counter()
        r = self.http.request(
            "POST",
            base + "/chat/completions",
            headers=self.headers(config, api_key),
            json=payload,
            timeout=timeout,
        )
        elapsed = int((time.perf_counter() - started) * 1000)
        if r.status_code >= 400:
            detail = r.text[:1600]
            raise RuntimeError(f"HTTP {r.status_code}: {detail}")
        try:
            data = r.json()
        except Exception as e:
            raise RuntimeError(f"Provider returned a non-JSON response: {r.text[:1000]}") from e
        if not isinstance(data, dict):
            raise RuntimeError("Provider returned an unexpected response type")
        data["_latency_ms"] = elapsed
        return data

    def test_provider(self, config: ProviderConfig, api_key: Optional[str] = None) -> Dict[str, Any]:
        result: Dict[str, Any] = {
            "provider": config.name,
            "models": [],
            "models_ok": False,
            "chat_ok": False,
            "latency_ms": None,
            "message": "",
            "selected_model": "",
            "network_route": "",
        }
        try:
            models = self.fetch_models(config, api_key, timeout=15)
            result["models"] = models[:100]
            result["models_ok"] = True
        except Exception as e:
            result["message"] = f"Models endpoint: {e}"
            # Some compatible APIs omit /models, so chat may still be valid.

        chosen = config.model
        if not chosen and result["models"]:
            chosen = result["models"][0]
        if not chosen:
            if result["models_ok"]:
                raise RuntimeError("Provider returned no models. Select/model ID is required.")
            raise RuntimeError(result["message"] or "Model ID is required")
        result["selected_model"] = chosen

        data = self.chat_once(
            config,
            [{"role": "user", "content": "Reply with exactly: OK"}],
            api_key=api_key,
            model=chosen,
            timeout=45,
            max_tokens=16,
            temperature=0,
        )
        result["chat_ok"] = True
        result["latency_ms"] = data.get("_latency_ms")
        result["network_route"] = self.http.route_label(config.base_url)
        try:
            content = data["choices"][0]["message"]["content"]
        except Exception:
            content = "Response received"
        result["message"] = str(content)[:300]
        return result


# -----------------------------
# Download helpers
# -----------------------------


class DownloadCancelled(Exception):
    pass


def human_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    size = float(n)
    for u in units:
        if size < 1024 or u == units[-1]:
            return f"{size:.1f} {u}"
        size /= 1024
    return f"{n} B"


def download_resumable(
    url: str,
    dest: Path,
    progress: Optional[Callable[[int, int], None]] = None,
    cancel: Optional[Callable[[], bool]] = None,
    timeout: Tuple[int, int] = (15, 60),
) -> Path:
    if requests is None:
        raise RuntimeError("The requests package is not installed")
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_suffix(dest.suffix + ".part")
    existing = part.stat().st_size if part.exists() else 0
    headers = {"User-Agent": f"{APP_NAME}/{APP_VERSION}"}
    if existing:
        headers["Range"] = f"bytes={existing}-"
    with requests.get(url, headers=headers, stream=True, allow_redirects=True, timeout=timeout) as r:
        if r.status_code == 416 and part.exists():
            part.replace(dest)
            return dest
        r.raise_for_status()
        if existing and r.status_code != 206:
            existing = 0
            try:
                part.unlink()
            except FileNotFoundError:
                pass
        content_len = int(r.headers.get("Content-Length", "0") or 0)
        total = existing + content_len if content_len else 0
        mode = "ab" if existing else "wb"
        done = existing
        with part.open(mode) as f:
            for chunk in r.iter_content(chunk_size=1024 * 1024):
                if cancel and cancel():
                    raise DownloadCancelled()
                if not chunk:
                    continue
                f.write(chunk)
                done += len(chunk)
                if progress:
                    progress(done, total)
        f_size = part.stat().st_size
        if total and f_size < total:
            raise IOError(f"Incomplete download: {human_bytes(f_size)} / {human_bytes(total)}")
    part.replace(dest)
    return dest


def resolve_llama_cpp_windows_asset() -> Tuple[str, str]:
    if requests is None:
        raise RuntimeError("The requests package is not installed")
    r = requests.get(GITHUB_LLAMA_RELEASE_API, headers={"User-Agent": APP_NAME}, timeout=20)
    r.raise_for_status()
    release = r.json()
    assets = release.get("assets", [])
    candidates = []
    for a in assets:
        name = str(a.get("name", ""))
        low = name.lower()
        if not low.endswith(".zip"):
            continue
        if "win" not in low:
            continue
        if not any(x in low for x in ("x64", "x86_64", "amd64")):
            continue
        if any(x in low for x in ("cuda", "cudart", "vulkan", "sycl", "hip", "arm64", "aarch64")):
            continue
        score = 0
        if "cpu" in low:
            score += 10
        if "avx2" in low:
            score -= 1
        if "win-x64" in low or "win-x86_64" in low:
            score += 3
        candidates.append((score, name, a.get("browser_download_url", "")))
    if not candidates:
        raise RuntimeError("Could not find a Windows x64 CPU llama.cpp archive in the latest release")
    candidates.sort(reverse=True)
    _, name, url = candidates[0]
    if not url:
        raise RuntimeError("Selected llama.cpp asset has no download URL")
    return name, url


def resolve_hf_gguf(repo: str, quant: str = DEFAULT_LOCAL_MODEL_QUANT) -> Tuple[str, str, Optional[int]]:
    if requests is None:
        raise RuntimeError("The requests package is not installed")
    api = HF_MODEL_API.format(repo=repo)
    r = requests.get(api, headers={"User-Agent": APP_NAME}, timeout=20)
    r.raise_for_status()
    data = r.json()
    siblings = data.get("siblings", [])
    matches = []
    q = quant.lower().replace("-", "_")
    for s in siblings:
        fn = str(s.get("rfilename", ""))
        low = fn.lower()
        if not low.endswith(".gguf"):
            continue
        normalized = low.replace("-", "_")
        score = 0
        if q in normalized:
            score += 20
        if "q4_k_m" in normalized:
            score += 10
        if "instruct" in normalized:
            score += 2
        size = s.get("size") or s.get("lfs", {}).get("size") if isinstance(s, dict) else None
        matches.append((score, fn, size))
    if not matches:
        raise RuntimeError(f"No GGUF files found in Hugging Face repo: {repo}")
    matches.sort(key=lambda x: (x[0], -(x[2] or 0)), reverse=True)
    _, filename, size = matches[0]
    return filename, HF_RESOLVE_URL.format(repo=repo, filename=filename), size


# -----------------------------
# Local llama.cpp manager
# -----------------------------


class LocalModelManager:
    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.process: Optional[subprocess.Popen[str]] = None
        self.log_callback: Optional[Callable[[str], None]] = None
        self._stop_reader = threading.Event()
        self._recent_output: List[str] = []
        self.last_exit_code: Optional[int] = None

    def find_server(self) -> Optional[Path]:
        names = ["llama-server.exe"] if os.name == "nt" else ["llama-server"]
        for name in names:
            for p in PATHS.runtime.rglob(name):
                if p.is_file():
                    return p
        found = shutil.which("llama-server") or shutil.which("llama-server.exe")
        return Path(found) if found else None

    def find_model(self) -> Optional[Path]:
        quant = str(self.settings.get("local_model_quant", DEFAULT_LOCAL_MODEL_QUANT)).lower().replace("-", "_")
        ggufs = list(PATHS.models.glob("*.gguf"))
        if not ggufs:
            return None
        for p in ggufs:
            if quant in p.name.lower().replace("-", "_"):
                return p
        return ggufs[0]

    def install_runtime(self, progress: Optional[Callable[[int, int], None]] = None) -> Path:
        if os.name != "nt":
            raise RuntimeError("Automatic llama.cpp runtime download is currently Windows x64 only. Install llama-server manually on this OS.")
        if platform.machine().lower() not in ("amd64", "x86_64"):
            raise RuntimeError("Automatic runtime currently targets Windows x64")
        asset_name, url = resolve_llama_cpp_windows_asset()
        logger.info("Resolved llama.cpp asset: %s", asset_name)
        zip_path = PATHS.downloads / asset_name
        download_resumable(url, zip_path, progress=progress)
        target = PATHS.runtime / "llama.cpp"
        if target.exists():
            shutil.rmtree(target, ignore_errors=True)
        target.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(target)
        server = self.find_server()
        if not server:
            raise RuntimeError("llama-server.exe was not found after extraction")
        logger.info("llama.cpp runtime ready: %s", server)
        return server

    def install_model(self, progress: Optional[Callable[[int, int], None]] = None) -> Path:
        repo = str(self.settings.get("local_model_repo") or DEFAULT_LOCAL_MODEL_REPO)
        quant = str(self.settings.get("local_model_quant") or DEFAULT_LOCAL_MODEL_QUANT)
        filename, url, size = resolve_hf_gguf(repo, quant)
        logger.info("Resolved model: %s%s", filename, f" ({human_bytes(size)})" if size else "")
        dest = PATHS.models / filename
        if dest.exists() and dest.stat().st_size > 10 * 1024 * 1024:
            logger.info("Model already exists: %s", dest)
            return dest
        download_resumable(url, dest, progress=progress)
        logger.info("Model ready: %s", dest)
        return dest

    def command(self) -> List[str]:
        server = self.find_server()
        model = self.find_model()
        if not server:
            raise RuntimeError("Local runtime is not installed")
        if not model:
            raise RuntimeError("Local GGUF model is not installed")
        port = int(self.settings.get("local_port", 8080))
        context = int(self.settings.get("local_context", 4096))
        threads = max(1, int(self.settings.get("local_threads", max(2, (os.cpu_count() or 4) - 1))))
        alias = str(self.settings.get("local_model_alias") or DEFAULT_LOCAL_ALIAS)
        return [
            str(server), "-m", str(model),
            "--host", "127.0.0.1", "--port", str(port),
            "-c", str(context), "-t", str(threads),
            "--alias", alias,
        ]

    def _base_url(self) -> str:
        return f"http://127.0.0.1:{int(self.settings.get('local_port', 8080))}"

    def _discover_model_id(self, timeout: float = 3.0) -> Optional[str]:
        if requests is None:
            return None
        try:
            r = requests.get(self._base_url() + "/v1/models", timeout=timeout)
            if r.status_code != 200:
                return None
            data = r.json()
            items = data.get("data", []) if isinstance(data, dict) else []
            if isinstance(items, list):
                for item in items:
                    if isinstance(item, dict) and item.get("id"):
                        return str(item["id"])
        except Exception:
            return None
        return None

    def _probe_chat(self, timeout: int = 45) -> Tuple[bool, str]:
        """Perform a real one-token OpenAI chat completion against the local API."""
        if requests is None:
            return False, "The requests package is not installed"
        model_id = self._discover_model_id(timeout=4) or str(
            self.settings.get("local_model_alias") or DEFAULT_LOCAL_ALIAS
        )
        payload = {
            "model": model_id,
            "messages": [{"role": "user", "content": "Reply with OK"}],
            "temperature": 0,
            "max_tokens": 2,
            "stream": False,
        }
        try:
            r = requests.post(
                self._base_url() + "/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json=payload,
                timeout=timeout,
            )
            if r.status_code != 200:
                return False, f"Chat probe returned HTTP {r.status_code}: {r.text[:500]}"
            data = r.json()
            choices = data.get("choices", []) if isinstance(data, dict) else []
            if not choices:
                return False, "Chat probe returned no choices"
            return True, f"Chat API ready ({model_id})"
        except Exception as e:
            return False, f"Chat probe failed: {e}"

    def _find_free_port(self, preferred: int) -> int:
        """Choose a predictable free local port without silently reusing an unrelated service."""
        candidates = [preferred]
        if preferred != 18080:
            candidates.append(18080)
        candidates.extend(range(18081, 18101))
        seen = set()
        for port in candidates:
            if port in seen:
                continue
            seen.add(port)
            if not tcp_open("127.0.0.1", port, timeout=0.15):
                return port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def start(self) -> None:
        if self.process and self.process.poll() is None:
            return

        configured_port = int(self.settings.get("local_port", 8080))
        if tcp_open("127.0.0.1", configured_port, timeout=0.2):
            ok, detail = self._probe_chat(timeout=4)
            if ok:
                logger.info("Reusing an already-running compatible local model on port %s: %s", configured_port, detail)
                return
            new_port = self._find_free_port(configured_port)
            if new_port != configured_port:
                logger.warning(
                    "Configured local port %s is occupied by another/non-ready service; switching to %s",
                    configured_port, new_port,
                )
                self.settings["local_port"] = new_port
                JsonStore.save(SETTINGS_FILE, self.settings)

        cmd = self.command()
        logger.info("Starting local model: %s", " ".join(cmd))
        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" and hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        self._stop_reader.clear()
        self._recent_output.clear()
        self.last_exit_code = None

        server = Path(cmd[0]).resolve()
        workdir = server.parent
        env = os.environ.copy()
        if os.name == "nt":
            env["PATH"] = str(workdir) + os.pathsep + env.get("PATH", "")

        self.process = subprocess.Popen(
            cmd,
            cwd=str(workdir),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creationflags,
        )
        threading.Thread(target=self._reader, daemon=True).start()

        time.sleep(1.0)
        if self.process.poll() is not None:
            self.last_exit_code = self.process.returncode
            tail = "\n".join(self._recent_output[-30:]).strip()
            detail = f"\n\nRuntime output:\n{tail}" if tail else ""
            raise RuntimeError(
                f"llama-server exited immediately (exit code {self.last_exit_code})."
                f"{detail}"
            )

    def _reader(self) -> None:
        p = self.process
        if not p or not p.stdout:
            return
        for line in iter(p.stdout.readline, ""):
            if self._stop_reader.is_set():
                break
            text = line.rstrip()
            if text:
                self._recent_output.append(text)
                if len(self._recent_output) > 300:
                    del self._recent_output[:-300]
                logger.info("[local] %s", text)
                if self.log_callback:
                    self.log_callback(text)
        if p.poll() is not None:
            self.last_exit_code = p.returncode
            logger.info("[local] llama-server exited with code %s", p.returncode)

    def stop(self) -> None:
        p = self.process
        self._stop_reader.set()
        if p and p.poll() is None:
            logger.info("Stopping local model")
            p.terminate()
            try:
                p.wait(timeout=6)
            except subprocess.TimeoutExpired:
                p.kill()
        self.process = None

    def is_running(self) -> bool:
        """Return True only for our live process or a verified compatible local model API."""
        if self.process and self.process.poll() is None:
            return True
        port = int(self.settings.get("local_port", 8080))
        if not tcp_open("127.0.0.1", port, timeout=0.2):
            return False
        return self._discover_model_id(timeout=0.8) is not None

    def readiness(self, verify_chat: bool = False) -> Tuple[bool, str]:
        """Verify HTTP health + model discovery; optionally verify an actual chat completion."""
        port = int(self.settings.get("local_port", 8080))
        base = f"http://127.0.0.1:{port}"
        if not tcp_open("127.0.0.1", port, timeout=0.3):
            return False, "Local API port is not open yet"
        if requests is None:
            return False, "The requests package is not installed"

        health_note = ""
        try:
            r = requests.get(base + "/health", timeout=2)
            if r.status_code == 503:
                return False, "Model is still loading"
            if r.status_code == 200:
                health_note = "health=200"
            elif r.status_code not in (404, 405):
                return False, f"Health endpoint returned HTTP {r.status_code}"
        except requests.RequestException:
            health_note = "health endpoint unavailable"

        model_id = self._discover_model_id(timeout=3)
        if not model_id:
            return False, "OpenAI models endpoint is not ready yet"

        if verify_chat:
            ok, detail = self._probe_chat(timeout=45)
            if not ok:
                return False, detail
            return True, detail
        return True, f"Model loaded ({model_id}; {health_note or 'models verified'})"

    def wait_ready(self, timeout: int = 240) -> bool:
        """Wait until the local model can complete a real OpenAI-compatible chat request."""
        end = time.time() + timeout
        last_reason = "Starting local model"
        while time.time() < end:
            if self.process and self.process.poll() is not None:
                self.last_exit_code = self.process.returncode
                tail = "\n".join(self._recent_output[-35:]).strip()
                detail = f"\n\nRuntime output:\n{tail}" if tail else ""
                raise RuntimeError(
                    f"Local model process stopped before the API became ready "
                    f"(exit code {self.last_exit_code}).{detail}"
                )

            ready, reason = self.readiness(verify_chat=False)
            last_reason = reason
            if ready:
                ok, chat_reason = self._probe_chat(timeout=45)
                if ok:
                    logger.info("Local model passed real chat readiness probe: %s", chat_reason)
                    return True
                last_reason = chat_reason
            time.sleep(0.8)

        tail = "\n".join(self._recent_output[-35:]).strip()
        detail = f"\n\nLast runtime output:\n{tail}" if tail else ""
        raise TimeoutError(
            f"Local model did not pass the end-to-end chat readiness test within {timeout} seconds. "
            f"Last status: {last_reason}.{detail}"
        )


# -----------------------------
# OpenAI-compatible bridge
# -----------------------------


class BridgeState:
    def __init__(self, providers: ProviderManager, settings: Dict[str, Any]):
        self.providers = providers
        self.settings = settings
        self._lock = threading.RLock()

    @property
    def active_name(self) -> str:
        with self._lock:
            return str(self.settings.get("active_provider") or "Local Model")

    def set_active(self, name: str) -> None:
        with self._lock:
            if not self.providers.get(name):
                raise KeyError(name)
            self.settings["active_provider"] = name
            JsonStore.save(SETTINGS_FILE, self.settings)

    def active_config(self) -> ProviderConfig:
        cfg = self.providers.get(self.active_name)
        if not cfg:
            raise RuntimeError("Active provider is not configured")
        return cfg


class BridgeRequestHandler(BaseHTTPRequestHandler):
    server_version = f"{APP_NAME}/{APP_VERSION}"
    protocol_version = "HTTP/1.1"

    @property
    def state(self) -> BridgeState:
        return self.server.bridge_state  # type: ignore[attr-defined]

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.info("[bridge] " + fmt, *args)

    def _json(self, code: int, payload: Any) -> None:
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Connection", "close")
        self.end_headers()
        self.wfile.write(raw)
        self.wfile.flush()

    def _authorized(self) -> bool:
        expected = str(self.state.settings.get("bridge_api_key") or "")
        if not expected:
            return True
        auth = self.headers.get("Authorization", "")
        return auth == f"Bearer {expected}"

    def _path(self) -> str:
        return self.path.split("?", 1)[0].rstrip("/") or "/"

    def do_GET(self) -> None:
        path = self._path()
        if path == "/health":
            try:
                cfg = self.state.active_config()
                self._json(200, {"status": "ok", "active_provider": cfg.name, "model": cfg.model})
            except Exception as e:
                self._json(503, {"status": "error", "error": str(e)})
            return
        if not self._authorized():
            self._json(401, {"error": {"message": "Invalid bridge API key", "type": "authentication_error"}})
            return
        if path in ("/v1/models", "/models"):
            try:
                cfg = self.state.active_config()
                model = cfg.model or f"{cfg.name.lower().replace(' ', '-')}-model"
                self._json(200, {
                    "object": "list",
                    "data": [{"id": model, "object": "model", "owned_by": "freellm-studio"}],
                })
            except Exception as e:
                self._json(500, {"error": {"message": str(e)}})
            return
        self._json(404, {"error": {"message": "Not found"}})

    def do_POST(self) -> None:
        path = self._path()
        if not self._authorized():
            self._json(401, {"error": {"message": "Invalid bridge API key", "type": "authentication_error"}})
            return
        if path not in ("/v1/chat/completions", "/chat/completions"):
            self._json(404, {"error": {"message": "Not found"}})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length)
            payload = json.loads(body.decode("utf-8")) if body else {}
            self._forward_chat(payload)
        except Exception as e:
            logger.exception("Bridge forwarding failed")
            self._json(502, {"error": {"message": str(e), "type": "upstream_error"}})

    def _forward_chat(self, payload: Dict[str, Any]) -> None:
        if requests is None:
            raise RuntimeError("The requests package is not installed")
        cfg = self.state.active_config()
        upstream = normalize_base_url(cfg.base_url) + "/chat/completions"
        # Route to the provider's configured model by default. This is intentional:
        # FreeLLMAPI/Cline can use a stable bridge model alias while the provider changes.
        payload = dict(payload)
        payload["model"] = cfg.model or payload.get("model")
        if not payload.get("model"):
            raise RuntimeError(f"No model configured for provider: {cfg.name}")
        stream = bool(payload.get("stream", False))
        headers = self.state.providers.headers(cfg)
        if cfg.kind != "local" and not self.state.providers.http.has_route(cfg.base_url):
            # Resolve the VPN/proxy route with an idempotent request before forwarding a
            # potentially streaming/non-idempotent chat completion.
            self.state.providers.http.warm_route(normalize_base_url(cfg.base_url) + "/models", headers=headers, timeout=12)
        r = self.state.providers.http.request("POST", upstream, headers=headers, json=payload, stream=stream, timeout=(15, 300))
        if r.status_code >= 400:
            text = r.text[:4000]
            self._json(r.status_code, {"error": {"message": text, "type": "upstream_http_error"}})
            return
        if not stream:
            raw = r.content
            self.send_response(200)
            self.send_header("Content-Type", r.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(raw)
            self.wfile.flush()
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            for line in r.iter_lines(decode_unicode=False):
                if line is None:
                    continue
                self.wfile.write(line + b"\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            logger.info("Bridge client disconnected during stream")
        finally:
            try:
                r.close()
            finally:
                sess = getattr(r, "_freellm_session", None)
                if sess is not None:
                    try: sess.close()
                    except Exception: pass


class BridgeServer:
    def __init__(self, state: BridgeState):
        self.state = state
        self.httpd: Optional[ThreadingHTTPServer] = None
        self.thread: Optional[threading.Thread] = None

    def start(self) -> None:
        if self.running:
            return
        host = str(self.state.settings.get("bridge_host", "127.0.0.1"))
        port = int(self.state.settings.get("bridge_port", 8899))
        httpd = ThreadingHTTPServer((host, port), BridgeRequestHandler)
        httpd.daemon_threads = True
        httpd.bridge_state = self.state  # type: ignore[attr-defined]
        self.httpd = httpd
        self.thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        self.thread.start()
        logger.info("Bridge started at http://%s:%s/v1 (active=%s)", host, port, self.state.active_name)

    def stop(self) -> None:
        if self.httpd:
            logger.info("Stopping bridge")
            self.httpd.shutdown()
            self.httpd.server_close()
        self.httpd = None
        self.thread = None

    @property
    def running(self) -> bool:
        return bool(self.httpd and self.thread and self.thread.is_alive())


# -----------------------------
# FreeLLMAPI process manager
# -----------------------------


class FreeLLMProcessManager:
    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.process: Optional[subprocess.Popen[str]] = None
        self._stop_reader = threading.Event()

    def detect_command(self, project_dir: Path) -> str:
        package_json = project_dir / "package.json"
        if package_json.exists():
            try:
                data = json.loads(package_json.read_text(encoding="utf-8"))
                scripts = data.get("scripts", {})
                for name in ("start", "dev", "serve"):
                    if name in scripts:
                        return f"npm run {name}"
            except Exception:
                pass
        for script in ("start.cmd", "start.bat", "run.cmd", "run.bat"):
            if (project_dir / script).exists():
                return script
        return ""

    def start(self, project_dir: str, command: str = "") -> None:
        if self.process and self.process.poll() is None:
            return
        pdir = Path(project_dir).expanduser().resolve()
        if not pdir.exists():
            raise FileNotFoundError(f"FreeLLMAPI project directory not found: {pdir}")
        cmd = command.strip() or self.detect_command(pdir)
        if not cmd:
            raise RuntimeError("Could not auto-detect the FreeLLMAPI start command. Set it in Gateway settings.")
        logger.info("Starting FreeLLMAPI: %s (cwd=%s)", cmd, pdir)
        self._stop_reader.clear()
        if os.name == "nt":
            args = ["cmd.exe", "/d", "/s", "/c", cmd]
            creationflags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0
        else:
            args = ["/bin/sh", "-lc", cmd]
            creationflags = 0
        self.process = subprocess.Popen(
            args,
            cwd=str(pdir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
            creationflags=creationflags,
        )
        threading.Thread(target=self._reader, daemon=True).start()

    def _reader(self) -> None:
        p = self.process
        if not p or not p.stdout:
            return
        for line in iter(p.stdout.readline, ""):
            if self._stop_reader.is_set():
                break
            text = line.rstrip()
            if text:
                logger.info("[freellmapi] %s", text)

    def stop(self) -> None:
        p = self.process
        self._stop_reader.set()
        if p and p.poll() is None:
            logger.info("Stopping FreeLLMAPI")
            p.terminate()
            try:
                p.wait(timeout=8)
            except subprocess.TimeoutExpired:
                p.kill()
        self.process = None

    def health(self) -> Tuple[bool, str]:
        base = normalize_base_url(str(self.settings.get("freellm_base_url", "http://127.0.0.1:3001/v1")))
        root = re.sub(r"/v1$", "", base)
        try:
            p = urlparse(root)
            if not p.hostname:
                return False, "Invalid FreeLLMAPI URL"
            port = p.port or (443 if p.scheme == "https" else 80)
            if tcp_open(p.hostname, port, timeout=0.5):
                return True, "Port is reachable"
            return False, "Port is not reachable"
        except Exception as e:
            return False, str(e)


# -----------------------------
# Utilities / diagnostics
# -----------------------------


def tcp_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def check_python() -> Tuple[bool, str]:
    ok = sys.version_info >= (3, 10)
    return ok, f"Python {sys.version.split()[0]}"


def check_requests() -> Tuple[bool, str]:
    return requests is not None, f"requests {getattr(requests, '__version__', 'missing') if requests else 'missing'}"


def run_core_self_test() -> int:
    print(f"{APP_NAME} {APP_VERSION} - core self-test")
    tests: List[Tuple[str, bool, str]] = []
    ok, msg = check_python(); tests.append(("Python", ok, msg))
    ok, msg = check_requests(); tests.append(("requests", ok, msg))

    s = dict(DEFAULT_SETTINGS)
    pm = ProviderManager(s)
    tests.append(("Provider presets", len(pm.names()) >= 8, f"{len(pm.names())} providers"))

    # Bridge test with no external network: verify server starts and /health works.
    # Pick a free temporary port.
    sock = socket.socket(); sock.bind(("127.0.0.1", 0)); port = sock.getsockname()[1]; sock.close()
    s["bridge_port"] = port
    state = BridgeState(pm, s)
    bridge = BridgeServer(state)
    try:
        bridge.start()
        if requests:
            r = requests.get(f"http://127.0.0.1:{port}/health", timeout=3)
            tests.append(("Bridge health", r.status_code == 200, r.text[:120]))
            r2 = requests.get(
                f"http://127.0.0.1:{port}/v1/models",
                headers={"Authorization": f"Bearer {s['bridge_api_key']}"}, timeout=3,
            )
            tests.append(("Bridge models", r2.status_code == 200, r2.text[:120]))
    except Exception as e:
        tests.append(("Bridge", False, str(e)))
    finally:
        bridge.stop()

    all_ok = True
    for name, passed, detail in tests:
        print(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
        all_ok &= passed
    return 0 if all_ok else 1


# -----------------------------
# Qt UI (imported late so --self-test can run without PySide6)
# -----------------------------


def launch_gui() -> int:
    try:
        from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, QTimer, Signal
        from PySide6.QtGui import QCloseEvent, QFont, QIcon
        from PySide6.QtWidgets import (
            QApplication, QButtonGroup, QComboBox, QDialog, QFileDialog, QFormLayout,
            QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
            QListWidgetItem, QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar,
            QPushButton, QScrollArea, QSizePolicy, QSpacerItem, QSpinBox, QStackedWidget,
            QTableWidget, QTableWidgetItem, QTextBrowser, QTextEdit, QVBoxLayout, QWidget,
            QHeaderView, QCheckBox,
        )
    except ImportError:
        print("PySide6 is not installed. Run: pip install -r requirements.txt", file=sys.stderr)
        return 2

    settings: Dict[str, Any] = JsonStore.load(SETTINGS_FILE, DEFAULT_SETTINGS)
    providers = ProviderManager(settings)
    local = LocalModelManager(settings)
    bridge_state = BridgeState(providers, settings)
    bridge = BridgeServer(bridge_state)
    freellm = FreeLLMProcessManager(settings)

    class WorkerSignals(QObject):
        result = Signal(object)
        error = Signal(str)
        finished = Signal()
        progress = Signal(int, int)

    class Worker(QRunnable):
        def __init__(self, fn: Callable[..., Any], *args: Any, **kwargs: Any):
            super().__init__()
            self.fn = fn
            self.args = args
            self.kwargs = kwargs
            self.signals = WorkerSignals()
            # PySide/QRunnable objects must outlive queued signal delivery.  Auto-delete
            # can otherwise destroy the C++ runnable immediately after run(), which is
            # a known source of intermittent GUI exits under fast network operations.
            self.setAutoDelete(False)

        def run(self) -> None:
            try:
                result = self.fn(*self.args, **self.kwargs)
                self.signals.result.emit(result)
            except Exception as e:
                logger.exception("Background task failed")
                self.signals.error.emit(friendly_error(e))
            finally:
                self.signals.finished.emit()

    class DownloadWorker(QRunnable):
        def __init__(self, fn: Callable[[Callable[[int, int], None]], Any]):
            super().__init__()
            self.fn = fn
            self.signals = WorkerSignals()
            self.setAutoDelete(False)

        def run(self) -> None:
            try:
                result = self.fn(lambda done, total: self.signals.progress.emit(done, total))
                self.signals.result.emit(result)
            except Exception as e:
                logger.exception("Download/background task failed")
                self.signals.error.emit(friendly_error(e))
            finally:
                self.signals.finished.emit()

    STYLE = """
    * { font-family: 'Segoe UI', 'Inter', sans-serif; font-size: 13px; }
    QMainWindow, QWidget#Root { background: #0b0e13; color: #e8edf6; }
    QFrame#Sidebar { background: #0f131b; border-right: 1px solid #202635; }
    QLabel#Brand { font-size: 19px; font-weight: 700; color: #ffffff; padding: 12px 10px; }
    QLabel#Muted { color: #8e99ad; }
    QLabel#Title { font-size: 25px; font-weight: 700; color: #f8fafc; }
    QLabel#Subtitle { color: #8e99ad; font-size: 13px; }
    QLabel#StatusOk { color: #70e0a4; font-weight: 600; }
    QLabel#StatusBad { color: #ff7c89; font-weight: 600; }
    QFrame#Card { background: #121721; border: 1px solid #232b3b; border-radius: 12px; }
    QFrame#Card:hover { border-color: #344058; }
    QPushButton { background: #1a2130; border: 1px solid #2a3448; border-radius: 8px; padding: 8px 12px; color: #e8edf6; }
    QPushButton:hover { background: #222b3d; border-color: #3c4962; }
    QPushButton:pressed { background: #151b27; }
    QPushButton#Primary { background: #6d5dfc; border-color: #7f73ff; color: white; font-weight: 600; }
    QPushButton#Primary:hover { background: #7a6bff; }
    QPushButton#Danger { background: #3a1d24; border-color: #6b2d38; color: #ff9ba5; }
    QPushButton#Nav { text-align: left; background: transparent; border: none; padding: 10px 14px; color: #aab4c5; }
    QPushButton#Nav:hover { background: #171d29; color: white; }
    QPushButton#Nav:checked { background: #1a2130; color: white; border-left: 3px solid #7667ff; border-radius: 6px; }
    QLineEdit, QTextEdit, QPlainTextEdit, QComboBox, QSpinBox { background: #0d1118; border: 1px solid #283246; border-radius: 8px; padding: 8px; color: #e8edf6; selection-background-color: #5d50d8; }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QComboBox:focus { border-color: #7062ff; }
    QListWidget, QTableWidget, QTextBrowser { background: #0d1118; border: 1px solid #232b3b; border-radius: 10px; color: #e8edf6; }
    QListWidget::item { padding: 10px; border-bottom: 1px solid #191f2b; }
    QListWidget::item:selected { background: #1b2331; color: white; }
    QHeaderView::section { background: #151b25; color: #aeb8ca; border: none; border-bottom: 1px solid #293246; padding: 8px; }
    QProgressBar { background: #0d1118; border: 1px solid #283246; border-radius: 6px; text-align: center; color: white; }
    QProgressBar::chunk { background: #6d5dfc; border-radius: 5px; }
    QScrollBar:vertical { background: #0c1016; width: 11px; margin: 0; }
    QScrollBar::handle:vertical { background: #2b3445; min-height: 25px; border-radius: 5px; }
    """

    def card() -> QFrame:
        f = QFrame(); f.setObjectName("Card")
        return f

    def title_block(title: str, subtitle: str) -> QWidget:
        w = QWidget(); l = QVBoxLayout(w); l.setContentsMargins(0, 0, 0, 12); l.setSpacing(4)
        t = QLabel(title); t.setObjectName("Title")
        s = QLabel(subtitle); s.setObjectName("Subtitle"); s.setWordWrap(True)
        l.addWidget(t); l.addWidget(s)
        return w

    def masked_error(tb: str) -> str:
        # Never render token-like secrets from errors if a library echoes request headers.
        text = re.sub(r"Bearer\s+[A-Za-z0-9_\-.]{12,}", "Bearer ***", str(tb), flags=re.I)
        text = re.sub(r"(gsk_|sk-|sk-or-v1-)[A-Za-z0-9_\-.]{12,}", r"\1***", text, flags=re.I)
        return friendly_error(text)[-2500:]

    class DashboardPage(QWidget):
        def __init__(self, main: "MainWindow"):
            super().__init__(); self.main = main
            layout = QVBoxLayout(self); layout.setContentsMargins(24, 22, 24, 24); layout.setSpacing(16)
            layout.addWidget(title_block("Overview", "Local LLM, cloud providers, bridge and FreeLLMAPI status at a glance."))
            grid = QGridLayout(); grid.setSpacing(12)
            self.local_status = QLabel(); self.bridge_status = QLabel(); self.free_status = QLabel(); self.active_status = QLabel()
            cards = [
                ("Local model", self.local_status), ("Provider bridge", self.bridge_status),
                ("FreeLLMAPI", self.free_status), ("Active provider", self.active_status),
            ]
            for i, (name, value) in enumerate(cards):
                c = card(); cl = QVBoxLayout(c); cl.setContentsMargins(16, 14, 16, 14)
                n = QLabel(name); n.setObjectName("Muted"); value.setStyleSheet("font-size:18px;font-weight:700;")
                cl.addWidget(n); cl.addWidget(value)
                grid.addWidget(c, i // 2, i % 2)
            layout.addLayout(grid)

            quick = card(); ql = QVBoxLayout(quick); ql.setContentsMargins(16,16,16,16)
            h = QLabel("Quick start"); h.setStyleSheet("font-size:16px;font-weight:700;")
            desc = QLabel("Install a lightweight local model, start the bridge, or run the complete diagnostic suite."); desc.setObjectName("Muted")
            buttons = QHBoxLayout()
            b1 = QPushButton("Local setup"); b1.setObjectName("Primary"); b1.clicked.connect(lambda: main.show_page(2))
            b2 = QPushButton("Providers"); b2.clicked.connect(lambda: main.show_page(3))
            b3 = QPushButton("Run diagnostics"); b3.clicked.connect(lambda: main.show_page(5))
            buttons.addWidget(b1); buttons.addWidget(b2); buttons.addWidget(b3); buttons.addStretch(1)
            ql.addWidget(h); ql.addWidget(desc); ql.addLayout(buttons); layout.addWidget(quick)
            layout.addStretch(1)

        def refresh(self) -> None:
            self.local_status.setText("Running" if local.is_running() else "Stopped")
            self.local_status.setObjectName("StatusOk" if local.is_running() else "StatusBad")
            self.local_status.setStyleSheet("font-size:18px;font-weight:700;color:%s;" % ("#70e0a4" if local.is_running() else "#ff7c89"))
            self.bridge_status.setText("Running" if bridge.running else "Stopped")
            self.bridge_status.setStyleSheet("font-size:18px;font-weight:700;color:%s;" % ("#70e0a4" if bridge.running else "#ff7c89"))
            ok, _ = freellm.health(); self.free_status.setText("Reachable" if ok else "Offline")
            self.free_status.setStyleSheet("font-size:18px;font-weight:700;color:%s;" % ("#70e0a4" if ok else "#ff7c89"))
            self.active_status.setText(bridge_state.active_name)

    class ChatPage(QWidget):
        def __init__(self, main: "MainWindow"):
            super().__init__(); self.main = main; self.history: List[Dict[str,str]] = []
            l = QVBoxLayout(self); l.setContentsMargins(24,22,24,24); l.setSpacing(12)
            l.addWidget(title_block("Chat", "Send a real request to the currently active provider."))
            top = QHBoxLayout(); self.provider = QComboBox(); self.provider.addItems(providers.names()); self.provider.setCurrentText(bridge_state.active_name)
            set_active = QPushButton("Set active"); set_active.clicked.connect(self.set_active)
            top.addWidget(QLabel("Provider")); top.addWidget(self.provider, 1); top.addWidget(set_active); l.addLayout(top)
            self.view = QTextBrowser(); self.view.setOpenExternalLinks(True); l.addWidget(self.view, 1)
            bottom = QHBoxLayout(); self.input = QTextEdit(); self.input.setPlaceholderText("Ask the model..."); self.input.setMaximumHeight(100)
            send = QPushButton("Send"); send.setObjectName("Primary"); send.clicked.connect(self.send)
            clear = QPushButton("Clear"); clear.clicked.connect(self.clear_chat)
            bottom.addWidget(self.input, 1); bottom.addWidget(send); bottom.addWidget(clear); l.addLayout(bottom)

        def set_active(self) -> None:
            try:
                bridge_state.set_active(self.provider.currentText()); self.main.toast("Active provider changed")
            except Exception as e: self.main.error(str(e))

        def clear_chat(self) -> None:
            self.history.clear(); self.view.clear()

        def send(self) -> None:
            text = self.input.toPlainText().strip()
            if not text: return
            name = self.provider.currentText(); cfg = providers.get(name)
            if not cfg: return self.main.error("Provider not found")
            if cfg.kind != "local":
                saved_key = providers.api_key(cfg)
                if not saved_key:
                    return self.main.error(
                        f"No saved API key was found for {cfg.name}. Open API Providers, enter the key, and run Test once."
                    )
            if cfg.kind == "local":
                if not local.is_running():
                    return self.main.error("Local Model is not running. Open Local Models and click Start model first.")
                ready, reason = local.readiness(verify_chat=False)
                if not ready:
                    return self.main.error(
                        "Local Model is running but is not ready for chat yet.\n\n"
                        f"Status: {reason}\n\n"
                        "Wait until Local Models shows Ready, then try again."
                    )
            self.history.append({"role":"user","content":text})
            self.view.append(f"<p><b>You</b><br>{html_escape(text)}</p>")
            self.input.clear(); self.main.set_busy(True, "Waiting for model...")
            worker = Worker(providers.chat_once, cfg, list(self.history), timeout=120)
            worker.signals.result.connect(self._chat_result)
            def chat_error(x: str) -> None:
                # Remove the failed user turn so retrying does not duplicate it.
                if self.history and self.history[-1].get("role") == "user":
                    self.history.pop()
                self.main.error(masked_error(x))
            worker.signals.error.connect(chat_error)
            worker.signals.finished.connect(lambda: self.main.set_busy(False)); self.main.start_worker(worker)

        def _chat_result(self, data: Dict[str,Any]) -> None:
            try: text = str(data["choices"][0]["message"]["content"])
            except Exception: text = json.dumps(data, ensure_ascii=False, indent=2)
            self.history.append({"role":"assistant","content":text})
            latency = data.get("_latency_ms")
            suffix = f"<br><span style='color:#7f8a9d'>Latency: {latency} ms</span>" if latency else ""
            self.view.append(f"<p><b>Assistant</b><br><pre style='white-space:pre-wrap'>{html_escape(text)}</pre>{suffix}</p>")

    class LocalPage(QWidget):
        def __init__(self, main: "MainWindow"):
            super().__init__(); self.main = main
            l = QVBoxLayout(self); l.setContentsMargins(24,22,24,24); l.setSpacing(14)
            l.addWidget(title_block("Local model", "CPU-friendly GGUF inference powered by llama.cpp. No Docker, PyTorch or Ollama required."))
            c = card(); cl = QVBoxLayout(c); cl.setContentsMargins(16,16,16,16); cl.setSpacing(10)
            self.runtime = QLabel(); self.model = QLabel(); self.status = QLabel(); self.endpoint = QLabel()
            for label in (self.runtime,self.model,self.status,self.endpoint): cl.addWidget(label)
            btns = QHBoxLayout();
            br = QPushButton("Install runtime"); br.clicked.connect(self.install_runtime)
            bm = QPushButton("Download Lite model"); bm.clicked.connect(self.install_model)
            bs = QPushButton("Start model"); bs.setObjectName("Primary"); bs.clicked.connect(self.start_model)
            bx = QPushButton("Stop"); bx.setObjectName("Danger"); bx.clicked.connect(self.stop_model)
            for b in (br,bm,bs,bx): btns.addWidget(b)
            btns.addStretch(1); cl.addLayout(btns)
            self.progress = QProgressBar(); self.progress.setVisible(False); cl.addWidget(self.progress)
            l.addWidget(c)

            cfg = card(); fl = QFormLayout(cfg); fl.setContentsMargins(16,16,16,16)
            self.repo = QLineEdit(str(settings["local_model_repo"])); self.quant = QLineEdit(str(settings["local_model_quant"])); self.alias = QLineEdit(str(settings["local_model_alias"]))
            self.port = QSpinBox(); self.port.setRange(1024,65535); self.port.setValue(int(settings["local_port"]))
            self.context = QSpinBox(); self.context.setRange(512,32768); self.context.setSingleStep(512); self.context.setValue(int(settings["local_context"]))
            self.threads = QSpinBox(); self.threads.setRange(1, max(2, os.cpu_count() or 8)); self.threads.setValue(int(settings["local_threads"]))
            save = QPushButton("Save local settings"); save.clicked.connect(self.save_settings)
            fl.addRow("Hugging Face repo", self.repo); fl.addRow("Quantization", self.quant); fl.addRow("Model alias", self.alias); fl.addRow("Port", self.port); fl.addRow("Context", self.context); fl.addRow("CPU threads", self.threads); fl.addRow("", save)
            l.addWidget(cfg); l.addStretch(1); self.refresh()

        def refresh(self) -> None:
            server = local.find_server(); model = local.find_model(); running = local.is_running()
            ready, reason = local.readiness(verify_chat=False) if running else (False, "Stopped")
            self.runtime.setText(f"Runtime: {'✓ ' + str(server) if server else 'Not installed'}")
            self.model.setText(f"Model: {'✓ ' + model.name if model else 'Not downloaded'}")
            if ready:
                status_text, color = "● Ready", "#70e0a4"
            elif running:
                status_text, color = f"◐ Starting — {reason}", "#f4c56a"
            else:
                status_text, color = "○ Stopped", "#ff7c89"
            self.status.setText(f"Status: {status_text}")
            self.status.setStyleSheet(f"color:{color};font-weight:700;")
            self.endpoint.setText(f"OpenAI API: http://127.0.0.1:{settings['local_port']}/v1")

        def _dl(self, fn: Callable[[Callable[[int,int],None]],Any]) -> None:
            self.progress.setVisible(True); self.progress.setRange(0,100); self.progress.setValue(0); self.main.set_busy(True,"Downloading...")
            w = DownloadWorker(fn)
            def prog(done:int,total:int):
                if total: self.progress.setValue(int(done*100/total)); self.progress.setFormat(f"{human_bytes(done)} / {human_bytes(total)}")
                else: self.progress.setRange(0,0)
            w.signals.progress.connect(prog); w.signals.result.connect(lambda p: self.main.toast(f"Ready: {Path(str(p)).name}")); w.signals.error.connect(lambda x:self.main.error(masked_error(x)))
            def fin(): self.main.set_busy(False); self.progress.setVisible(False); self.refresh(); providers.refresh_local_provider()
            w.signals.finished.connect(fin); self.main.start_worker(w)

        def install_runtime(self): self._dl(local.install_runtime)
        def install_model(self): self._dl(local.install_model)

        def start_model(self) -> None:
            try:
                self.save_settings(silent=True)
                local.start()
                self.main.set_busy(True,"Starting local model...")
                w = Worker(local.wait_ready, 240)
                def ready(_: Any) -> None:
                    providers.refresh_local_provider()
                    self.port.setValue(int(settings["local_port"]))
                    bridge_state.set_active("Local Model")
                    try:
                        chat_page = self.main.pages[1]
                        chat_page.provider.setCurrentText("Local Model")
                    except Exception:
                        pass
                    self.main.toast("Local model is READY — real chat probe passed")
                def failed(msg: str) -> None:
                    self.main.error(masked_error(msg))
                def finished() -> None:
                    self.main.set_busy(False)
                    self.refresh()
                w.signals.result.connect(ready)
                w.signals.error.connect(failed)
                w.signals.finished.connect(finished)
                self.main.start_worker(w)
            except Exception as e:
                self.refresh()
                self.main.error(masked_error(str(e)))

        def stop_model(self) -> None:
            local.stop(); self.refresh()

        def save_settings(self, silent: bool=False) -> None:
            settings.update({"local_model_repo":self.repo.text().strip(),"local_model_quant":self.quant.text().strip(),"local_model_alias":self.alias.text().strip(),"local_port":self.port.value(),"local_context":self.context.value(),"local_threads":self.threads.value()})
            JsonStore.save(SETTINGS_FILE, settings); providers.refresh_local_provider();
            if not silent: self.main.toast("Local settings saved")
            self.refresh()

    class ProvidersPage(QWidget):
        def __init__(self, main: "MainWindow"):
            super().__init__(); self.main=main
            l = QVBoxLayout(self); l.setContentsMargins(24,22,24,24); l.setSpacing(12)
            l.addWidget(title_block("API providers", "Add API keys, discover models, run a real inference test, and choose the active route."))
            body = QHBoxLayout(); self.list=QListWidget(); self.list.setFixedWidth(190); self.list.addItems(providers.names()); self.list.currentTextChanged.connect(self.load_provider); body.addWidget(self.list)
            form_card=card(); form=QFormLayout(form_card); form.setContentsMargins(18,18,18,18); form.setSpacing(10)
            self.name=QLineEdit(); self.base=QLineEdit(); self.key=QLineEdit(); self.key.setEchoMode(QLineEdit.EchoMode.Password); self.model=QComboBox(); self.model.setEditable(True)
            self.result=QLabel("Not tested"); self.result.setWordWrap(True); self.result.setObjectName("Muted")
            buttons=QHBoxLayout(); self.save_btn=QPushButton("Save"); self.save_btn.clicked.connect(self.save_provider); self.fetch_btn=QPushButton("Fetch models"); self.fetch_btn.clicked.connect(self.fetch_models); self.test_btn=QPushButton("Test"); self.test_btn.setObjectName("Primary"); self.test_btn.clicked.connect(self.test_provider); self.active_btn=QPushButton("Set active"); self.active_btn.clicked.connect(self.set_active)
            self._provider_busy = False
            for b in (self.save_btn,self.fetch_btn,self.test_btn,self.active_btn): buttons.addWidget(b)
            form.addRow("Name",self.name); form.addRow("Base URL",self.base); form.addRow("API key",self.key); form.addRow("Model",self.model); form.addRow("Status",self.result); form.addRow("",buttons)
            body.addWidget(form_card,1); l.addLayout(body,1)
            add=QPushButton("+ Add custom provider"); add.clicked.connect(self.add_custom); l.addWidget(add,0,Qt.AlignLeft)
            self.list.setCurrentRow(0)

        def _set_provider_busy(self, busy: bool, text: str = "") -> None:
            self._provider_busy = busy
            for b in (self.save_btn, self.fetch_btn, self.test_btn, self.active_btn):
                b.setEnabled(not busy)
            self.list.setEnabled(not busy)
            self.base.setEnabled(not busy)
            self.key.setEnabled(not busy)
            self.model.setEnabled(not busy)
            if busy and text:
                self.result.setText(text)

        def load_provider(self,name:str)->None:
            cfg=providers.get(name)
            if not cfg:return
            self.name.setText(cfg.name); self.name.setEnabled(cfg.name=="Custom" or cfg.name.startswith("Custom "))
            self.base.setText(cfg.base_url); self.key.setText(providers.api_key(cfg)); self.model.clear(); self.model.addItem(cfg.model or ""); self.result.setText("Not tested")
            if cfg.kind=="local": self.key.setPlaceholderText("Local server usually ignores this key")
            else: self.key.setPlaceholderText("Stored locally outside the project (never committed)")

        def current_config(self)->ProviderConfig:
            old_name=self.list.currentItem().text() if self.list.currentItem() else self.name.text().strip()
            old=providers.get(old_name)
            return ProviderConfig(name=self.name.text().strip() or old_name,base_url=self.base.text().strip(),model=self.model.currentText().strip(),api_key_secret=(old.api_key_secret if old else f"provider:{self.name.text().strip()}:api_key"),kind=(old.kind if old else "openai"))

        def save_provider(self)->None:
            try:
                cfg=self.current_config(); ok,err=validate_http_url(cfg.base_url)
                if not ok:return self.main.error(err)
                if not cfg.name:return self.main.error("Provider name is required")
                providers.upsert(cfg,self.key.text())
                self.main.toast("Provider saved")
                self.refresh_list(select=cfg.name)
            except Exception as e:
                logger.exception("Could not save provider")
                self.main.error("Provider test may be valid, but saving the local configuration failed.\n\n" + masked_error(str(e)))

        def fetch_models(self)->None:
            if self._provider_busy:
                return
            try:
                cfg=self.current_config(); key=self.key.text().strip()
                ok, err = validate_http_url(cfg.base_url)
                if not ok: return self.main.error(err)
                if cfg.kind != "local" and not key: return self.main.error("API key is required")
            except Exception as e:
                return self.main.error(masked_error(str(e)))
            self._set_provider_busy(True, "Fetching models..."); self.main.set_busy(True,"Fetching models...")
            w=Worker(providers.fetch_models,cfg,key,20)
            def done(models:List[str]):
                current=self.model.currentText(); self.model.clear(); self.model.addItems(models)
                if current and current in models: self.model.setCurrentText(current)
                elif models: self.model.setCurrentIndex(0)
                self.result.setText(f"✓ {len(models)} models discovered")
                self.result.setStyleSheet("color:#70e0a4;font-weight:600;")
            def failed(x:str):
                self.result.setText("✗ Could not fetch models")
                self.result.setStyleSheet("color:#ff7c89;")
                self.main.error(masked_error(x))
            def finished():
                self.main.set_busy(False); self._set_provider_busy(False)
            w.signals.result.connect(done); w.signals.error.connect(failed); w.signals.finished.connect(finished); self.main.start_worker(w)

        def test_provider(self)->None:
            if self._provider_busy:
                return
            try:
                cfg=self.current_config(); key=self.key.text().strip()
                ok, err = validate_http_url(cfg.base_url)
                if not ok: return self.main.error(err)
                if cfg.kind != "local" and not key: return self.main.error("API key is required")
            except Exception as e:
                return self.main.error(masked_error(str(e)))
            self._set_provider_busy(True,"Testing authentication and inference..."); self.main.set_busy(True,"Testing provider...")
            w=Worker(providers.test_provider,cfg,key)
            def done(r:Dict[str,Any]):
                # A successful real inference test is authoritative: persist the API key
                # and the exact model that passed, then make this provider active so the
                # Chat page works immediately without a second Save/Set-active step.
                models = list(r.get("models") or [])
                chosen = str(r.get("selected_model") or cfg.model or "").strip()
                if models:
                    self.model.blockSignals(True)
                    self.model.clear(); self.model.addItems(models)
                    self.model.blockSignals(False)
                if chosen:
                    if self.model.findText(chosen) < 0:
                        self.model.addItem(chosen)
                    self.model.setCurrentText(chosen)
                saved_cfg = ProviderConfig(
                    name=cfg.name,
                    base_url=cfg.base_url,
                    model=chosen,
                    api_key_secret=cfg.api_key_secret,
                    kind=cfg.kind,
                    enabled=cfg.enabled,
                    notes=cfg.notes,
                )
                try:
                    providers.upsert(saved_cfg, key)
                    bridge_state.set_active(saved_cfg.name)
                    try:
                        chat_page = self.main.pages[1]
                        chat_page.provider.setCurrentText(saved_cfg.name)
                    except Exception:
                        pass
                except Exception as e:
                    logger.exception("Provider inference passed but persistence failed")
                    self.result.setText(
                        f"✓ API works | model={chosen or 'auto'} | chat=PASS | "
                        f"{r.get('latency_ms')} ms | local save=FAILED"
                    )
                    self.result.setStyleSheet("color:#ffcc66;font-weight:600;")
                    self.main.error(
                        "The provider API test succeeded, but the local configuration could not be saved.\n\n"
                        + masked_error(str(e))
                    )
                    return
                self.result.setText(
                    f"✓ Connected & active | model={chosen or 'auto'} | "
                    f"models={'PASS' if r['models_ok'] else 'SKIP'} | chat=PASS | "
                    f"{r.get('latency_ms')} ms | route={r.get('network_route') or 'auto'}"
                )
                self.result.setStyleSheet("color:#70e0a4;font-weight:600;")
                self.main.toast(f"{saved_cfg.name} tested, saved and set active")
            def failed(x:str):
                self.result.setText("✗ Test failed")
                self.result.setStyleSheet("color:#ff7c89;")
                self.main.error(masked_error(x))
            def finished():
                self.main.set_busy(False); self._set_provider_busy(False)
            w.signals.result.connect(done); w.signals.error.connect(failed); w.signals.finished.connect(finished); self.main.start_worker(w)

        def set_active(self)->None:
            try:self.save_provider(); bridge_state.set_active(self.name.text().strip()); self.main.toast("Active provider updated")
            except Exception as e:self.main.error(str(e))

        def add_custom(self)->None:
            idx=1
            while providers.get(f"Custom {idx}"):idx+=1
            name=f"Custom {idx}"; providers.upsert(ProviderConfig(name=name,base_url="",model="",api_key_secret=f"provider:{name}:api_key",kind="openai"),""); self.refresh_list(select=name)

        def refresh_list(self,select:Optional[str]=None)->None:
            self.list.blockSignals(True); self.list.clear(); self.list.addItems(providers.names()); self.list.blockSignals(False)
            if select:
                items=self.list.findItems(select,Qt.MatchExactly)
                if items:self.list.setCurrentItem(items[0])
            elif self.list.count():self.list.setCurrentRow(0)

    class GatewayPage(QWidget):
        def __init__(self, main:"MainWindow"):
            super().__init__(); self.main=main
            l=QVBoxLayout(self); l.setContentsMargins(24,22,24,24); l.setSpacing(14)
            l.addWidget(title_block("Gateway & Cline", "Use the Python bridge as one stable OpenAI-compatible provider inside FreeLLMAPI. Switch actual providers here without reconfiguring Cline."))
            bridge_card=card(); bl=QFormLayout(bridge_card); bl.setContentsMargins(16,16,16,16)
            self.bridge_status=QLabel(); self.bridge_url=QLineEdit(f"http://127.0.0.1:{settings['bridge_port']}/v1"); self.bridge_url.setReadOnly(True); self.bridge_key=QLineEdit(str(settings["bridge_api_key"]));
            hb=QHBoxLayout(); sb=QPushButton("Start bridge"); sb.setObjectName("Primary"); sb.clicked.connect(self.start_bridge); xb=QPushButton("Stop"); xb.clicked.connect(lambda:(bridge.stop(),self.refresh())); tb=QPushButton("Test bridge"); tb.clicked.connect(self.test_bridge); cb=QPushButton("Copy config"); cb.clicked.connect(self.copy_bridge)
            for b in (sb,xb,tb,cb):hb.addWidget(b)
            bl.addRow("Bridge status",self.bridge_status); bl.addRow("Base URL",self.bridge_url); bl.addRow("API key",self.bridge_key); bl.addRow("",hb); l.addWidget(bridge_card)

            free=card(); fl=QFormLayout(free); fl.setContentsMargins(16,16,16,16)
            self.project=QLineEdit(str(settings.get("freellm_project_dir",""))); pick=QPushButton("Browse"); pick.clicked.connect(self.pick_project); ph=QHBoxLayout(); ph.addWidget(self.project,1); ph.addWidget(pick)
            self.command=QLineEdit(str(settings.get("freellm_start_command",""))); self.command.setPlaceholderText("Auto-detect: npm run start/dev")
            self.free_base=QLineEdit(str(settings.get("freellm_base_url","http://127.0.0.1:3001/v1"))); self.free_key=QLineEdit(SECRETS.get("freellm_api_key",str(settings.get("freellm_api_key","")))); self.free_key.setEchoMode(QLineEdit.EchoMode.Password)
            self.free_model=QLineEdit(str(settings.get("freellm_model","freellm-studio"))); self.free_status=QLabel()
            fh=QHBoxLayout(); sf=QPushButton("Start FreeLLMAPI"); sf.clicked.connect(self.start_free); xf=QPushButton("Stop"); xf.clicked.connect(lambda:(freellm.stop(),self.refresh())); of=QPushButton("Open dashboard"); of.clicked.connect(lambda:webbrowser.open(str(settings.get("freellm_dashboard_url","http://127.0.0.1:3001")))); save=QPushButton("Save"); save.clicked.connect(self.save_free)
            for b in (sf,xf,of,save):fh.addWidget(b)
            fl.addRow("Project directory",ph); fl.addRow("Start command",self.command); fl.addRow("FreeLLMAPI base URL",self.free_base); fl.addRow("Unified API key",self.free_key); fl.addRow("Model name",self.free_model); fl.addRow("Status",self.free_status); fl.addRow("",fh); l.addWidget(free)

            note=QLabel("One-time FreeLLMAPI setup: add a Custom OpenAI-compatible provider with the Bridge Base URL and Bridge API key above. After that, provider/model switching happens entirely inside FreeLLM Studio."); note.setWordWrap(True); note.setObjectName("Muted"); l.addWidget(note); l.addStretch(1); self.refresh()

        def refresh(self)->None:
            self.bridge_status.setText("● Running" if bridge.running else "○ Stopped"); self.bridge_status.setStyleSheet("color:%s;font-weight:700;" % ("#70e0a4" if bridge.running else "#ff7c89"))
            ok,msg=freellm.health(); self.free_status.setText(("● Reachable - " if ok else "○ Offline - ")+msg); self.free_status.setStyleSheet("color:%s;" % ("#70e0a4" if ok else "#ff7c89"))
            self.bridge_url.setText(f"http://127.0.0.1:{settings['bridge_port']}/v1")

        def start_bridge(self)->None:
            settings["bridge_api_key"]=self.bridge_key.text().strip(); JsonStore.save(SETTINGS_FILE,settings)
            try:bridge.start(); self.main.toast("Provider bridge started"); self.refresh()
            except Exception as e:self.main.error(str(e))

        def test_bridge(self)->None:
            if not bridge.running:
                try:bridge.start()
                except Exception as e:return self.main.error(str(e))
            cfg=ProviderConfig(name="Bridge",base_url=self.bridge_url.text(),model=providers.get(bridge_state.active_name).model if providers.get(bridge_state.active_name) else "",api_key_secret="")
            self.main.set_busy(True,"Testing bridge..."); w=Worker(providers.test_provider,cfg,self.bridge_key.text())
            w.signals.result.connect(lambda r:self.main.toast(f"Bridge PASS ({r.get('latency_ms')} ms)")); w.signals.error.connect(lambda x:self.main.error(masked_error(x))); w.signals.finished.connect(lambda:self.main.set_busy(False)); self.main.start_worker(w)

        def copy_bridge(self)->None:
            QApplication.clipboard().setText(f"Base URL: {self.bridge_url.text()}\nAPI Key: {self.bridge_key.text()}\nModel: {providers.get(bridge_state.active_name).model if providers.get(bridge_state.active_name) else ''}")
            self.main.toast("Bridge configuration copied")

        def pick_project(self)->None:
            p=QFileDialog.getExistingDirectory(self,"Select FreeLLMAPI project")
            if p:self.project.setText(p)

        def save_free(self)->None:
            settings.update({"freellm_project_dir":self.project.text().strip(),"freellm_start_command":self.command.text().strip(),"freellm_base_url":self.free_base.text().strip(),"freellm_model":self.free_model.text().strip()}); JsonStore.save(SETTINGS_FILE,settings); SECRETS.set("freellm_api_key",self.free_key.text().strip()); self.main.toast("FreeLLMAPI settings saved")

        def start_free(self)->None:
            try:self.save_free(); freellm.start(self.project.text(),self.command.text()); self.main.toast("FreeLLMAPI process started"); QTimer.singleShot(2000,self.refresh)
            except Exception as e:self.main.error(str(e))

    class DiagnosticsPage(QWidget):
        def __init__(self, main:"MainWindow"):
            super().__init__(); self.main=main
            l=QVBoxLayout(self); l.setContentsMargins(24,22,24,24); l.setSpacing(12)
            l.addWidget(title_block("Diagnostics", "Run checks from the Python environment all the way to the active LLM route."))
            self.table=QTableWidget(0,3); self.table.setHorizontalHeaderLabels(["Check","Status","Detail"]); self.table.horizontalHeader().setSectionResizeMode(0,QHeaderView.ResizeMode.ResizeToContents); self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.ResizeToContents); self.table.horizontalHeader().setSectionResizeMode(2,QHeaderView.ResizeMode.Stretch); l.addWidget(self.table,1)
            run=QPushButton("Run full system test"); run.setObjectName("Primary"); run.clicked.connect(self.run_all); l.addWidget(run,0,Qt.AlignLeft)

        def add_row(self,name:str,ok:bool,detail:str)->None:
            r=self.table.rowCount(); self.table.insertRow(r); self.table.setItem(r,0,QTableWidgetItem(name)); st=QTableWidgetItem("PASS" if ok else "FAIL"); st.setForeground(Qt.GlobalColor.green if ok else Qt.GlobalColor.red); self.table.setItem(r,1,st); self.table.setItem(r,2,QTableWidgetItem(detail[:1000]))

        def checks(self)->List[Tuple[str,bool,str]]:
            out=[]; ok,msg=check_python(); out.append(("Python",ok,msg)); ok,msg=check_requests(); out.append(("HTTP client",ok,msg));
            server=local.find_server(); out.append(("llama.cpp runtime",server is not None,str(server) if server else "Not installed")); model=local.find_model(); out.append(("Local model file",model is not None,str(model) if model else "Not downloaded"));
            lrun=local.is_running(); out.append(("Local API",lrun,f"127.0.0.1:{settings['local_port']}"));
            out.append(("Provider bridge",bridge.running,f"127.0.0.1:{settings['bridge_port']}"));
            ok,msg=freellm.health(); out.append(("FreeLLMAPI",ok,msg));
            cfg=providers.get(bridge_state.active_name)
            if cfg:
                try:r=providers.test_provider(cfg); out.append((f"Active provider: {cfg.name}",bool(r.get('chat_ok')),f"{r.get('latency_ms')} ms | {r.get('message','')}"))
                except Exception as e:out.append((f"Active provider: {cfg.name}",False,str(e)))
            return out

        def run_all(self)->None:
            self.table.setRowCount(0); self.main.set_busy(True,"Running diagnostics..."); w=Worker(self.checks); w.signals.result.connect(lambda rows:[self.add_row(*row) for row in rows]); w.signals.error.connect(lambda x:self.main.error(masked_error(x))); w.signals.finished.connect(lambda:self.main.set_busy(False)); self.main.start_worker(w)

    class LogsPage(QWidget):
        def __init__(self,main:"MainWindow"):
            super().__init__(); self.main=main
            l=QVBoxLayout(self); l.setContentsMargins(24,22,24,24); l.setSpacing(10); l.addWidget(title_block("Logs","Live application, local runtime and FreeLLMAPI process output.")); self.box=QPlainTextEdit(); self.box.setReadOnly(True); l.addWidget(self.box,1); clear=QPushButton("Clear view"); clear.clicked.connect(self.box.clear); l.addWidget(clear,0,Qt.AlignLeft)
        def append(self,text:str)->None:
            self.box.appendPlainText(text); sb=self.box.verticalScrollBar(); sb.setValue(sb.maximum())

    class SettingsPage(QWidget):
        def __init__(self,main:"MainWindow"):
            super().__init__(); self.main=main
            l=QVBoxLayout(self); l.setContentsMargins(24,22,24,24); l.setSpacing(12); l.addWidget(title_block("Settings","Ports, bridge credentials, VPN/proxy routing and application data location."))
            c=card(); f=QFormLayout(c); f.setContentsMargins(16,16,16,16)
            self.bridge_port=QSpinBox(); self.bridge_port.setRange(1024,65535); self.bridge_port.setValue(int(settings["bridge_port"])); self.bridge_key=QLineEdit(str(settings["bridge_api_key"])); self.root=QLineEdit(str(PATHS.root)); self.root.setReadOnly(True)
            self.proxy_mode=QComboBox(); self.proxy_mode.addItem("Auto - Windows/VPN recommended", "auto"); self.proxy_mode.addItem("System / environment proxy", "system"); self.proxy_mode.addItem("Direct / VPN tunnel", "direct"); self.proxy_mode.addItem("Manual proxy", "manual")
            wanted=str(settings.get("network_proxy_mode") or "auto"); idx=self.proxy_mode.findData(wanted); self.proxy_mode.setCurrentIndex(max(0,idx))
            self.proxy_url=QLineEdit(str(settings.get("network_proxy_url") or "")); self.proxy_url.setPlaceholderText("Optional, e.g. http://127.0.0.1:10809 or socks5h://127.0.0.1:10808")
            detected=", ".join(providers.http._system_proxy_urls()) or "No Windows/system proxy detected (TUN VPN can still work directly)"
            self.proxy_detected=QLabel(detected); self.proxy_detected.setWordWrap(True); self.proxy_detected.setObjectName("Muted")
            save=QPushButton("Save settings"); save.clicked.connect(self.save)
            f.addRow("Bridge port",self.bridge_port); f.addRow("Bridge API key",self.bridge_key); f.addRow("Network mode",self.proxy_mode); f.addRow("Manual proxy",self.proxy_url); f.addRow("Detected route",self.proxy_detected); f.addRow("App data",self.root); f.addRow("",save); l.addWidget(c)
            warning=QLabel("Auto mode keeps localhost direct, honors Windows/environment proxies, supports TUN VPNs, and can detect common local HTTP/SOCKS VPN ports. API keys stay only in your local app-data folder and are never committed to the project."); warning.setWordWrap(True); warning.setObjectName("Muted"); l.addWidget(warning); l.addStretch(1)
        def save(self)->None:
            new_port=self.bridge_port.value(); new_key=self.bridge_key.text().strip()
            bridge_changed=(new_port!=int(settings.get("bridge_port",8899)) or new_key!=str(settings.get("bridge_api_key") or ""))
            if bridge.running and bridge_changed:
                return self.main.error("Stop the bridge before changing its port or bridge API key. Network/VPN settings can be changed while it is running.")
            settings["bridge_port"]=new_port; settings["bridge_api_key"]=new_key; settings["network_proxy_mode"]=str(self.proxy_mode.currentData() or "auto"); settings["network_proxy_url"]=self.proxy_url.text().strip(); JsonStore.save(SETTINGS_FILE,settings)
            with providers.http._lock: providers.http._route_cache.clear()
            self.main.toast("Settings saved; network routes will be re-detected")

    class MainWindow(QMainWindow):
        def __init__(self):
            super().__init__(); self.pool=QThreadPool.globalInstance(); self._active_workers: set[Any] = set(); self._closing = False; self.setWindowTitle(f"{APP_NAME} {APP_VERSION}"); self.resize(1180,760); self.setMinimumSize(980,650)
            root=QWidget(); root.setObjectName("Root"); self.setCentralWidget(root); outer=QHBoxLayout(root); outer.setContentsMargins(0,0,0,0); outer.setSpacing(0)
            side=QFrame(); side.setObjectName("Sidebar"); side.setFixedWidth(210); sl=QVBoxLayout(side); sl.setContentsMargins(10,10,10,12); sl.setSpacing(4); brand=QLabel("◈ FreeLLM Studio"); brand.setObjectName("Brand"); sl.addWidget(brand)
            ver=QLabel(f"University Edition  •  v{APP_VERSION}"); ver.setObjectName("Muted"); ver.setContentsMargins(10,0,0,12); sl.addWidget(ver)
            self.stack=QStackedWidget();
            self.pages=[DashboardPage(self),ChatPage(self),LocalPage(self),ProvidersPage(self),GatewayPage(self),DiagnosticsPage(self),LogsPage(self),SettingsPage(self)]
            for p in self.pages:self.stack.addWidget(p)
            labels=["Overview","Chat","Local Models","API Providers","Gateway / Cline","Diagnostics","Logs","Settings"]
            self.nav=[]; group=QButtonGroup(self); group.setExclusive(True)
            for i,text in enumerate(labels):
                b=QPushButton(text); b.setObjectName("Nav"); b.setCheckable(True); b.clicked.connect(lambda checked=False,x=i:self.show_page(x)); group.addButton(b); sl.addWidget(b); self.nav.append(b)
            sl.addStretch(1)
            footer=QLabel("OpenAI-compatible bridge\nLocal-first • No Docker required"); footer.setObjectName("Muted"); footer.setWordWrap(True); footer.setContentsMargins(10,8,6,4); sl.addWidget(footer)
            outer.addWidget(side); content=QVBoxLayout(); content.setContentsMargins(0,0,0,0); self.busy=QLabel(""); self.busy.setStyleSheet("background:#161d2a;color:#aeb9cc;padding:7px 14px;border-bottom:1px solid #252e40;"); self.busy.setVisible(False); content.addWidget(self.busy); content.addWidget(self.stack,1); cw=QWidget(); cw.setLayout(content); outer.addWidget(cw,1)
            self.nav[0].setChecked(True); self.show_page(0)
            self.timer=QTimer(self); self.timer.timeout.connect(self.tick); self.timer.start(700)
            try:bridge.start()
            except Exception as e:logger.warning("Bridge auto-start failed: %s",e)

        def show_page(self,index:int)->None:
            self.stack.setCurrentIndex(index)
            if 0<=index<len(self.nav):self.nav[index].setChecked(True)
            if index==0:self.pages[0].refresh()
            if index==2:self.pages[2].refresh()
            if index==4:self.pages[4].refresh()

        def tick(self)->None:
            logs:LogsPage=self.pages[6]  # type: ignore
            for _ in range(200):
                try:msg=LOG_QUEUE.get_nowait()
                except queue.Empty:break
                logs.append(msg)
            if self.stack.currentIndex()==0:self.pages[0].refresh()  # type: ignore

        def toast(self,text:str)->None:
            self.statusBar().showMessage(text,5000); logger.info(text)

        def error(self,text:str)->None:
            logger.error(text); QMessageBox.critical(self,"Error",text[:3500])

        def set_busy(self,busy:bool,text:str="Working...")->None:
            self.busy.setText(text); self.busy.setVisible(busy)

        def start_worker(self, worker: Any) -> None:
            """Start a QRunnable while retaining a strong reference until all queued signals land."""
            self._active_workers.add(worker)
            def release_worker() -> None:
                # Run release on the GUI event loop after other finished handlers.
                QTimer.singleShot(0, lambda w=worker: self._active_workers.discard(w))
            worker.signals.finished.connect(release_worker)
            self.pool.start(worker)

        def closeEvent(self,event:QCloseEvent)->None:
            self._closing = True
            try:
                bridge.stop(); local.stop(); freellm.stop()
                # Do not tear Qt down while a provider/network callback is still in flight.
                self.pool.waitForDone(3000)
            finally:
                event.accept()

    def html_escape(text: str) -> str:
        return text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;").replace("'","&#39;").replace("\n","<br>")

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME); app.setOrganizationName(APP_ORG); app.setStyleSheet(STYLE)
    app.setFont(QFont("Segoe UI",10))

    # Never let a normal Python exception in a Qt callback terminate the GUI silently.
    def gui_exception_hook(exc_type: Any, exc_value: Any, exc_tb: Any) -> None:
        detail = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
        logger.error("Unhandled GUI exception:\n%s", detail)
        try:
            QMessageBox.critical(app.activeWindow(), "Unexpected error", friendly_error(exc_value))
        except Exception:
            pass

    sys.excepthook = gui_exception_hook

    def thread_exception_hook(args: Any) -> None:
        detail = "".join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))
        logger.error("Unhandled background-thread exception (%s):\n%s", getattr(args.thread, "name", "thread"), detail)

    if hasattr(threading, "excepthook"):
        threading.excepthook = thread_exception_hook  # type: ignore[assignment]

    win=MainWindow(); win.show()
    return app.exec()


# -----------------------------
# CLI
# -----------------------------


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--self-test", action="store_true", help="Run network-free core self-test and exit")
    parser.add_argument("--version", action="store_true", help="Show version and exit")
    args = parser.parse_args(argv)
    if args.version:
        print(APP_VERSION); return 0
    if args.self_test:
        return run_core_self_test()
    return launch_gui()


if __name__ == "__main__":
    raise SystemExit(main())
