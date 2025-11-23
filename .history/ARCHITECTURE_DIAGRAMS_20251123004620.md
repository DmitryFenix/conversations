# Code Review Platform - Архитектурные диаграммы

Визуальные диаграммы архитектуры и логики работы платформы для оценки навыков code review.

## 1. Общая архитектура системы

```mermaid
graph TB
    subgraph "👥 Пользователи"
        Reviewer[👨‍💼 Ревьюер]
        Candidate[👤 Кандидат]
    end
    
    subgraph "💻 Веб-интерфейс"
        WebApp[🌐 Web-приложение<br/>React]
    end
    
    subgraph "⚙️ Сервер приложения"
        API[🔧 API Сервер<br/>FastAPI]
    end
    
    subgraph "💾 Хранилище данных"
        SessionsDB[(📊 База сессий<br/>и комментариев)]
        MRDB[(📦 База Merge Requests)]
        Queue[(⚡ Очередь задач)]
    end
    
    subgraph "🔄 Фоновая обработка"
        Worker[⚙️ Обработчик оценок]
    end
    
    subgraph "🔗 Внешние сервисы"
        GitServer[📝 Git-сервер<br/>Gitea]
    end
    
    Reviewer --> WebApp
    Candidate --> WebApp
    WebApp --> API
    API --> SessionsDB
    API --> MRDB
    API --> Queue
    API --> GitServer
    Queue --> Worker
    Worker --> SessionsDB
    
    style Reviewer fill:#4CAF50,color:#fff
    style Candidate fill:#2196F3,color:#fff
    style WebApp fill:#FF9800,color:#fff
    style API fill:#9C27B0,color:#fff
    style SessionsDB fill:#00BCD4,color:#fff
    style MRDB fill:#00BCD4,color:#fff
    style Queue fill:#F44336,color:#fff
    style Worker fill:#FFC107,color:#000
    style GitServer fill:#607D8B,color:#fff
```

## 2. Основные компоненты системы

```mermaid
graph LR
    subgraph "🎯 Основные модули"
        A[📋 Управление сессиями]
        B[📝 Выбор задач<br/>Merge Requests]
        C[💬 Система комментариев]
        D[📊 Автоматическая оценка]
        E[📄 Генерация отчётов]
    end
    
    A --> B
    B --> C
    C --> D
    D --> E
    
    style A fill:#E3F2FD,color:#000
    style B fill:#F3E5F5,color:#000
    style C fill:#E8F5E9,color:#000
    style D fill:#FFF3E0,color:#000
    style E fill:#FCE4EC,color:#000
```

## 3. Процесс создания сессии

```mermaid
flowchart TD
    Start([🎬 Ревьюер создаёт сессию]) --> Create[📝 Создание сессии<br/>для кандидата]
    Create --> Setup[⚙️ Настройка Git-репозитория]
    Setup --> Select[📦 Выбор задач<br/>Merge Requests]
    Select --> Ready[✅ Сессия готова]
    Ready --> Share[🔗 Отправка ссылки<br/>кандидату]
    
    style Start fill:#4CAF50,color:#fff
    style Create fill:#2196F3,color:#fff
    style Setup fill:#FF9800,color:#fff
    style Select fill:#9C27B0,color:#fff
    style Ready fill:#00BCD4,color:#fff
    style Share fill:#8BC34A,color:#fff
```

## 4. Работа кандидата

```mermaid
sequenceDiagram
    participant R as 👨‍💼 Ревьюер
    participant S as ⚙️ Система
    participant C as 👤 Кандидат
    participant G as 📝 Git-сервер
    
    R->>S: Создать сессию
    S->>G: Настроить репозиторий
    S->>R: Ссылка для кандидата
    R->>C: Отправить ссылку
    
    C->>S: Открыть сессию
    S->>C: Показать код для ревью
    C->>S: Добавить комментарии
    C->>G: Работать в Git-интерфейсе
    S->>S: Собрать все комментарии
    
    Note over C,S: Кандидат может работать<br/>в удобном интерфейсе
```

## 5. Система оценки

```mermaid
flowchart LR
    A[💬 Комментарии<br/>кандидата] --> B[📊 Сравнение с<br/>эталоном]
    B --> C[📈 Расчёт метрик]
    C --> D[📄 Генерация отчёта]
    D --> E[📧 Отправка результатов]
    
    style A fill:#E3F2FD,color:#000
    style B fill:#F3E5F5,color:#000
    style C fill:#E8F5E9,color:#000
    style D fill:#FFF3E0,color:#000
    style E fill:#FCE4EC,color:#000
```

## 6. Классификация задач

```mermaid
graph TD
    MR[Merge Request] --> Type[📋 Тип задачи]
    MR --> Complexity[⭐ Сложность]
    MR --> Stack[🛠️ Технологии]
    
    Type --> T1[🐛 Исправление багов]
    Type --> T2[✨ Новая функция]
    Type --> T3[♻️ Рефакторинг]
    Type --> T4[🧪 Тесты]
    
    Complexity --> C1[⭐ Простая]
    Complexity --> C2[⭐⭐ Средняя]
    Complexity --> C3[⭐⭐⭐ Сложная]
    
    Stack --> S1[🐍 Python]
    Stack --> S2[⚛️ JavaScript/React]
    Stack --> S3[🔧 Backend]
    Stack --> S4[🎨 Frontend]
    
    style MR fill:#9C27B0,color:#fff
    style Type fill:#2196F3,color:#fff
    style Complexity fill:#FF9800,color:#fff
    style Stack fill:#4CAF50,color:#fff
```

## 7. Преимущества системы

```mermaid
mindmap
  root((Code Review<br/>Platform))
    Автоматизация
      Создание сессий
      Настройка репозиториев
      Генерация отчётов
    Гибкость
      Выбор задач
      Разные уровни сложности
      Разные технологии
    Удобство
      Веб-интерфейс
      Интеграция с Git
      Автоматическая оценка
    Качество
      Объективная оценка
      Детальные метрики
      Сравнение с эталоном
```

## 8. Технологический стек

```mermaid
graph TB
    subgraph "Frontend"
        React[⚛️ React]
        Vite[⚡ Vite]
    end
    
    subgraph "Backend"
        FastAPI[🚀 FastAPI]
        Python[🐍 Python]
    end
    
    subgraph "Базы данных"
        SQLite[📊 SQLite]
        PostgreSQL[🐘 PostgreSQL]
        Redis[⚡ Redis]
    end
    
    subgraph "Инфраструктура"
        Docker[🐳 Docker]
        Gitea[📝 Gitea]
    end
    
    React --> FastAPI
    Vite --> FastAPI
    FastAPI --> SQLite
    FastAPI --> PostgreSQL
    FastAPI --> Redis
    FastAPI --> Gitea
    Docker --> React
    Docker --> FastAPI
    
    style React fill:#61DAFB,color:#000
    style FastAPI fill:#009688,color:#fff
    style Python fill:#3776AB,color:#fff
    style SQLite fill:#003B57,color:#fff
    style PostgreSQL fill:#336791,color:#fff
    style Redis fill:#DC382D,color:#fff
    style Docker fill:#2496ED,color:#fff
    style Gitea fill:#609926,color:#fff
```

## 9. Процесс работы системы

```mermaid
stateDiagram-v2
    [*] --> Создание: Ревьюер создаёт сессию
    Создание --> Настройка: Настройка Git-репозитория
    Настройка --> ВыборЗадач: Выбор Merge Requests
    ВыборЗадач --> Готова: Сессия готова
    Готова --> Работа: Кандидат получает доступ
    Работа --> Комментарии: Кандидат добавляет комментарии
    Комментарии --> Оценка: Ревьюер запускает оценку
    Оценка --> Отчёт: Генерация отчёта
    Отчёт --> [*]: Сессия завершена
```

## 10. Метрики оценки

```mermaid
pie title Метрики качества code review
    "Точность обнаружения" : 35
    "Полнота анализа" : 25
    "Качество комментариев" : 20
    "Покрытие кода" : 20
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

### Использование для презентаций

Эти диаграммы оптимизированы для:
- Презентаций заказчикам
- Документации проекта
- Портфолио
- Технических обзоров
