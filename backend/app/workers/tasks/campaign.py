"""Attack campaign task: AI-generate full exploit test suite + run forge test."""
from __future__ import annotations

import asyncio
import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config import get_settings
from app.core.campaign_generator import generate_campaign
from app.core.logging import get_logger
from app.core.sandbox import SandboxError, run_sandboxed
from app.db.session import session_scope
from app.models.domain import AttackCampaign, Contract, Finding, Job
from app.schemas.enums import CampaignStatus
from app.schemas.finding import FindingOut
from app.workers.celery_app import celery_app

log = get_logger(__name__)


def _parse_forge_results(output: str) -> dict[str, str]:
    """Parse forge test -vvv output into {test_name: 'pass'|'fail'}."""
    results: dict[str, str] = {}
    for line in output.splitlines():
        line = line.strip()
        if line.startswith("[PASS]"):
            m = re.search(r"\[PASS\]\s+(\w+)\(\)", line)
            if m:
                results[m.group(1)] = "pass"
        elif line.startswith("[FAIL]"):
            m = re.search(r"\[FAIL\]\s+(\w+)\(\)", line)
            if m:
                results[m.group(1)] = "fail"
    return results


async def _run(campaign_id: str) -> None:
    settings = get_settings()

    # ── Phase 1: Load campaign + job context ──────────────────────────────
    async with session_scope() as session:
        campaign = await session.get(AttackCampaign, campaign_id)
        if campaign is None:
            log.error("campaign_missing", campaign_id=campaign_id)
            return
        campaign.status = CampaignStatus.PLANNING
        job_id = campaign.job_id

    contract_source: str | None = None
    project_files: dict[str, str] | None = None
    contract_name = "Unknown"
    findings: list[FindingOut] = []

    async with session_scope() as session:
        job = await session.get(Job, job_id)
        contract = await session.get(Contract, job.contract_id)
        result = await session.execute(
            select(Finding)
            .where(Finding.job_id == job_id)
            .options(selectinload(Finding.evidences))
        )
        findings_db = list(result.scalars().all())
        # Validate while session is open to avoid DetachedInstanceError on evidences
        findings = [FindingOut.model_validate(f) for f in findings_db]
        if contract:
            contract_source = contract.source
            contract_name = contract.name
            if contract.project_files:
                try:
                    project_files = json.loads(contract.project_files)
                except (json.JSONDecodeError, TypeError):
                    pass

    # ── Phase 2: AI generates attack plan + test suite ────────────────────
    try:
        attack_plan, test_code = await generate_campaign(
            job_id=job_id,
            contract_name=contract_name,
            contract_source=contract_source,
            project_files=project_files,
            findings=findings,
        )
    except Exception as exc:
        log.error("campaign_ai_failed", campaign_id=campaign_id, error=str(exc))
        async with session_scope() as session:
            campaign = await session.get(AttackCampaign, campaign_id)
            campaign.status = CampaignStatus.FAILED
            campaign.error = f"AI generation failed: {exc}"
            campaign.finished_at = datetime.now(tz=timezone.utc)
        return

    # Persist plan + code, transition to RUNNING
    async with session_scope() as session:
        campaign = await session.get(AttackCampaign, campaign_id)
        campaign.attack_plan = attack_plan
        campaign.test_code = test_code
        campaign.status = CampaignStatus.RUNNING

    if not test_code:
        async with session_scope() as session:
            campaign = await session.get(AttackCampaign, campaign_id)
            campaign.status = CampaignStatus.FAILED
            campaign.error = "AI returned no test code"
            campaign.finished_at = datetime.now(tz=timezone.utc)
        return

    # ── Phase 3: Set up Foundry project + run forge test ──────────────────
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "src").mkdir()
        (root / "test").mkdir()

        if project_files:
            for rel_path, content in project_files.items():
                dest = root / "src" / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(content, encoding="utf-8")
        elif contract_source:
            filename = contract_name if contract_name.endswith(".sol") else f"{contract_name}.sol"
            (root / "src" / filename).write_text(contract_source, encoding="utf-8")

        (root / "test" / "AttackCampaign.t.sol").write_text(test_code, encoding="utf-8")
        (root / "foundry.toml").write_text(
            "[profile.default]\nsrc = 'src'\ntest = 'test'\n",
            encoding="utf-8",
        )

        try:
            forge_result = run_sandboxed(
                [settings.forge_bin, "test", "-vvv"],
                cwd=str(root),
                timeout=settings.simulation_timeout_s,
            )
        except SandboxError as exc:
            async with session_scope() as session:
                campaign = await session.get(AttackCampaign, campaign_id)
                campaign.status = CampaignStatus.FAILED
                campaign.error = f"forge not available: {exc}"
                campaign.finished_at = datetime.now(tz=timezone.utc)
            return

    # ── Phase 4: Parse results and persist ────────────────────────────────
    parsed_results = _parse_forge_results(forge_result.stdout or "")

    if forge_result.timed_out:
        final_status = CampaignStatus.TIMED_OUT
    elif forge_result.returncode == 0:
        final_status = CampaignStatus.SUCCEEDED
    elif any(v == "pass" for v in parsed_results.values()):
        final_status = CampaignStatus.PARTIAL
    else:
        final_status = CampaignStatus.FAILED

    async with session_scope() as session:
        campaign = await session.get(AttackCampaign, campaign_id)
        campaign.status = final_status
        campaign.output = forge_result.stdout
        campaign.trace = forge_result.stderr
        campaign.results = parsed_results or None
        campaign.finished_at = datetime.now(tz=timezone.utc)

    log.info(
        "campaign_finished",
        campaign_id=campaign_id,
        status=final_status,
        tests=len(parsed_results),
    )


@celery_app.task(
    name="app.workers.tasks.campaign.run_attack_campaign",
    bind=True,
    max_retries=1,
    default_retry_delay=60,
)
def run_attack_campaign(self, campaign_id: str) -> None:  # type: ignore[override]
    try:
        asyncio.run(_run(campaign_id))
    except Exception as exc:
        log.error("campaign_task_failed", campaign_id=campaign_id, error=str(exc))
        raise self.retry(exc=exc)
