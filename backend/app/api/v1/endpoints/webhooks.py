"""GitHub webhook receiver — auto-triggers analysis on .sol file changes."""
from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.session import get_session
from app.models.domain import Contract, Job
from app.schemas.enums import ContractLanguage, JobStatus, ToolName
from app.workers.dispatcher import dispatch_job

router = APIRouter()
logger = logging.getLogger(__name__)


def _verify_signature(body: bytes, signature: str | None) -> None:
    if not settings.github_webhook_secret:
        return  # secret not configured → skip verification
    if not signature or not signature.startswith("sha256="):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing or invalid signature")
    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(), body, hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "signature mismatch")


@router.post("/github", status_code=status.HTTP_200_OK)
async def github_webhook(
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    body = await request.body()
    _verify_signature(body, x_hub_signature_256)

    payload = await request.json()
    queued = 0

    if x_github_event not in ("push", "pull_request"):
        return {"queued": 0, "event": x_github_event}

    # Collect changed .sol files
    sol_files: list[tuple[str, str]] = []  # (filename, raw_url)
    if x_github_event == "push":
        for commit in payload.get("commits", []):
            for fname in commit.get("added", []) + commit.get("modified", []):
                if fname.endswith(".sol"):
                    repo = payload.get("repository", {})
                    raw_url = (
                        f"https://raw.githubusercontent.com/"
                        f"{repo.get('full_name','unknown')}/HEAD/{fname}"
                    )
                    sol_files.append((fname, raw_url))
    elif x_github_event == "pull_request":
        if payload.get("action") in ("opened", "synchronize"):
            repo_full = payload.get("repository", {}).get("full_name", "unknown")
            for fname in payload.get("files_changed", []):
                if isinstance(fname, str) and fname.endswith(".sol"):
                    raw_url = f"https://raw.githubusercontent.com/{repo_full}/HEAD/{fname}"
                    sol_files.append((fname, raw_url))

    for fname, raw_url in sol_files:
        contract = Contract(
            name=fname,
            language=ContractLanguage.SOLIDITY,
            source=f"// auto-queued from GitHub: {raw_url}",
        )
        session.add(contract)
        await session.flush()
        job = Job(
            contract_id=contract.id,
            status=JobStatus.PENDING,
            tools=[ToolName.SLITHER.value, ToolName.MYTHRIL.value],
            progress=0,
        )
        session.add(job)
        await session.flush()
        dispatch_job(job.id, contract.id, [ToolName.SLITHER.value, ToolName.MYTHRIL.value])
        queued += 1

    await session.commit()
    logger.info("github_webhook queued %d jobs", queued)
    return {"queued": queued}
