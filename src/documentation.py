from pathlib import Path
from typing import List, Dict
from docx import Document
from docx.shared import Pt

_current_doc = None


def start_documenting(documentation_path: Path, doc_name="BETHER.docx"):
    """Start a new Word document for documentation."""
    global _current_doc
    documentation_path.mkdir(parents=True, exist_ok=True)
    _current_doc = Document()
    _current_doc.add_heading("Traffic Simulation Documentation", level=0)
    print("Document started.")


def add_intersection_data_table(intersection, name: str = "Intersection"):
    """Add a table describing intersection info, including its name."""
    global _current_doc
    if _current_doc is None:
        raise RuntimeError(
            "Document not started. Call start_documenting() first.")

    _current_doc.add_heading(f"Intersection Data: {name}", level=1)
    table = _current_doc.add_table(rows=1, cols=4)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Approach Name"
    hdr_cells[1].text = "Number of Lanes"
    hdr_cells[2].text = "Saturation Flow/Lane"
    hdr_cells[3].text = "Saturation Flow Total"

    for app in intersection.approaches:
        row_cells = table.add_row().cells
        row_cells[0].text = app.name
        row_cells[1].text = str(app.num_lanes)
        row_cells[2].text = f"{getattr(app, 'saturation_flow_per_lane', 0):.1f}"
        row_cells[3].text = f"{getattr(app, 'saturation_flow_total', 0):.1f}"


def add_signal_plan_table(signal_plan: List, name: str = "Signal Plan"):
    """Add tables describing the signal plan per phase, including a name/title."""
    global _current_doc
    if _current_doc is None:
        raise RuntimeError(
            "Document not started. Call start_documenting() first.")

    _current_doc.add_heading(f"{name}", level=1)
    for idx, phase in enumerate(signal_plan, start=1):
        _current_doc.add_heading(f"Phase {idx}", level=2)
        _current_doc.add_paragraph(
            f"Green: {phase.green:.1f}s | Amber: {phase.amber:.1f}s | All Red: {phase.all_red:.1f}s | "
            f"Start: {phase.start:.1f}s | Duration: {phase.duration:.1f}s"
        )

        table = _current_doc.add_table(rows=1, cols=5)
        table.style = 'Table Grid'
        hdr_cells = table.rows[0].cells
        hdr_cells[0].text = "From Approach"
        hdr_cells[1].text = "Lane"
        hdr_cells[2].text = "To Approach"
        hdr_cells[3].text = "Movement Type"
        hdr_cells[4].text = "Average Flow (veh/h)"

        for mv in phase.movements:
            row_cells = table.add_row().cells
            row_cells[0].text = mv.from_approach.name
            row_cells[1].text = str(mv.lane_index)
            row_cells[2].text = mv.to_approach.name
            row_cells[3].text = mv.movement_type
            row_cells[4].text = f"{mv.average_flow:.1f}"


def add_report_table(report: Dict, name: str = "Simulation Report"):
    """Add a table summarizing the simulation statistics, with a report name."""
    global _current_doc
    if _current_doc is None:
        raise RuntimeError(
            "Document not started. Call start_documenting() first.")

    _current_doc.add_heading(f"{name}", level=1)
    table = _current_doc.add_table(rows=1, cols=2)
    table.style = 'Table Grid'
    hdr_cells = table.rows[0].cells
    hdr_cells[0].text = "Metric"
    hdr_cells[1].text = "Value"

    for key, value in report.items():
        row_cells = table.add_row().cells
        row_cells[0].text = key.replace('_', ' ').title()
        row_cells[1].text = f"{value:.2f}" if isinstance(
            value, float) else str(value)


def finish_documenting(documentation_path: Path, doc_name="Simulation_Report.docx"):
    """Save and close the document."""
    global _current_doc
    if _current_doc is None:
        raise RuntimeError(
            "Document not started. Call start_documenting() first.")

    doc_path = documentation_path / doc_name
    _current_doc.save(doc_path)
    _current_doc = None
    print(f"Document saved to: {doc_path}")
    return doc_path
