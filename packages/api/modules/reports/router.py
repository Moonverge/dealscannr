from fastapi import APIRouter, HTTPException
from modules.reports.controller import handle_get_report

router = APIRouter()


@router.get("/reports/{report_id}")
def get_report(report_id: str):
    report = handle_get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report
