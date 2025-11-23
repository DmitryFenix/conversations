# Code Review Platform - Архитектурные диаграммы

Этот документ содержит визуальные диаграммы архитектуры и логики работы приложения Code Review Platform.

## 1. Общая архитектура системы

```mermaid
graph TB
    subgraph "Client Layer"
        R[Reviewer Browser]
        C[Candidate Browser]
    end
    
    subgraph "Frontend Layer"
        RD[ReviewerDashboard]
        MRP[MRSelectionPage]
        CV[CandidateView]
        Router[React Router]
    end
    
    subgraph "Backend Layer - FastAPI"
        API[FastAPI API<br/>Port 8000]
        GiteaClient[Gitea Client]
    end
    
    subgraph "Data Layer"
        SQLite[(SQLite<br/>reviews.db<br/>Sessions, Comments)]
        PostgreSQL[(PostgreSQL<br/>mr_database<br/>Merge Requests)]
        Redis[(Redis<br/>Task Queue<br/>Port 6379)]
    end
    
    subgraph "Processing Layer"
        Worker[RQ Worker<br/>Eval Worker<br/>with Scheduler]
    end
    
    subgraph "External Services"
        Gitea[Gitea<br/>Git Server<br/>Port 4001]
    end
    
    subgraph "Storage"
        Artifacts[Artifacts<br/>diff.patch<br/>report.txt<br/>report.pdf]
        GiteaData[Gitea Data<br/>Repositories<br/>PRs, Comments]
    end
    
    R --> Router
    C --> Router
    Router --> RD
    Router --> MRP
    Router --> CV
    
    RD --> API
    MRP --> API
    CV --> API
    
    API --> SQLite
    API --> PostgreSQL
    API --> Redis
    API --> GiteaClient
    API --> Artifacts
    
    GiteaClient --> Gitea
    Gitea --> GiteaData
    
    Redis --> Worker
    Worker --> SQLite
    Worker --> Artifacts
    
    style R fill:#e1f5ff
    style C fill:#fff4e1
    style API fill:#e8f5e9
    style SQLite fill:#f3e5f5
    style PostgreSQL fill:#e3f2fd
    style Redis fill:#ffebee
    style Worker fill:#fff9c4
    style Gitea fill:#e0f2f1
```

## 2. Архитектура базы данных

### 2.1 SQLite (Sessions & Comments)

```mermaid
erDiagram
    SESSIONS ||--o{ COMMENTS : has
    SESSIONS {
        int id PK
        string candidate_id
        string candidate_name
        string reviewer_name
        string mr_package
        text comments JSON
        datetime created_at
        datetime expires_at
        string access_token
        string reviewer_token
        int mr_id
        string gitea_user
        string gitea_repo
        int gitea_pr_id
        boolean gitea_enabled
        datetime candidate_ready_at
        datetime deleted_at
    }
    
    COMMENTS {
        int id PK
        int session_id
        string file_path
        int line_number
        string comment_text
        datetime created_at
    }
```

### 2.2 PostgreSQL (Merge Requests)

```mermaid
erDiagram
    MERGE_REQUESTS ||--o{ MR_FILES : contains
    MERGE_REQUESTS ||--o{ MR_COMMENTS : has
    MERGE_REQUESTS ||--o{ MR_METRICS : has
    
    MERGE_REQUESTS {
        int id PK
        string external_id UK
        string title
        text description
        string url
        string author
        datetime created_at
        datetime merged_at
        string state
        string language
        string[] languages
        string change_type
        int files_changed
        int lines_added
        int lines_deleted
        int diff_size
        real complexity_score
        text diff_content
        boolean has_tests
        real test_coverage
        real code_quality_score
        int bugs_count
        string[] issues_detected
        int security_issues
        int performance_issues
        string difficulty_level
        int review_time_estimate
        jsonb metadata
        string[] tags
        string mr_type
        int complexity_points
        string[] stack_tags
        datetime created_at_db
        datetime updated_at
    }
    
    MR_FILES {
        int id PK
        int mr_id
        string file_path
        string language
        string change_type
        int lines_added
        int lines_deleted
        real complexity_score
        string[] issues_detected
        datetime created_at
    }
    
    MR_COMMENTS {
        int id PK
        int mr_id
        string author
        string file_path
        int line_number
        text comment_text
        string comment_type
        datetime created_at
        datetime created_at_db
    }
    
    MR_METRICS {
        int id PK
        int mr_id
        string metric_name
        real metric_value
        jsonb metric_data
        datetime calculated_at
    }
```

## 3. Поток создания сессии с выбором MR

```mermaid
sequenceDiagram
    participant R as Reviewer
    participant FD as Frontend
    participant API as FastAPI API
    participant SQLite as SQLite DB
    participant PG as PostgreSQL
    participant GC as Gitea Client
    participant G as Gitea
    participant Redis as Redis Queue
    
    R->>FD: Создать сессию (имя кандидата)
    FD->>API: POST /api/reviewer/sessions
    API->>SQLite: Создать запись сессии
    API->>GC: Создать пользователя Gitea
    GC->>G: POST /api/v1/admin/users
    G-->>GC: User created
    API->>GC: Создать репозиторий
    GC->>G: POST /api/v1/admin/users/{user}/repos
    G-->>GC: Repository created
    API->>GC: Создать ветку candidate-work-{id}
    GC->>G: POST /api/v1/repos/{owner}/{repo}/branches
    G-->>GC: Branch created
    API->>GC: Создать начальный файл main.py
    GC->>G: POST /api/v1/repos/{owner}/{repo}/contents
    G-->>GC: File created
    API->>GC: Создать Pull Request
    GC->>G: POST /api/v1/repos/{owner}/{repo}/pulls
    G-->>GC: PR created
    API->>SQLite: Обновить сессию (gitea_repo, gitea_pr_id)
    API-->>FD: Session created (session_id)
    FD->>FD: Redirect to /reviewer/sessions/{id}/select-mr
    
    Note over R,FD: Страница выбора MR
    
    FD->>API: GET /api/mr/list
    API->>PG: SELECT * FROM merge_requests
    PG-->>API: List of MRs
    API-->>FD: MRs with filters
    
    R->>FD: Выбрать MR(s)
    FD->>API: PUT /api/reviewer/sessions/{id}/mrs
    API->>PG: Получить diff из выбранных MR
    PG-->>API: diff_content для каждого MR
    API->>API: Объединить diff'ы
    API->>API: Парсить diff (parse_diff_simple)
    API->>GC: Обновить файлы в Gitea PR
    loop Для каждого файла
        GC->>G: GET /api/v1/repos/{owner}/{repo}/contents/{file}
        alt Файл существует
            GC->>G: PUT /api/v1/repos/{owner}/{repo}/contents/{file}
        else Файл не существует
            GC->>G: POST /api/v1/repos/{owner}/{repo}/contents/{file}
        end
    end
    API->>SQLite: Обновить сессию (mr_id)
    API-->>FD: MR updated successfully
    FD->>FD: Redirect to session details
```

## 4. Поток работы кандидата

```mermaid
sequenceDiagram
    participant C as Candidate
    participant FD as Frontend
    participant API as FastAPI API
    participant SQLite as SQLite DB
    participant GC as Gitea Client
    participant G as Gitea
    
    C->>FD: Открыть /candidate/{token}
    FD->>API: GET /api/candidate/sessions/{token}
    API->>SQLite: Найти сессию по access_token
    SQLite-->>API: Session data
    API->>API: Проверить срок действия
    API->>API: Загрузить diff из artifacts
    API-->>FD: Session data + diff content
    
    FD->>FD: Отобразить diff в Monaco Editor
    
    C->>FD: Добавить комментарий
    FD->>API: POST /api/candidate/sessions/{token}/comments
    API->>SQLite: Сохранить комментарий
    SQLite-->>API: Comment saved
    API-->>FD: Comment created
    
    Note over C,G: Кандидат может работать в Gitea напрямую
    
    C->>G: Открыть PR в Gitea
    G->>G: Добавить комментарии в PR
    G->>G: Создать review comments
    
    FD->>API: GET /api/reviewer/sessions/{id}/gitea/pr
    API->>GC: Получить комментарии из PR
    GC->>G: GET /api/v1/repos/{owner}/{repo}/pulls/{pr_id}/comments
    G-->>GC: PR comments
    GC-->>API: Comments data
    API-->>FD: Gitea PR data with comments
```

## 5. Поток оценки сессии (Evaluation)

```mermaid
sequenceDiagram
    participant R as Reviewer
    participant FD as Frontend
    participant API as FastAPI API
    participant Redis as Redis Queue
    participant Worker as RQ Worker
    participant SQLite as SQLite DB
    participant Artifacts as Artifacts
    
    R->>FD: Запустить оценку
    FD->>API: POST /api/reviewer/sessions/{id}/evaluate
    API->>SQLite: Получить сессию
    SQLite-->>API: Session data
    API->>API: Проверить наличие комментариев
    API->>Redis: Enqueue evaluation job
    Redis-->>API: Job ID
    API-->>FD: Evaluation started
    
    Note over Worker,Artifacts: Фоновая обработка
    
    Worker->>Redis: Получить задачу из очереди
    Redis-->>Worker: Job data (session_id)
    Worker->>SQLite: Загрузить сессию и комментарии
    SQLite-->>Worker: Session + comments
    Worker->>Artifacts: Загрузить golden_truth.json
    Artifacts-->>Worker: Golden truth data
    Worker->>Worker: Сравнить комментарии с golden truth
    Worker->>Worker: Рассчитать метрики
    Worker->>Artifacts: Сохранить report.txt
    Worker->>Artifacts: Сохранить report.pdf
    Worker->>SQLite: Обновить сессию (evaluation results)
    Worker->>Redis: Job completed
    
    R->>FD: Обновить страницу
    FD->>API: GET /api/reviewer/sessions/{id}
    API->>SQLite: Получить сессию
    SQLite-->>API: Session with evaluation results
    API-->>FD: Session data
    FD->>FD: Отобразить результаты оценки
```

## 6. Архитектура компонентов Docker

```mermaid
graph TB
    subgraph "Docker Compose Services"
        subgraph "API Service"
            API[FastAPI Container<br/>Port 8000<br/>Hot Reload Enabled]
            APIVolumes[Volumes:<br/>- ./api/*.py<br/>- ./artifacts<br/>- ./mr_packages<br/>- ./scripts]
        end
        
        subgraph "Worker Service"
            Worker[RQ Worker Container<br/>with Scheduler<br/>Restart: always]
            WorkerVolumes[Volumes:<br/>- ./api/eval_worker.py<br/>- ./artifacts<br/>- ./mr_packages]
        end
        
        subgraph "Redis Service"
            Redis[Redis 7.2-alpine<br/>Port 6379<br/>Health Check]
        end
        
        subgraph "PostgreSQL Service"
            PG[PostgreSQL 16-alpine<br/>Port 5432<br/>Named Volume]
        end
        
        subgraph "Gitea Service"
            Gitea[Gitea 1.22.2<br/>Port 4001<br/>SSH Port 2222]
            GiteaVolumes[Volumes:<br/>- ./gitea_data<br/>- ./gitea_config]
        end
    end
    
    subgraph "Host Filesystem"
        ArtifactsDir[./artifacts]
        MPPackagesDir[./mr_packages]
        ScriptsDir[./scripts]
        GiteaDataDir[./gitea_data]
        PostgresVolume[(postgres_data)]
    end
    
    API --> Redis
    API --> PG
    API --> Gitea
    Worker --> Redis
    Worker --> PG
    
    APIVolumes -.-> ArtifactsDir
    APIVolumes -.-> MPPackagesDir
    APIVolumes -.-> ScriptsDir
    WorkerVolumes -.-> ArtifactsDir
    WorkerVolumes -.-> MPPackagesDir
    GiteaVolumes -.-> GiteaDataDir
    PG -.-> PostgresVolume
    
    style API fill:#e8f5e9
    style Worker fill:#fff9c4
    style Redis fill:#ffebee
    style PG fill:#e3f2fd
    style Gitea fill:#e0f2f1
```

## 7. Классификация Merge Requests

```mermaid
graph LR
    subgraph "MR Classification System"
        MR[Merge Request] --> Classifier[MR Classifier]
        
        Classifier --> Type[MR Type]
        Classifier --> Complexity[Complexity Points]
        Classifier --> Stack[Stack Tags]
        
        Type --> T1[Bugfix]
        Type --> T2[Feature]
        Type --> T3[Refactoring]
        Type --> T4[Tests]
        Type --> T5[Performance]
        Type --> T6[Security]
        Type --> T7[Infrastructure]
        Type --> T8[Code Style]
        
        Complexity --> C1[1 point<br/>Simple]
        Complexity --> C2[2 points<br/>Easy]
        Complexity --> C3[3 points<br/>Medium]
        Complexity --> C4[4 points<br/>Hard]
        Complexity --> C5[5 points<br/>Very Hard]
        
        Stack --> S1[Python]
        Stack --> S2[JavaScript]
        Stack --> S3[React]
        Stack --> S4[Backend]
        Stack --> S5[Frontend]
        Stack --> S6[Docker]
    end
    
    MR --> Metrics[MR Metrics]
    Metrics --> M1[Files Changed]
    Metrics --> M2[Lines Added/Deleted]
    Metrics --> M3[Diff Size]
    Metrics --> M4[Complexity Score]
    Metrics --> M5[Test Coverage]
    Metrics --> M6[Code Quality]
    
    style Classifier fill:#e8f5e9
    style Type fill:#fff9c4
    style Complexity fill:#e3f2fd
    style Stack fill:#f3e5f5
```

## 8. Поток выбора и применения MR

```mermaid
flowchart TD
    Start([Reviewer создает сессию]) --> CreateSession[Создать сессию в SQLite]
    CreateSession --> CreateGitea[Создать Gitea репозиторий и PR]
    CreateGitea --> Redirect[Redirect to MR Selection Page]
    
    Redirect --> LoadMRs[Загрузить список MR из PostgreSQL]
    LoadMRs --> FilterMRs[Применить фильтры:<br/>- Type<br/>- Complexity<br/>- Stack Tags]
    
    FilterMRs --> DisplayMRs[Отобразить MR с тегами и баллами]
    DisplayMRs --> SelectMRs{Reviewer выбирает MR}
    
    SelectMRs -->|Выбрано| UpdateSession[PUT /api/reviewer/sessions/{id}/mrs]
    SelectMRs -->|Пропустить| Skip[Пропустить выбор MR]
    
    UpdateSession --> FetchDiffs[Получить diff_content из PostgreSQL]
    FetchDiffs --> ParseDiffs[Парсить diff для каждого MR]
    ParseDiffs --> CombineDiffs[Объединить diff'ы]
    CombineDiffs --> SaveArtifact[Сохранить в artifacts/{id}_diff.patch]
    
    SaveArtifact --> UpdateGitea[Обновить файлы в Gitea PR]
    UpdateGitea --> CheckFile{Файл существует?}
    
    CheckFile -->|Да| UpdateFile[PUT /api/v1/repos/.../contents/{file}]
    CheckFile -->|Нет| CreateFile[POST /api/v1/repos/.../contents/{file}]
    
    UpdateFile --> UpdateSQLite[Обновить session.mr_id в SQLite]
    CreateFile --> UpdateSQLite
    
    UpdateSQLite --> Success[MR успешно применены]
    Skip --> Success
    Success --> SessionReady[Сессия готова для кандидата]
    
    style Start fill:#e1f5ff
    style SelectMRs fill:#fff9c4
    style UpdateSession fill:#e8f5e9
    style Success fill:#c8e6c9
```

## 9. Интеграция с Gitea

```mermaid
graph TB
    subgraph "Code Review Platform"
        API[FastAPI API]
        GC[Gitea Client]
    end
    
    subgraph "Gitea API Endpoints"
        Users[User Management<br/>POST /api/v1/admin/users]
        Repos[Repository Management<br/>POST /api/v1/admin/users/{user}/repos]
        Branches[Branch Management<br/>POST /api/v1/repos/{owner}/{repo}/branches]
        Files[File Operations<br/>GET/POST/PUT /api/v1/repos/{owner}/{repo}/contents]
        PRs[Pull Requests<br/>POST /api/v1/repos/{owner}/{repo}/pulls]
        Comments[PR Comments<br/>GET /api/v1/repos/{owner}/{repo}/pulls/{id}/comments]
    end
    
    subgraph "Gitea Server"
        Gitea[Gitea Instance<br/>Port 4001]
        RepoData[(Repository Data)]
        UserData[(User Data)]
    end
    
    API --> GC
    GC --> Users
    GC --> Repos
    GC --> Branches
    GC --> Files
    GC --> PRs
    GC --> Comments
    
    Users --> Gitea
    Repos --> Gitea
    Branches --> Gitea
    Files --> Gitea
    PRs --> Gitea
    Comments --> Gitea
    
    Gitea --> RepoData
    Gitea --> UserData
    
    style API fill:#e8f5e9
    style GC fill:#fff9c4
    style Gitea fill:#e0f2f1
```

## 10. Система мониторинга RQ

```mermaid
graph LR
    subgraph "RQ Monitoring"
        RQMonitor[RQ Monitor<br/>OptimizedQueue]
        RQDashboard[RQ Dashboard<br/>/api/rq/*]
    end
    
    subgraph "Redis Queue"
        Queue[default Queue]
        Jobs[Jobs:<br/>- Pending<br/>- Started<br/>- Finished<br/>- Failed]
    end
    
    subgraph "Worker"
        Worker[RQ Worker<br/>with Scheduler]
        EvalWorker[Eval Worker<br/>evaluate function]
    end
    
    RQMonitor --> Queue
    RQMonitor --> Jobs
    RQDashboard --> RQMonitor
    Queue --> Worker
    Worker --> EvalWorker
    
    style RQMonitor fill:#e8f5e9
    style RQDashboard fill:#fff9c4
    style Worker fill:#e3f2fd
```

## Примечания

### Форматы диаграмм

Все диаграммы созданы в формате **Mermaid**, который поддерживается:
- GitHub (автоматический рендеринг в .md файлах)
- VS Code (с расширением Mermaid Preview)
- Онлайн редакторы (Notion, GitLab, и др.)
- Экспорт в PNG/SVG через Mermaid Live Editor

### Экспорт в изображения

Для экспорта диаграмм в PNG/SVG:
1. Откройте [Mermaid Live Editor](https://mermaid.live/)
2. Скопируйте код диаграммы из этого файла
3. Экспортируйте в PNG или SVG

### Обновление диаграмм

При изменении архитектуры обновите соответствующие диаграммы в этом файле для поддержания актуальности документации.

