import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

from app import create_app, db
from app.models import IssueCategory, User, Report, Issue, IssueReport, AIDetection, DuplicateCandidate, IssueStatusHistory, IssueAssignment
from app.services.clustering_service import cluster_all_reports
from app.services.priority_service import recalculate_issue_priority
from app.services.ai_service import detect_report
from sqlalchemy import text
from geoalchemy2.elements import WKTElement

ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = ROOT / 'uploads' / 'demo'

DEMO_USERS = [
    ('Aarav Patil','aarav@example.com','9000000001'), ('Diya Shah','diya@example.com','9000000002'),
    ('Kabir Joshi','kabir@example.com','9000000003'), ('Anaya Kulkarni','anaya@example.com','9000000004'),
    ('Vivaan Deshmukh','vivaan@example.com','9000000005'), ('Ishita More','ishita@example.com','9000000006'),
    ('Aditya Jadhav','aditya@example.com','9000000007'), ('Myra Pawar','myra@example.com','9000000008'),
    ('Rohan Kale','rohan@example.com','9000000009'), ('Saanvi Bhosale','saanvi@example.com','9000000010'),
]

GROUPS = [
    # category, base_lat, base_lon, count, severity, location importance
    # 20 reports distributed across 8 physical issue clusters.
    ('Pothole', 18.52080, 73.85670, 10, 5, 5),
    ('Pothole', 18.52600, 73.86250, 2, 2, 1),
    ('Road Damage', 18.51360, 73.84720, 3, 3, 3),
    ('Road Damage', 18.51680, 73.85020, 1, 2, 2),
    ('Road Crack', 18.53200, 73.87100, 1, 4, 4),
    ('Road Crack', 18.54200, 73.88000, 1, 2, 2),
    ('Pothole', 18.50600, 73.83900, 1, 3, 2),
    ('Road Damage', 18.54800, 73.88900, 1, 3, 3),
]

def demo_image(path, label, idx):
    path.parent.mkdir(parents=True, exist_ok=True)
    img = Image.new('RGB', (900, 600), (230, 237, 243))
    draw = ImageDraw.Draw(img)
    draw.rectangle((70, 100, 830, 500), fill=(70, 75, 80))
    cx = 250 + (idx * 83) % 350
    cy = 310 + (idx * 47) % 90
    draw.ellipse((cx-75, cy-55, cx+75, cy+55), fill=(25,25,25))
    draw.text((90, 35), f'DEMO DATA · {label}', fill=(20,50,80))
    draw.text((90, 535), 'Synthetic academic image — not real municipal evidence', fill=(60,70,80))
    img.save(path, quality=90)


def main():
    if os.getenv("ALLOW_DEMO_SEED", "").lower() != "true":
        raise SystemExit("Set ALLOW_DEMO_SEED=true to seed and reset a local demo database.")
    app = create_app()
    with app.app_context():
        # Reset demo data but preserve schema/configuration.
        for model in [IssueStatusHistory, IssueAssignment, DuplicateCandidate, AIDetection, IssueReport, Issue, Report, User]:
            db.session.query(model).delete()
        db.session.commit()
        db.session.execute(text("ALTER SEQUENCE users_id_seq RESTART WITH 1"))
        db.session.execute(text("ALTER SEQUENCE reports_id_seq RESTART WITH 1"))
        db.session.execute(text("ALTER SEQUENCE issues_id_seq RESTART WITH 1"))
        db.session.execute(text("ALTER SEQUENCE issue_reports_id_seq RESTART WITH 1"))
        db.session.commit()

        admin = User(name='System Administrator', email='admin@smartcivic.local', mobile='9000000100', password_hash=None, role='ADMIN')
        db.session.add(admin)
        citizens=[]
        for name,email,mobile in DEMO_USERS:
            u=User(name=name,email=email,mobile=mobile,password_hash=None,role='CITIZEN')
            db.session.add(u); citizens.append(u)
        db.session.flush()

        cats={c.name:c for c in IssueCategory.query.filter(IssueCategory.active.is_(True)).all()}
        report_no=0
        now=datetime.now(timezone.utc)
        for group_idx,(cat_name,lat,lon,count,severity,importance) in enumerate(GROUPS):
            for j in range(count):
                report_no += 1
                # Small offsets keep intended cluster members within roughly 20–40m.
                off_lat=((j%5)-2)*0.00008
                off_lon=((j//5)-0.5)*0.00010
                rpath=DEMO_DIR/f'report_{report_no:02d}.jpg'
                demo_image(rpath,cat_name,report_no)
                created=now-timedelta(days=min(25,1+group_idx*2+j%6))
                r=Report(user_id=citizens[(report_no-1)%len(citizens)].id,category_id=cats[cat_name].id,description=f'{cat_name} reported near a public road; cluster {group_idx+1}.',image_path=str(rpath),latitude=lat+off_lat,longitude=lon+off_lon,location_geometry=WKTElement(f'POINT({lon+off_lon} {lat+off_lat})',srid=4326),submission_status='SUBMITTED',self_reported_severity=severity,created_at=created,updated_at=created)
                db.session.add(r); db.session.flush()
                detect_report(r)
        db.session.commit()
        cluster_all_reports()
        issues=Issue.query.order_by(Issue.id.asc()).all()
        # Configure headline priority scenarios plus additional clustered issues. The seed keeps 20 reports / 8 unified issues as a demonstrable dataset.
        for idx,issue in enumerate(issues):
            linked=[x.report for x in issue.issue_reports]
            if linked:
                issue.created_at=min(r.created_at for r in linked)
                issue.updated_at=now
            if idx==0:
                issue.severity=5; issue.location_importance=5; issue.status='VERIFIED'
            elif idx==1:
                issue.severity=2; issue.location_importance=1; issue.status='REPORTED'
            elif idx==2:
                issue.severity=3; issue.location_importance=3; issue.status='IN_PROGRESS'
            elif idx==3:
                issue.severity=4; issue.location_importance=4; issue.status='ASSIGNED'
            elif idx==4:
                issue.severity=2; issue.location_importance=2; issue.status='UNDER_REVIEW'
            else:
                issue.severity=3; issue.location_importance=2; issue.status='RESOLVED' if idx==5 else 'VERIFIED'
            recalculate_issue_priority(issue)
            if issue.status != 'REPORTED':
                db.session.add(IssueStatusHistory(issue_id=issue.id,old_status='REPORTED',new_status=issue.status,changed_by=admin.id,remarks='Seeded demonstration status.',changed_at=issue.created_at+timedelta(hours=4)))
            if issue.status in {'ASSIGNED','IN_PROGRESS'}:
                db.session.add(IssueAssignment(issue_id=issue.id,assigned_to='Road Maintenance Officer',department='Road Maintenance',remarks='Demo assignment.',assigned_at=issue.created_at+timedelta(hours=6)))
            if issue.status=='RESOLVED': issue.resolved_at=issue.created_at+timedelta(days=2)
        db.session.commit()

        # Create a few pending duplicate candidates within the first cluster for admin review.
        report_rows=Report.query.order_by(Report.id.asc()).all()
        for a,b in [(report_rows[1],report_rows[0]),(report_rows[2],report_rows[0]),(report_rows[10],report_rows[0])]:
            dist = ((a.latitude-b.latitude)**2 + (a.longitude-b.longitude)**2) ** 0.5 * 111320
            db.session.add(DuplicateCandidate(new_report_id=a.id,existing_report_id=b.id,distance_meters=dist,category_similarity=1.0,image_similarity=0.86,text_similarity=0.72,overall_similarity=0.84,decision='PENDING'))
        db.session.commit()
        print('Demo data seeded successfully.')
        print('Demo identities: admin@smartcivic.local and aarav@example.com (create verified Firebase users before signing in).')
        print(f'Reports: {Report.query.count()} | Issues: {Issue.query.count()} | Citizens: {User.query.filter_by(role="CITIZEN").count()}')

if __name__ == '__main__':
    main()
