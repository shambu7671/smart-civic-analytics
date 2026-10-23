# System Architecture and Academic Presentation Guide

## A. System architecture

```text
Citizen/Admin Browser
       |
       | HTML/CSS/JS, multipart uploads, JSON REST
       v
Flask Application
  |-- Authentication + RBAC + CSRF
  |-- Report API
  |-- Issue API
  |-- Admin API
  |-- GIS API
  |-- Analytics API
  `-- AI API
       |
       +--> AI Service
       |      |-- OpenCV image preprocessing
       |      |-- DEMO/MOCK mode
       |      `-- YOLO-compatible real inference
       |
       +--> Duplicate Service
       |      |-- PostGIS nearby candidates
       |      |-- Category comparison
       |      |-- OpenCV perceptual similarity
       |      `-- TF-IDF cosine similarity
       |
       +--> Clustering Service
       |      `-- DBSCAN + haversine distance
       |
       `--> Priority Service
              |-- severity
              |-- supporting report count
              |-- issue age
              `-- location importance
                       |
              SQLAlchemy / GeoAlchemy2
                       |
              PostgreSQL + PostGIS
```

## B. Module architecture

The Flask routes deliberately remain thin. Business logic is located in `app/services/`, which makes it possible to test or replace AI/image/clustering implementations independently.

## C. Database ER structure

```text
users
  1 ─────< reports >───── 1 issue_categories
           |
           +──── 1 ai_detections
           |
           +────< duplicate_candidates >──── reports
           |
           `──── issue_reports >──── 1 issues
                                      |
                                      +────< issue_status_history
                                      |
                                      `────< issue_assignments

system_settings
```

`reports.location_geometry` and `issues.location_geometry` are `GEOGRAPHY(POINT,4326)`.

## D. API list

Auth: register, login, logout, me

Reports: create, mine, detail, AI

Issues: list, detail

Admin: reports, report review, issues, issue patch, verify, assign, status, duplicates, clustering, users, settings, assignments, status history, analytics

GIS: public read-only map + admin map + heatmap

## E. Page list

Public: home, about, login, register, help, public civic map.

Citizen: dashboard, report, reports, report detail, civic issue detail, profile, tracking.

Admin: admin login, dashboard, reports, issues, issue detail, duplicates, map, analytics, users, assignments, status, settings.

## F. Data flow

```text
Photo + Description + GPS
            |
            v
        Report row
            |
            +----> YOLO/OpenCV result
            |
            +----> Nearby reports (PostGIS)
            |          |
            |          +--> category similarity
            |          +--> image similarity
            |          `--> text similarity
            |
            `----> DBSCAN cluster
                         |
                         v
                  Unified Issue row
                         |
                         v
                   Priority score
                         |
             +-----------+-----------+
             |                       |
             v                       v
        Admin workflow          GIS/Heatmap
             |
             v
       Status history
             |
             v
       Citizen tracking
```

## G. Development order

1. Database/PostGIS
2. Auth + RBAC
3. Report upload/GPS
4. AI boundary + DEMO mode
5. Duplicate service
6. DBSCAN
7. Priority score
8. Admin workflow/audit
9. GIS + heatmap
10. Analytics
11. Real YOLO checkpoint
12. End-to-end PostGIS test

## H. Viva explanation in one minute

The project changes the unit of civic workload from *individual complaint* to *unified physical issue*. A citizen contributes a photo, description and GPS point. The backend stores that evidence, runs a modular AI detector, searches geographically nearby reports, compares category/image/text evidence and clusters reports using DBSCAN. Supporting reports become one civic issue. A configurable score based on severity, report count, age and location importance helps administrators prioritize. The issue then appears on a GIS map and follows an auditable status/assignment workflow until resolution.
