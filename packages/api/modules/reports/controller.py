from modules.reports.service import get_report_by_id


def handle_get_report(report_id: str):
    return get_report_by_id(report_id)
