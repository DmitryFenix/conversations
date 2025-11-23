# Code Review Platform - ASCII диаграммы архитектуры

Упрощенные ASCII-диаграммы для быстрого просмотра без специальных инструментов.

## 1. Общая архитектура системы

```
┌─────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER                              │
│  ┌──────────────┐                    ┌──────────────┐          │
│  │   Reviewer   │                    │  Candidate   │          │
│  │   Browser    │                    │   Browser    │          │
│  └──────┬───────┘                    └──────┬───────┘          │
└─────────┼────────────────────────────────────┼──────────────────┘
          │                                    │
          └────────────┬───────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────────────┐
│                    FRONTEND LAYER                               │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              React Router                                │  │
│  │  /reviewer → ReviewerDashboard                           │  │
│  │  /reviewer/sessions/:id/select-mr → MRSelectionPage      │  │
│  │  /candidate/:token → CandidateView                      │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────────┘
                       │ HTTP/REST API
┌──────────────────────▼──────────────────────────────────────────┐
│                    BACKEND LAYER                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              FastAPI API (Port 8000)                     │  │
│  │  • Session Management                                     │  │
│  │  • MR Selection & Management                              │  │
│  │  • Comment Handling                                       │  │
│  │  • Evaluation Triggering                                  │  │
│  └──────────────┬───────────────────────────────────────────┘  │
│                 │                                                │
│  ┌──────────────▼───────────────────────────────────────────┐  │
│  │              Gitea Client                                 │  │
│  │  • User/Repo Creation                                    │  │
│  │  • PR Management                                         │  │
│  │  • File Operations                                       │  │
│  └──────────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┬──────────────┐
        │              │              │              │
┌───────▼──────┐ ┌─────▼─────┐ ┌─────▼─────┐ ┌─────▼─────┐
│   SQLite     │ │PostgreSQL  │ │   Redis   │ │  Gitea    │
│ reviews.db   │ │mr_database │ │Task Queue │ │Git Server │
│              │ │            │ │           │ │Port 4001  │
│ Sessions     │ │Merge       │ │RQ Jobs    │ │           │
│ Comments     │ │Requests    │ │           │ │Repos      │
│              │ │            │ │           │ │PRs        │
└──────┬───────┘ └────────────┘ └─────┬─────┘ └───────────┘
       │                              │
       │                              │
┌──────▼──────────────────────────────▼───────┐
│         PROCESSING LAYER                     │
│  ┌──────────────────────────────────────┐  │
│  │         RQ Worker                     │  │
│  │  • Eval Worker (evaluate function)    │  │
│  │  • Scheduler (scheduled tasks)        │  │
│  │  • Restart: always                   │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## 2. Поток создания сессии с выбором MR

```
Reviewer
   │
   │ 1. POST /api/reviewer/sessions
   ▼
FastAPI
   │
   ├─► 2. Create session in SQLite
   │
   ├─► 3. Create Gitea user
   │      │
   │      └─► Gitea API: POST /api/v1/admin/users
   │
   ├─► 4. Create Gitea repository
   │      │
   │      └─► Gitea API: POST /api/v1/admin/users/{user}/repos
   │
   ├─► 5. Create branch (candidate-work-{id})
   │      │
   │      └─► Gitea API: POST /api/v1/repos/{owner}/{repo}/branches
   │
   ├─► 6. Create initial file (main.py)
   │      │
   │      └─► Gitea API: POST /api/v1/repos/{owner}/{repo}/contents
   │
   ├─► 7. Create Pull Request
   │      │
   │      └─► Gitea API: POST /api/v1/repos/{owner}/{repo}/pulls
   │
   └─► 8. Return session_id
        │
        ▼
   Frontend: Redirect to /reviewer/sessions/{id}/select-mr
        │
        │ 9. GET /api/mr/list
        ▼
   PostgreSQL: SELECT * FROM merge_requests
        │
        ▼
   Frontend: Display MRs with filters
        │
        │ 10. Reviewer selects MR(s)
        │
        │ 11. PUT /api/reviewer/sessions/{id}/mrs
        ▼
   FastAPI
        │
        ├─► 12. Fetch diff_content from PostgreSQL
        │
        ├─► 13. Parse diff (parse_diff_simple)
        │
        ├─► 14. Combine diffs
        │
        ├─► 15. Save to artifacts/{id}_diff.patch
        │
        └─► 16. Update files in Gitea PR
             │
             ├─► For each file:
             │   ├─► GET /api/v1/repos/.../contents/{file}
             │   │
             │   ├─► If exists: PUT /api/v1/repos/.../contents/{file}
             │   │
             │   └─► If not: POST /api/v1/repos/.../contents/{file}
             │
             └─► Update session.mr_id in SQLite
                  │
                  ▼
             Frontend: Redirect to session details
```

## 3. Архитектура базы данных

### SQLite (Sessions & Comments)

```
┌─────────────────────────────────┐
│          SESSIONS               │
├─────────────────────────────────┤
│ id (PK)                         │
│ candidate_id                    │
│ candidate_name                  │
│ reviewer_name                   │
│ mr_package                      │
│ comments (JSON)                 │
│ created_at                      │
│ expires_at                      │
│ access_token                    │
│ reviewer_token                  │
│ mr_id (FK)                      │
│ gitea_user                      │
│ gitea_repo                      │
│ gitea_pr_id                     │
│ gitea_enabled                   │
│ candidate_ready_at              │
│ deleted_at                      │
└──────────┬──────────────────────┘
           │
           │ 1:N
           │
┌──────────▼──────────────────────┐
│         COMMENTS                │
├─────────────────────────────────┤
│ id (PK)                         │
│ session_id (FK)                 │
│ file_path                       │
│ line_number                     │
│ comment_text                    │
│ created_at                      │
└─────────────────────────────────┘
```

### PostgreSQL (Merge Requests)

```
┌──────────────────────────────────────────────────┐
│           MERGE_REQUESTS                         │
├──────────────────────────────────────────────────┤
│ id (PK)                                          │
│ external_id (UK)                                 │
│ title                                            │
│ description                                      │
│ url                                              │
│ author                                           │
│ created_at                                       │
│ merged_at                                        │
│ state                                            │
│ language                                         │
│ languages[]                                      │
│ change_type                                      │
│ files_changed                                    │
│ lines_added                                      │
│ lines_deleted                                    │
│ diff_size                                        │
│ complexity_score                                 │
│ diff_content (TEXT)                              │
│ has_tests                                        │
│ test_coverage                                    │
│ code_quality_score                               │
│ bugs_count                                       │
│ issues_detected[]                                │
│ security_issues                                  │
│ performance_issues                               │
│ difficulty_level                                 │
│ review_time_estimate                             │
│ metadata (JSONB)                                  │
│ tags[]                                           │
│ mr_type                                          │
│ complexity_points                                │
│ stack_tags[]                                     │
│ created_at_db                                    │
│ updated_at                                       │
└──────┬──────────────┬──────────────┬─────────────┘
       │              │              │
       │ 1:N          │ 1:N          │ 1:N
       │              │              │
┌──────▼──────┐ ┌────▼──────┐ ┌─────▼──────┐
│  MR_FILES   │ │MR_COMMENTS│ │MR_METRICS  │
├─────────────┤ ├───────────┤ ├────────────┤
│ id (PK)     │ │ id (PK)   │ │ id (PK)    │
│ mr_id (FK)  │ │ mr_id(FK) │ │ mr_id (FK) │
│ file_path   │ │ author    │ │metric_name │
│ language    │ │file_path  │ │metric_value│
│change_type  │ │line_number│ │metric_data │
│lines_added  │ │comment_txt│ │calculated  │
│lines_deleted│ │comment_type│            │
│complexity   │ │created_at │ │            │
│issues[]     │ │           │ │            │
└─────────────┘ └───────────┘ └────────────┘
```

## 4. Docker Compose архитектура

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  api (FastAPI)                                     │    │
│  │  • Port: 8000                                      │    │
│  │  • Hot Reload: Enabled                             │    │
│  │  • Volumes:                                        │    │
│  │    - ./api/*.py                                    │    │
│  │    - ./artifacts                                   │    │
│  │    - ./mr_packages                                │    │
│  │    - ./scripts                                    │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  worker (RQ Worker)                                │    │
│  │  • Command: rq worker default --with-scheduler     │    │
│  │  • Restart: always                                 │    │
│  │  • Volumes:                                        │    │
│  │    - ./api/eval_worker.py                          │    │
│  │    - ./artifacts                                   │    │
│  │    - ./mr_packages                                 │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  redis (Redis 7.2-alpine)                         │    │
│  │  • Port: 6379                                      │    │
│  │  • Health Check: Enabled                           │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  postgres (PostgreSQL 16-alpine)                   │    │
│  │  • Port: 5432                                      │    │
│  │  • Database: mr_database                           │    │
│  │  • Volume: postgres_data (named)                   │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌────────────────────────────────────────────────────┐    │
│  │  gitea (Gitea 1.22.2)                             │    │
│  │  • Port: 4001 (HTTP), 2222 (SSH)                  │    │
│  │  • Volumes:                                        │    │
│  │    - ./gitea_data                                  │    │
│  │    - ./gitea_config                                │    │
│  └────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## 5. Классификация MR

```
                    Merge Request
                          │
                          ▼
                   MR Classifier
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
    MR Type      Complexity Points    Stack Tags
        │                 │                 │
   ┌────┴────┐      ┌─────┴─────┐     ┌─────┴─────┐
   │         │      │           │     │           │
Bugfix       1 pt   Simple      Python JavaScript
Feature      2 pts  Easy        React Backend
Refactoring  3 pts  Medium      Frontend Docker
Tests        4 pts  Hard
Performance  5 pts  Very Hard
Security
Infrastructure
Code Style
```

## 6. Поток оценки сессии

```
Reviewer
   │
   │ POST /api/reviewer/sessions/{id}/evaluate
   ▼
FastAPI
   │
   ├─► Validate session exists
   │
   ├─► Check comments exist
   │
   └─► Enqueue job to Redis
        │
        ▼
   Redis Queue (default)
        │
        ▼
   RQ Worker picks up job
        │
        ├─► Load session from SQLite
        │
        ├─► Load comments from SQLite
        │
        ├─► Load golden_truth.json from artifacts
        │
        ├─► Compare comments with golden truth
        │
        ├─► Calculate metrics:
        │   • Precision
        │   • Recall
        │   • F1 Score
        │   • Coverage
        │
        ├─► Generate report.txt
        │
        ├─► Generate report.pdf (WeasyPrint)
        │
        ├─► Save reports to artifacts/
        │
        └─► Update session in SQLite
             │
             ▼
        Job completed
             │
             ▼
   Reviewer refreshes page
        │
        │ GET /api/reviewer/sessions/{id}
        ▼
   FastAPI returns session with evaluation results
        │
        ▼
   Frontend displays results
```

## Использование

Эти ASCII-диаграммы можно:
- Просматривать в любом текстовом редакторе
- Вставлять в документацию
- Использовать в презентациях
- Печатать на принтере

Для более детальных и интерактивных диаграмм см. `ARCHITECTURE_DIAGRAMS.md` с Mermaid диаграммами.


