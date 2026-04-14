"""Fork-based simulator using Foundry `forge test --fork-url`."""
from __future__ import annotations

import ipaddress
import socket
import tempfile
import urllib.parse
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.core.sandbox import SandboxError, run_sandboxed
from app.schemas.enums import SimulationStatus, VulnerabilityType
from app.simulators.base import BaseSimulator, template_for

# Ports commonly used by Ethereum RPC endpoints
_ALLOWED_RPC_PORTS = {80, 443, 8545, 8546, 9545}


def _is_safe_rpc_url(url: str) -> bool:
    """Return True only if the URL resolves to a public (non-internal) address.

    Guards against SSRF: rejects loopback, private, link-local, multicast,
    and unspecified addresses so `forge` cannot be weaponised to probe the
    internal network or cloud metadata endpoints.
    """
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        host = parsed.hostname
        if not host:
            return False
        port = parsed.port
        if port is not None and port not in _ALLOWED_RPC_PORTS:
            return False
        ip_str = socket.gethostbyname(host)
        ip = ipaddress.ip_address(ip_str)
        return not (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_unspecified
        )
    except (socket.gaierror, ValueError, OSError):
        return False


class ForkSimulator(BaseSimulator):
    def __init__(self, binary: str | None = None, timeout: int | None = None) -> None:
        settings = get_settings()
        self.binary = binary or settings.forge_bin
        self.timeout = timeout or settings.simulation_timeout_s

    def run(
        self,
        *,
        template: VulnerabilityType,
        fork_rpc_url: str | None = None,
        fork_block: int | None = None,
        poc_code: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        if not fork_rpc_url:
            return {
                "status": SimulationStatus.FAILED,
                "output": "fork_rpc_url is required",
                "trace": None,
            }
        if not _is_safe_rpc_url(fork_rpc_url):
            return {
                "status": SimulationStatus.FAILED,
                "output": "fork_rpc_url is not allowed: must be a public http(s) Ethereum RPC endpoint",
                "trace": None,
            }

        test_code = poc_code if poc_code else template_for(template)
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "test").mkdir(parents=True, exist_ok=True)
            (root / "src").mkdir(parents=True, exist_ok=True)
            (root / "test" / "Exploit.t.sol").write_text(test_code, encoding="utf-8")
            (root / "foundry.toml").write_text("[profile.default]\nsrc='src'\ntest='test'\n", encoding="utf-8")

            cmd = [self.binary, "test", "--fork-url", fork_rpc_url, "-vvv"]
            if fork_block is not None:
                cmd.extend(["--fork-block-number", str(fork_block)])

            try:
                result = run_sandboxed(cmd, cwd=str(root), timeout=self.timeout)
            except SandboxError as exc:
                return {
                    "status": SimulationStatus.FAILED,
                    "output": f"forge not available: {exc}",
                    "trace": None,
                }

            if result.timed_out:
                return {
                    "status": SimulationStatus.TIMED_OUT,
                    "output": result.stdout + result.stderr,
                    "trace": None,
                }

            status = SimulationStatus.SUCCEEDED if result.returncode == 0 else SimulationStatus.FAILED
            return {"status": status, "output": result.stdout, "trace": result.stderr}
