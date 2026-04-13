from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.domain import Report
from app.schemas.report import ReportOut

router = APIRouter()


@router.get("/{report_id}", response_model=ReportOut)
async def get_report(report_id: str, session: AsyncSession = Depends(get_session)) -> Report:
    report = await session.get(Report, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "report not found")
    return report


@router.get("/{report_id}/markdown", response_class=PlainTextResponse)
async def get_report_markdown(
    report_id: str, session: AsyncSession = Depends(get_session)
) -> str:
    report = await session.get(Report, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "report not found")
    return report.markdown or ""


@router.get("/{report_id}/html", response_class=HTMLResponse)
async def get_report_html(
    report_id: str, session: AsyncSession = Depends(get_session)
) -> str:
    report = await session.get(Report, report_id)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "report not found")
    return report.html or "<html><body><p>Report not ready</p></body></html>"
