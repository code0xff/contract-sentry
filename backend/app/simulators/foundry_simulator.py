"""Foundry (forge test) simulator."""
from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from app.config import get_settings
from app.core.sandbox import SandboxError, run_sandboxed
from app.schemas.enums import SimulationStatus, VulnerabilityType
from app.simulators.base import BaseSimulator, template_for


class FoundrySimulator(BaseSimulator):
    def __init__(self, binary: str | None = None, timeout: int | None = None) -> None:
        settings = get_settings()
        self.binary = binary or settings.forge_bin
        self.timeout = timeout or settings.simulation_timeout_s

    def run(self, *, template: VulnerabilityType, **kwargs: Any) -> dict[str, Any]:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "test").mkdir(parents=True, exist_ok=True)
            (root / "src").mkdir(parents=True, exist_ok=True)
            (root / "test" / "Exploit.t.sol").write_text(template_for(template), encoding="utf-8")
            (root / "foundry.toml").write_text("[profile.default]\nsrc='src'\ntest='test'\n", encoding="utf-8")

            try:
                result = run_sandboxed(
                    [self.binary, "test", "-vv"],
                    cwd=str(root),
                    timeout=self.timeout,
                )
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
            return {
                "status": status,
                "output": result.stdout,
                "trace": result.stderr,
            }
