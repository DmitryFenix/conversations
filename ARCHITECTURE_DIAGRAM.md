# Архитектура Code Review Platform - Визуальная диаграмма

## Общая архитектура системы

```mermaid
graph TB
    subgraph "Client Layer"
        R[Reviewer Browser]
        C[Candidate Browser]
    end
    
    subgraph "Frontend Layer"
        RD[ReviewerDashboard]
        CV[CandidateView]
        Router[React Router]
    end
    
    subgraph "Backend Layer"
        API[FastAPI API]
        GiteaClient[Gitea Client]
    end
    
    subgraph "Data Layer"
        DB[(SQLite<br/>reviews.db)]
        Redis[(Redis<br/>Task Queue)]
    end
    
    subgraph "Processing Layer"
        Worker[RQ Worker<br/>Eval Worker]
    end
    
    subgraph "External Services"
        Gitea[Gitea<br/>Git Server]
    end
    
    subgraph "Storage"
        Artifacts[Artifacts<br/>diff.patch<br/>report.txt<br/>report.pdf]
        GiteaData[Gitea Data<br/>Repositories]
    end
    
    R --> Router
    C --> Router
    Router --> RD
    Router --> CV
    
    RD --> API
    CV --> API
    
    API --> DB
    API --> Redis
    API --> GiteaClient
    API --> Artifacts
    
    GiteaClient --> Gitea
    Gitea --> GiteaData
    
    Redis --> Worker
    Worker --> DB
    Worker --> Artifacts
    
    style R fill:#e1f5ff
    style C fill:#fff4e1
    style API fill:#e8f5e9
    style DB fill:#f3e5f5
    style Redis fill:#ffebee
    style Worker fill:#fff9c4
    style Gitea fill:#e0f2f1
```

## Поток создания сессии

```mermaid
sequenceDiagram
    participant R as Reviewer
    participant API as FastAPI
    participant DB as SQLite
    participant GC as Gitea Client
    participant G as Gitea
    
    R->>API: POST /api/reviewer/sessions
    API->>DB: INSERT session
    DB-->>API: session_id
    
    alt Gitea enabled
        API->>GC: create_user(candidate_XXX)
        GC->>G: POST /api/v1/admin/users
        G-->>GC: user created
        API->>GC: create_repository(session_YYY)
        GC->>G: POST /api/v1/user/repos
        G-->>GC: repo created
        API->>GC: create_file(main.py)
        GC->>G: POST /api/v1/repos/.../contents
        G-->>GC: file created
        API->>DB: UPDATE gitea_enabled=1
    end
    
    API-->>R: {session_id, access_token, gitea: {...}}
```

## Поток работы кандидата

```mermaid
sequenceDiagram
    participant C as Candidate
    participant API as FastAPI
    participant DB as SQLite
    participant Artifacts as Artifacts
    
    C->>API: GET /api/candidate/sessions/{token}
    API->>DB: SELECT WHERE access_token=token
    DB-->>API: session data
    API-->>C: {session_id, diff_url, ...}
    
    C->>API: GET /api/candidate/sessions/{token}/diff
    API->>Artifacts: read {session_id}_diff.patch
    Artifacts-->>API: diff content
    API-->>C: diff text
    
    C->>API: POST /api/candidate/sessions/{token}/comments
    API->>DB: UPDATE comments
    DB-->>API: OK
    API-->>C: {status: "ok"}
```

## Поток оценки сессии

```mermaid
sequenceDiagram
    participant R as Reviewer
    participant API as FastAPI
    participant Redis as Redis Queue
    participant Worker as RQ Worker
    participant DB as SQLite
    participant Artifacts as Artifacts
    
    R->>API: POST /api/reviewer/sessions/{id}/evaluate
    API->>Redis: enqueue(evaluate, session_id)
    Redis-->>API: job_id
    API-->>R: {job_id}
    
    Worker->>Redis: dequeue job
    Worker->>DB: SELECT comments, mr_package
    DB-->>Worker: comments, mr_package
    Worker->>Artifacts: read golden_truth.json
    Artifacts-->>Worker: golden truth
    
    Worker->>Worker: compare comments
    Worker->>Worker: calculate TP, FP, FN
    Worker->>Worker: calculate Score, Grade
    
    Worker->>Artifacts: write report.txt
    Worker->>DB: UPDATE (optional)
    
    R->>API: GET /api/reviewer/sessions/{id}/report
    API->>Artifacts: read report.txt
    Artifacts-->>API: report content
    API-->>R: report text
```

## Разделение ролей

```mermaid
graph LR
    subgraph "Reviewer Access"
        R1[Create Sessions]
        R2[View Sessions List]
        R3[View Session Details]
        R4[Evaluate Session]
        R5[View Reports]
        R6[Extend Session]
        R7[Access Gitea]
    end
    
    subgraph "Candidate Access"
        C1[View Session by Token]
        C2[View Diff]
        C3[Add Comments]
        C4[View Timer]
    end
    
    subgraph "Restricted"
        X1[❌ View Reports]
        X2[❌ Extend Session]
        X3[❌ Create Sessions]
    end
    
    C1 --> C2
    C2 --> C3
    C3 --> C4
    
    R1 --> R2
    R2 --> R3
    R3 --> R4
    R4 --> R5
    R5 --> R6
    R6 --> R7
    
    C1 -.->|No Access| X1
    C1 -.->|No Access| X2
    C1 -.->|No Access| X3
```

## Структура данных

```mermaid
erDiagram
    SESSIONS {
        int id PK
        string candidate_id
        string candidate_name
        string reviewer_name
        string mr_package
        json comments
        datetime created_at
        datetime expires_at
        string access_token UK
        string reviewer_token
        string status
        string gitea_user
        string gitea_repo
        int gitea_pr_id
        bool gitea_enabled
    }
    
    COMMENTS {
        string file
        string line_range
        string type
        string severity
        string text
    }
    
    SESSIONS ||--o{ COMMENTS : contains
```

## Docker Compose Services

```mermaid
graph TB
    subgraph "Docker Compose"
        API[api:8000<br/>FastAPI]
        Redis[redis:6379<br/>Redis 7.2-alpine]
        Worker[worker<br/>RQ Worker]
        Gitea[gitea:3000<br/>Gitea 1.22.2]
    end
    
    subgraph "Volumes"
        DBVol[./api/reviews.db]
        ArtifactsVol[./artifacts]
        MRVol[./mr_packages]
        GiteaDataVol[./gitea_data]
        GiteaConfigVol[./gitea_config]
    end
    
    API --> Redis
    API --> DBVol
    API --> ArtifactsVol
    API --> MRVol
    API --> Gitea
    
    Worker --> Redis
    Worker --> DBVol
    Worker --> ArtifactsVol
    Worker --> MRVol
    
    Gitea --> GiteaDataVol
    Gitea --> GiteaConfigVol
    
    style API fill:#e8f5e9
    style Redis fill:#ffebee
    style Worker fill:#fff9c4
    style Gitea fill:#e0f2f1
```

## Технологический стек

```mermaid
graph TB
    subgraph "Frontend"
        React[React 19.1.1]
        Vite[Vite 7.1.7]
        Router[React Router 6.31.1]
        Monaco[Monaco Editor]
    end
    
    subgraph "Backend"
        FastAPI[FastAPI 0.119.1]
        Python[Python 3.11.10]
        Uvicorn[Uvicorn 0.38.0]
        WeasyPrint[WeasyPrint 62.3]
    end
    
    subgraph "Data"
        SQLite[SQLite]
        Redis[Redis 7.2]
    end
    
    subgraph "Task Queue"
        RQ[RQ 2.6.0]
    end
    
    subgraph "Git"
        Gitea[Gitea 1.22.2]
    end
    
    React --> Vite
    Vite --> Router
    Router --> Monaco
    
    FastAPI --> Python
    Python --> Uvicorn
    Python --> WeasyPrint
    Python --> SQLite
    Python --> Redis
    Python --> RQ
    Python --> Gitea
```

