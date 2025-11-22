-- Миграция: Создание таблиц для системы Merge Requests
-- Дата: 2025-11-21

-- Таблица: merge_requests
CREATE TABLE IF NOT EXISTS merge_requests (
    id SERIAL PRIMARY KEY,
    
    -- Идентификация
    external_id TEXT UNIQUE,  -- ID из исходной системы (GitHub, GitLab, etc.)
    title TEXT NOT NULL,
    description TEXT,
    url TEXT,  -- Ссылка на оригинальный MR
    
    -- Метаданные
    author TEXT,
    created_at TIMESTAMP,
    merged_at TIMESTAMP,
    state TEXT,  -- 'open', 'merged', 'closed'
    
    -- Технические характеристики
    language TEXT,  -- Основной язык
    languages TEXT[],  -- Массив языков (если несколько)
    change_type TEXT,  -- 'bugfix', 'feature', 'refactoring', 'performance', 'security', 'documentation'
    
    -- Метрики сложности
    files_changed INTEGER DEFAULT 0,
    lines_added INTEGER DEFAULT 0,
    lines_deleted INTEGER DEFAULT 0,
    diff_size INTEGER DEFAULT 0,  -- Размер diff в байтах
    complexity_score REAL DEFAULT 0,  -- Оценка сложности (0-100)
    
    -- Diff и содержимое
    diff_content TEXT,  -- Полный diff (может быть большим)
    diff_path TEXT,  -- Путь к файлу diff (если храним отдельно)
    
    -- Метрики качества
    has_tests BOOLEAN DEFAULT FALSE,
    test_coverage REAL,  -- Покрытие тестами (0-100)
    code_quality_score REAL,  -- Оценка качества кода (0-100)
    
    -- Проблемы и баги
    bugs_count INTEGER DEFAULT 0,  -- Количество реальных багов
    issues_detected TEXT[],  -- Массив обнаруженных проблем
    security_issues INTEGER DEFAULT 0,
    performance_issues INTEGER DEFAULT 0,
    
    -- Классификация
    difficulty_level TEXT,  -- 'beginner', 'intermediate', 'advanced'
    review_time_estimate INTEGER,  -- Оценка времени на ревью (минуты)
    
    -- Дополнительные данные
    metadata JSONB,  -- Дополнительные метаданные
    tags TEXT[],  -- Теги для категоризации
    
    -- Временные метки
    created_at_db TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Индексы для быстрого поиска
CREATE INDEX IF NOT EXISTS idx_mr_language ON merge_requests(language);
CREATE INDEX IF NOT EXISTS idx_mr_difficulty ON merge_requests(difficulty_level);
CREATE INDEX IF NOT EXISTS idx_mr_change_type ON merge_requests(change_type);
CREATE INDEX IF NOT EXISTS idx_mr_complexity ON merge_requests(complexity_score);
CREATE INDEX IF NOT EXISTS idx_mr_tags ON merge_requests USING GIN(tags);
CREATE INDEX IF NOT EXISTS idx_mr_metadata ON merge_requests USING GIN(metadata);
CREATE INDEX IF NOT EXISTS idx_mr_created_at ON merge_requests(created_at);
CREATE INDEX IF NOT EXISTS idx_mr_external_id ON merge_requests(external_id);

-- Полнотекстовый поиск
CREATE INDEX IF NOT EXISTS idx_mr_search ON merge_requests USING GIN(
    to_tsvector('english', coalesce(title, '') || ' ' || coalesce(description, ''))
);

-- Таблица: mr_files (для детализации по файлам)
CREATE TABLE IF NOT EXISTS mr_files (
    id SERIAL PRIMARY KEY,
    mr_id INTEGER REFERENCES merge_requests(id) ON DELETE CASCADE,
    
    file_path TEXT NOT NULL,
    language TEXT,
    change_type TEXT,  -- 'added', 'modified', 'deleted', 'renamed'
    
    lines_added INTEGER DEFAULT 0,
    lines_deleted INTEGER DEFAULT 0,
    complexity_score REAL,
    
    issues_detected TEXT[],
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mr_files_mr_id ON mr_files(mr_id);
CREATE INDEX IF NOT EXISTS idx_mr_files_language ON mr_files(language);
CREATE INDEX IF NOT EXISTS idx_mr_files_path ON mr_files(file_path);

-- Таблица: mr_comments (комментарии из оригинального ревью)
CREATE TABLE IF NOT EXISTS mr_comments (
    id SERIAL PRIMARY KEY,
    mr_id INTEGER REFERENCES merge_requests(id) ON DELETE CASCADE,
    
    author TEXT,
    file_path TEXT,
    line_number INTEGER,
    comment_text TEXT,
    comment_type TEXT,  -- 'suggestion', 'question', 'issue', 'approval', 'change_request'
    
    created_at TIMESTAMP,
    created_at_db TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_mr_comments_mr_id ON mr_comments(mr_id);
CREATE INDEX IF NOT EXISTS idx_mr_comments_file ON mr_comments(file_path);
CREATE INDEX IF NOT EXISTS idx_mr_comments_type ON mr_comments(comment_type);

-- Таблица: mr_metrics (дополнительные метрики)
CREATE TABLE IF NOT EXISTS mr_metrics (
    id SERIAL PRIMARY KEY,
    mr_id INTEGER REFERENCES merge_requests(id) ON DELETE CASCADE,
    
    metric_name TEXT NOT NULL,
    metric_value REAL,
    metric_data JSONB,  -- Дополнительные данные метрики
    
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(mr_id, metric_name)
);

CREATE INDEX IF NOT EXISTS idx_mr_metrics_mr_id ON mr_metrics(mr_id);
CREATE INDEX IF NOT EXISTS idx_mr_metrics_name ON mr_metrics(metric_name);

-- Функция для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Триггер для автоматического обновления updated_at
DROP TRIGGER IF EXISTS update_merge_requests_updated_at ON merge_requests;
CREATE TRIGGER update_merge_requests_updated_at 
    BEFORE UPDATE ON merge_requests
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();





