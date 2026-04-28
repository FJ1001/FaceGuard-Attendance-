"""Minimal PDF report for analytics (fpdf2)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Dict


def build_analytics_pdf_summary(analytics_data: Dict[str, Any]) -> bytes:
    """Return PDF bytes with overview + key metrics (no charts)."""
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 14)
            self.cell(0, 10, "Attendance analytics report", ln=True)
            self.set_font("Helvetica", "", 9)
            self.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
            self.ln(4)

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "", 10)

    overview = analytics_data.get("overview") or {}
    na = "n/a"
    lines = [
        f"Total students: {overview.get('total_students', na)}",
        f"Present today: {overview.get('present_today', na)}",
        f"Absent today: {overview.get('absent_today', na)}",
        f"Attendance rate today (%): {overview.get('attendance_rate_today', na)}",
        f"Avg weekly rate (%): {overview.get('avg_weekly_rate', na)}",
        "",
        f"Daily trend rows: {len(analytics_data.get('daily_trends') or [])}",
        f"Student performance rows: {len(analytics_data.get('student_performance') or [])}",
        f"Course rows: {len(analytics_data.get('course_analytics') or [])}",
        f"Alerts: {len(analytics_data.get('alerts') or [])}",
    ]
    for line in lines:
        pdf.cell(0, 6, line or " ", ln=True)

    pdf.ln(6)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(
        0,
        5,
        "Charts stay in the web app; this PDF is a short text summary for archiving.",
        ln=True,
    )

    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1")
    return bytes(raw)


def build_live_tracking_pdf_summary(report_data: Dict[str, Any]) -> bytes:
    """Return a short PDF summary for the live tracking report."""
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 14)
            self.cell(0, 10, "Live tracking report", ln=True)
            self.set_font("Helvetica", "", 9)
            self.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
            self.ln(4)

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "", 10)

    summary = report_data.get("summary") or {}
    insights = report_data.get("insights") or []
    top_alerts = report_data.get("top_alerts") or []
    top_students = report_data.get("top_students") or []

    lines = [
        f"Report period (days): {report_data.get('period_days', 'n/a')}",
        f"Generated at: {report_data.get('generated_at', 'n/a')}",
        "",
        f"Total students: {summary.get('total_students', 'n/a')}",
        f"Present today: {summary.get('present_today', 'n/a')}",
        f"Absent today: {summary.get('absent_today', 'n/a')}",
        f"Attendance rate: {summary.get('attendance_rate', 'n/a')}%",
        f"Active alerts: {summary.get('active_alerts', 'n/a')}",
        f"Critical alerts: {summary.get('critical_alerts', 'n/a')}",
    ]

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for line in lines:
        pdf.cell(0, 6, line or " ", ln=True)

    if insights:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Key insights", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for insight in insights[:3]:
            pdf.multi_cell(0, 6, f"- {insight}", new_x="LMARGIN", new_y="NEXT")

    if top_alerts:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Top alerts", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for alert in top_alerts[:5]:
            pdf.multi_cell(
                0,
                6,
                f"- {alert.get('title', 'Alert')}: {alert.get('message', '')}",
                new_x="LMARGIN",
                new_y="NEXT",
            )

    if top_students:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Tracked students", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for student in top_students[:5]:
            pdf.multi_cell(
                0,
                6,
                f"- {student.get('name', 'Student')} ({student.get('roll_number', 'n/a')}): {student.get('status', 'n/a')}",
                new_x="LMARGIN",
                new_y="NEXT",
            )

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "This summary keeps the report short and practical for quick review.", ln=True)

    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1")
    return bytes(raw)


def build_focus_analysis_pdf_summary(analysis: Dict[str, Any]) -> bytes:
    """Return a short PDF summary for a focus / live score analysis."""
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 14)
            self.cell(0, 10, "Focus analysis report", ln=True)
            self.set_font("Helvetica", "", 9)
            self.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
            self.ln(4)

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "", 10)

    score = float(analysis.get("focus_score", 0.0))
    rolling = float(analysis.get("rolling_focus_score", score))
    status = analysis.get("rolling_status", analysis.get("status", "n/a"))
    sample_count = int(analysis.get("sample_count", 0))
    alerts = analysis.get("rolling_alerts") or analysis.get("alerts") or []
    components = analysis.get("components") or {}

    lines = [
        f"Live score: {score:.1f}",
        f"Rolling average: {rolling:.1f}",
        f"Status: {status}",
        f"Sample count: {sample_count}",
        "",
        f"Eyes: {components.get('eyes', 'n/a')}",
        f"Centering: {components.get('centering', 'n/a')}",
        f"Clarity: {components.get('clarity', 'n/a')}",
        f"Brightness: {components.get('brightness', 'n/a')}",
        f"Face size: {components.get('face_size', 'n/a')}",
    ]

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for line in lines:
        pdf.cell(0, 6, line or " ", ln=True)

    if alerts:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Alerts", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for alert in alerts[:5]:
            pdf.multi_cell(0, 6, f"- {alert}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "This report captures the current live focus analysis in a short printable format.", ln=True)

    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1")
    return bytes(raw)


def build_student_attendance_pdf_summary(report_data: Dict[str, Any]) -> bytes:
    """Return a short PDF summary for a single student's attendance analytics."""
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 14)
            self.cell(0, 10, "Student attendance report", ln=True)
            self.set_font("Helvetica", "", 9)
            self.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
            self.ln(4)

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "", 10)

    student = report_data.get("student_info") or {}
    lines = [
        f"Name: {student.get('name', 'n/a')}",
        f"Roll number: {student.get('roll_number', 'n/a')}",
        f"Course: {student.get('course', 'n/a')}",
        f"Period days: {report_data.get('period_days', 'n/a')}",
        f"Present days: {report_data.get('present_days', 'n/a')}",
        f"Absent days: {report_data.get('absent_days', 'n/a')}",
        f"Attendance rate: {report_data.get('attendance_rate', 'n/a')}%",
        f"Records captured: {len(report_data.get('records') or [])}",
        f"Time-in records: {report_data.get('has_time_in', 'n/a')}",
        f"Time-out records: {report_data.get('has_time_out', 'n/a')}",
    ]

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for line in lines:
        pdf.cell(0, 6, line, ln=True)

    records = report_data.get("records") or []
    if records:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Recent records", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for record in records[:10]:
            pdf.multi_cell(
                0,
                6,
                f"- {record.get('date', 'n/a')}: in {record.get('time_in', 'n/a')} | out {record.get('time_out', 'n/a')} | {record.get('status', 'n/a')}",
                new_x="LMARGIN",
                new_y="NEXT",
            )

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "This summary is intentionally short and practical for admin review.", ln=True)

    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1")
    return bytes(raw)


def build_student_focus_analytics_pdf_summary(
    *,
    student: Dict[str, Any],
    analytics: Dict[str, Any],
    sessions: list[Dict[str, Any]],
) -> bytes:
    """Return a short PDF summary for one student's saved focus sessions."""
    from fpdf import FPDF

    class PDF(FPDF):
        def header(self):
            self.set_font("Helvetica", "B", 14)
            self.cell(0, 10, "Student focus analytics report", ln=True)
            self.set_font("Helvetica", "", 9)
            self.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
            self.ln(4)

    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "", 10)

    lines = [
        f"Name: {student.get('name', 'n/a')}",
        f"Roll number: {student.get('roll_number', 'n/a')}",
        f"Course: {student.get('course', 'n/a')}",
        "",
        f"Total sessions: {analytics.get('total_sessions', 0)}",
        f"Average focus score: {analytics.get('avg_focus_score', 0)}",
        f"Average rolling score: {analytics.get('avg_rolling_score', 0)}",
        f"Total alerts: {analytics.get('total_alerts', 0)}",
        f"Latest status: {analytics.get('last_status', 'n/a')}",
    ]

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for line in lines:
        pdf.cell(0, 6, line or " ", ln=True)

    if sessions:
        pdf.ln(2)
        pdf.set_font("Helvetica", "B", 11)
        pdf.cell(0, 7, "Recent sessions", ln=True)
        pdf.set_font("Helvetica", "", 10)
        for session in sessions[:10]:
            pdf.multi_cell(
                0,
                6,
                f"- {session.get('created_at', 'n/a')}: avg {session.get('avg_focus_score', 0):.1f}, "
                f"rolling {session.get('avg_rolling_score', 0):.1f}, "
                f"status {session.get('final_status', 'n/a')}, alerts {session.get('alerts_count', 0)}",
                new_x="LMARGIN",
                new_y="NEXT",
            )

    pdf.ln(4)
    pdf.set_font("Helvetica", "I", 8)
    pdf.cell(0, 5, "Saved live sessions from Focus Monitor appear in this report.", ln=True)

    raw = pdf.output(dest="S")
    if isinstance(raw, str):
        return raw.encode("latin-1")
    return bytes(raw)
