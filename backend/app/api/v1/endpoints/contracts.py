from __future__ import annotations

import json
from pathlib import PurePosixPath

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_cached_job_id
from app.db.session import get_session
from app.models.domain import Contract, Job
from app.schemas.contract import ContractCreate, ContractOut
from app.schemas.enums import ContractLanguage, JobStatus, ToolName
from app.schemas.job import JobCreate, JobOut
from app.workers.dispatcher import dispatch_job

router = APIRouter()

_MAX_FILE_BYTES = 10 * 1024 * 1024   # 10 MB per file
_MAX_TOTAL_BYTES = 50 * 1024 * 1024  # 50 MB total


def _sanitize_path(raw: str) -> str:
    """Strip unsafe path components and return a clean relative path."""
    parts = [p for p in PurePosixPath(raw).parts if p not in ("", ".", "..")]
    if not parts:
        raise ValueError(f"empty path after sanitisation: {raw!r}")
    clean = str(PurePosixPath(*parts))
    if clean.startswith("/"):
        raise ValueError(f"absolute path rejected: {raw!r}")
    return clean


@router.post("/upload", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
async def upload_contract_files(
    name: str = Form(...),
    language: ContractLanguage = Form(ContractLanguage.SOLIDITY),
    compiler_version: str | None = Form(None),
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_session),
) -> Contract:
    """Create a contract from one or more uploaded .sol files."""
    if not files:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "at least one file required")

    file_map: dict[str, str] = {}
    total_bytes = 0

    for upload in files:
        filename = upload.filename or ""
        if not filename.endswith(".sol"):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"only .sol files are accepted, got: {filename!r}",
            )
        try:
            rel_path = _sanitize_path(filename)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

        if rel_path in file_map:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"duplicate file path: {rel_path!r}",
            )

        content_bytes = await upload.read()
        if len(content_bytes) == 0:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"empty file rejected: {rel_path!r}",
            )
        if len(content_bytes) > _MAX_FILE_BYTES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"file too large ({len(content_bytes)} bytes): {rel_path!r}",
            )
        total_bytes += len(content_bytes)
        if total_bytes > _MAX_TOTAL_BYTES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "total upload size exceeds 50 MB limit",
            )

        try:
            file_map[rel_path] = content_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"file is not valid UTF-8: {rel_path!r}",
            ) from exc

    # Use first alphabetical file as the primary source (backwards compat)
    primary_source = file_map[sorted(file_map.keys())[0]]

    contract = Contract(
        name=name,
        language=language,
        source=primary_source,
        compiler_version=compiler_version,
        project_files=json.dumps(file_map),
    )
    session.add(contract)
    await session.commit()
    await session.refresh(contract)
    return contract


@router.post("", response_model=ContractOut, status_code=status.HTTP_201_CREATED)
async def create_contract(
    payload: ContractCreate,
    session: AsyncSession = Depends(get_session),
) -> Contract:
    contract = Contract(
        name=payload.name,
        language=payload.language,
        source=payload.source,
        bytecode=payload.bytecode,
        compiler_version=payload.compiler_version,
    )
    session.add(contract)
    await session.commit()
    await session.refresh(contract)
    return contract


@router.get("", response_model=list[ContractOut])
async def list_contracts(session: AsyncSession = Depends(get_session)) -> list[Contract]:
    result = await session.execute(select(Contract).order_by(Contract.created_at.desc()))
    return list(result.scalars().all())


@router.get("/{contract_id}", response_model=ContractOut)
async def get_contract(contract_id: str, session: AsyncSession = Depends(get_session)) -> Contract:
    contract = await session.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "contract not found")
    return contract


@router.get("/{contract_id}/jobs", response_model=list[JobOut])
async def list_contract_jobs(contract_id: str, session: AsyncSession = Depends(get_session)) -> list[Job]:
    contract = await session.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "contract not found")
    result = await session.execute(
        select(Job).where(Job.contract_id == contract_id).order_by(Job.created_at.desc())
    )
    return list(result.scalars().all())


@router.delete("/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contract(contract_id: str, session: AsyncSession = Depends(get_session)) -> None:
    """Delete a contract and all associated jobs, findings, reports, and simulations."""
    contract = await session.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "contract not found")
    await session.delete(contract)
    await session.commit()


@router.post("/{contract_id}/compile-check")
async def compile_check_contract(
    contract_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Try to compile the contract's project files and return missing imports."""
    contract = await session.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "contract not found")
    if not contract.project_files:
        return {"success": True, "missing": [], "errors": []}

    from app.core.compile_check import check_compilation  # local import — heavy deps

    files: dict[str, str] = json.loads(contract.project_files)
    result = check_compilation(files)

    # Auto-resolve missing imports by basename match within existing project_files.
    # e.g. missing "@universal/interfaces/ISemver.sol" → find existing "universal/interfaces/ISemver.sol"
    # or "ISemver.sol" and alias it at the expected import path.
    if result.get("missing"):
        basename_map: dict[str, str] = {}
        for path in files:
            basename_map[path.rsplit("/", 1)[-1]] = path  # last one wins for dupes

        auto_resolved: dict[str, str] = {}
        for missing_path in result["missing"]:
            if missing_path in files:
                continue
            basename = missing_path.rsplit("/", 1)[-1]
            if basename in basename_map:
                auto_resolved[missing_path] = files[basename_map[basename]]

        if auto_resolved:
            files.update(auto_resolved)
            contract.project_files = json.dumps(files)
            await session.commit()
            result = check_compilation(files)

    return result


@router.patch("/{contract_id}/files", response_model=ContractOut)
async def add_contract_files(
    contract_id: str,
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_session),
) -> Contract:
    """Merge additional files into an existing contract's project_files."""
    contract = await session.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "contract not found")

    existing: dict[str, str] = json.loads(contract.project_files) if contract.project_files else {}
    total_bytes = sum(len(v.encode()) for v in existing.values())

    for upload in files:
        filename = upload.filename or ""
        if not filename.endswith(".sol"):
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"only .sol files are accepted, got: {filename!r}",
            )
        try:
            rel_path = _sanitize_path(filename)
        except ValueError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc

        content_bytes = await upload.read()
        if len(content_bytes) > _MAX_FILE_BYTES:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"file too large: {rel_path!r}",
            )
        total_bytes += len(content_bytes)
        if total_bytes > _MAX_TOTAL_BYTES:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "total size exceeds 50 MB")

        try:
            existing[rel_path] = content_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"file is not valid UTF-8: {rel_path!r}",
            ) from exc

        # Remove stale root-level key with the same basename when a scoped path
        # is added (e.g. adding "@universal/interfaces/ISemver.sol" cleans up
        # any previously uploaded bare "ISemver.sol").
        if "/" in rel_path:
            basename = rel_path.rsplit("/", 1)[-1]
            existing.pop(basename, None)

    contract.project_files = json.dumps(existing)
    await session.commit()
    await session.refresh(contract)
    return contract


@router.post("/{contract_id}/analyze", response_model=JobOut, status_code=status.HTTP_202_ACCEPTED)
async def analyze_contract(
    contract_id: str,
    response: Response,
    payload: JobCreate | None = None,
    session: AsyncSession = Depends(get_session),
) -> Job:
    contract = await session.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "contract not found")

    tools = payload.tools if payload else [ToolName.SLITHER, ToolName.MYTHRIL]
    tool_values = [t.value for t in tools]

    if contract.bytecode:
        cached_id = await get_cached_job_id(contract.bytecode, tool_values)
        if cached_id is not None:
            cached_job = await session.get(Job, cached_id)
            # Only serve completed jobs from cache; stale pending/failed entries are ignored
            if cached_job is not None and cached_job.status == JobStatus.COMPLETED:
                response.headers["x-cache"] = "HIT"
                return cached_job

    entry_files = payload.entry_files if payload else None
    job = Job(
        contract_id=contract.id,
        status=JobStatus.PENDING,
        tools=tool_values,
        entry_files=entry_files,
        progress=0,
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    dispatch_job(job.id, contract.id, tool_values, entry_files=entry_files)
    # Cache write is deferred to the worker task after successful completion
    return job
