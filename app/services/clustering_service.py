from datetime import datetime, timezone
import numpy as np
from sklearn.cluster import DBSCAN
from flask import current_app
from app import db
from app.models.report import Report
from app.models.issue import Issue
from app.models.issue_report import IssueReport
from app.models.audit import IssueStatusHistory
from app.models.category import IssueCategory
from geoalchemy2.elements import WKTElement
from app.services.priority_service import recalculate_issue_priority
from app.services.setting_service import get_setting


def _make_point(lat, lon):
    return WKTElement(f"POINT({lon} {lat})", srid=4326)


def _issue_for_report(report):
    link = IssueReport.query.filter_by(report_id=report.id).first()
    return link.issue if link else None


def _new_issue_from_report(report):
    issue = Issue(
        issue_code="TEMP",
        category_id=report.category_id,
        description=report.description,
        latitude=report.latitude,
        longitude=report.longitude,
        location_geometry=_make_point(report.latitude, report.longitude),
        severity=report.self_reported_severity,
        severity_source="CITIZEN",
        report_count=1,
        status="REPORTED",
    )
    db.session.add(issue)
    db.session.flush()
    issue.issue_code = f"CIVIC-{issue.id:05d}"
    db.session.add(IssueReport(issue_id=issue.id, report_id=report.id, link_method="AUTOMATIC_CLUSTER"))
    db.session.add(IssueStatusHistory(issue_id=issue.id, old_status=None, new_status="REPORTED", changed_by=report.user_id, remarks="Issue candidate created from citizen report.") )
    db.session.flush()
    recalculate_issue_priority(issue)
    return issue


def cluster_all_reports():
    reports = Report.query.order_by(Report.id.asc()).all()
    grouped = {}
    for report in reports:
        grouped.setdefault(report.category_id, []).append(report)

    cluster_results = []
    eps_m = get_setting("DBSCAN_EPS_METERS", current_app.config["DBSCAN_EPS_METERS"], float)
    min_samples = get_setting("DBSCAN_MIN_SAMPLES", current_app.config["DBSCAN_MIN_SAMPLES"], int)
    eps_rad = eps_m / 6371000.0

    for category_id, items in grouped.items():
        if len(items) == 1:
            labels = np.array([0])
        else:
            radians = np.radians([[r.latitude, r.longitude] for r in items])
            model = DBSCAN(eps=eps_rad, min_samples=min_samples, metric="haversine")
            labels = model.fit_predict(radians)

        clusters = {}
        for report, label in zip(items, labels):
            clusters.setdefault(int(label), []).append(report)

        for label, cluster_reports in clusters.items():
            if label == -1:
                for r in cluster_reports:
                    if not _issue_for_report(r):
                        _new_issue_from_report(r)
                continue
            existing_issues = {_issue_for_report(r).id for r in cluster_reports if _issue_for_report(r)}
            if existing_issues:
                issue = Issue.query.get(sorted(existing_issues)[0])
                # If more than one issue exists in the cluster, consolidate them into the chosen issue.
                for report in cluster_reports:
                    linked_issue = _issue_for_report(report)
                    if not linked_issue:
                        db.session.add(IssueReport(issue_id=issue.id, report_id=report.id, link_method="AUTOMATIC_CLUSTER"))
                    elif linked_issue.id != issue.id:
                        # Re-point the IssueReport row to the canonical issue
                        ir_link = IssueReport.query.filter_by(report_id=report.id).first()
                        if ir_link:
                            ir_link.issue_id = issue.id
                            ir_link.link_method = "AUTOMATIC_CLUSTER"
                issue.description = max((r.description for r in cluster_reports), key=len)
                issue.latitude = sum(r.latitude for r in cluster_reports) / len(cluster_reports)
                issue.longitude = sum(r.longitude for r in cluster_reports) / len(cluster_reports)
                issue.location_geometry = _make_point(issue.latitude, issue.longitude)
            else:
                issue = _new_issue_from_report(cluster_reports[0])
                for report in cluster_reports[1:]:
                    db.session.add(IssueReport(issue_id=issue.id, report_id=report.id, link_method="AUTOMATIC_CLUSTER"))
            issue = db.session.merge(issue)
            db.session.flush()
            cluster_results.append({"issue_id": issue.id, "report_count": len(cluster_reports), "cluster_label": label, "category_id": category_id})

    db.session.flush()
    for issue in Issue.query.all():
        issue.report_count = IssueReport.query.filter_by(issue_id=issue.id).count()
        if issue.report_count == 0:
            db.session.delete(issue)
        else:
            recalculate_issue_priority(issue)
    db.session.commit()
    return cluster_results
