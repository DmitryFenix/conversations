-- Миграция: Добавление классификации MR по типам и баллам сложности
-- Дата: 2025-11-22

-- Добавляем поля для классификации
ALTER TABLE merge_requests 
ADD COLUMN IF NOT EXISTS mr_type TEXT,  -- Тип MR: bugfix, feature, refactoring, tests, performance, security, infrastructure, code_style
ADD COLUMN IF NOT EXISTS complexity_points INTEGER DEFAULT 3,  -- Баллы сложности: 1-5
ADD COLUMN IF NOT EXISTS stack_tags TEXT[];  -- Теги стека: ['python', 'backend', 'django']

-- Создаём индекс для быстрого поиска по типу
CREATE INDEX IF NOT EXISTS idx_mr_type ON merge_requests(mr_type);
CREATE INDEX IF NOT EXISTS idx_mr_complexity ON merge_requests(complexity_points);
CREATE INDEX IF NOT EXISTS idx_mr_stack_tags ON merge_requests USING GIN(stack_tags);

-- Обновляем существующие записи (если есть)
-- Устанавливаем дефолтные значения для существующих MR
UPDATE merge_requests 
SET 
    mr_type = COALESCE(mr_type, 'feature'),
    complexity_points = COALESCE(complexity_points, 3),
    stack_tags = COALESCE(stack_tags, ARRAY[]::TEXT[])
WHERE mr_type IS NULL OR complexity_points IS NULL OR stack_tags IS NULL;




