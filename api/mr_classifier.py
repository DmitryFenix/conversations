# api/mr_classifier.py
"""
Модуль для классификации Merge Requests по типам и баллам сложности
"""
from typing import Dict, Any, List, Optional
import re


# Типы MR
MR_TYPES = {
    'bugfix': 'Bugfix / корректность логики',
    'feature': 'Feature / добавление функционала',
    'refactoring': 'Refactoring / архитектурный MR',
    'tests': 'Tests / покрытие и качество тестов',
    'performance': 'Performance / ресурсоёмкость',
    'security': 'Security / надёжность',
    'infrastructure': 'Infrastructure / конфигурация / DevOps',
    'code_style': 'Code style / читаемость / code smells'
}

# Теги стека
STACK_TAGS = {
    'python': ['python', 'py', '.py'],
    'javascript': ['javascript', 'js', 'typescript', 'ts', '.js', '.ts'],
    'java': ['java', '.java'],
    'go': ['go', 'golang', '.go'],
    'backend': ['backend', 'api', 'server', 'django', 'flask', 'fastapi'],
    'frontend': ['frontend', 'react', 'vue', 'angular', 'ui'],
    'devops': ['docker', 'kubernetes', 'k8s', 'ci/cd', 'deploy'],
    'database': ['sql', 'postgres', 'mysql', 'mongodb']
}


def detect_mr_type(mr_data: Dict[str, Any], diff_content: Optional[str] = None) -> str:
    """
    Определить тип MR на основе метаданных и diff
    
    Args:
        mr_data: Данные MR
        diff_content: Содержимое diff (опционально)
        
    Returns:
        Тип MR (один из MR_TYPES.keys())
    """
    title = (mr_data.get('title', '') or '').lower()
    description = (mr_data.get('description', '') or '').lower()
    change_type = (mr_data.get('change_type', '') or '').lower()
    diff = (diff_content or '').lower()
    
    combined_text = f"{title} {description} {change_type} {diff}"
    
    # Security
    security_keywords = ['security', 'vulnerability', 'injection', 'xss', 'csrf', 'sql injection', 
                        'secret', 'token', 'auth', 'authorization', 'permission', 'access control']
    if any(kw in combined_text for kw in security_keywords):
        return 'security'
    
    # Performance
    perf_keywords = ['performance', 'optimization', 'slow', 'bottleneck', 'cache', 'query optimization',
                     'n+1', 'eager loading', 'lazy loading', 'index']
    if any(kw in combined_text for kw in perf_keywords):
        return 'performance'
    
    # Tests
    test_keywords = ['test', 'spec', 'coverage', 'mock', 'fixture', 'assert', 'pytest', 'unittest',
                     'integration test', 'unit test']
    if any(kw in combined_text for kw in test_keywords):
        return 'tests'
    
    # Infrastructure
    infra_keywords = ['docker', 'dockerfile', 'docker-compose', 'kubernetes', 'k8s', 'deploy', 'ci/cd',
                      'github actions', 'gitlab ci', 'jenkins', 'migration', 'config', 'env']
    if any(kw in combined_text for kw in infra_keywords):
        return 'infrastructure'
    
    # Refactoring
    refactor_keywords = ['refactor', 'refactoring', 'architecture', 'design pattern', 'solid', 'dry',
                         'extract', 'split', 'restructure', 'reorganize', 'cleanup']
    if any(kw in combined_text for kw in refactor_keywords):
        return 'refactoring'
    
    # Bugfix
    bugfix_keywords = ['bug', 'fix', 'error', 'issue', 'bugfix', 'correct', 'wrong', 'incorrect',
                       'null', 'none', 'exception', 'crash']
    if any(kw in combined_text for kw in bugfix_keywords):
        return 'bugfix'
    
    # Code style
    style_keywords = ['style', 'format', 'lint', 'readability', 'naming', 'clean code', 'pep8',
                      'eslint', 'prettier', 'code style']
    if any(kw in combined_text for kw in style_keywords):
        return 'code_style'
    
    # Feature (по умолчанию)
    return 'feature'


def calculate_complexity_points(mr_data: Dict[str, Any], diff_content: Optional[str] = None) -> int:
    """
    Вычислить баллы сложности (1-5) для MR
    
    Args:
        mr_data: Данные MR
        diff_content: Содержимое diff (опционально)
        
    Returns:
        Баллы сложности от 1 до 5
    """
    points = 1  # Базовый уровень
    
    # Фактор 1: Размер и разброс
    files_changed = mr_data.get('files_changed', 0)
    lines_added = mr_data.get('lines_added', 0)
    lines_deleted = mr_data.get('lines_deleted', 0)
    total_lines = lines_added + lines_deleted
    
    if files_changed <= 2 and total_lines <= 30:
        # 1-2 файла, до 30 строк
        pass  # остаётся 1 балл
    elif files_changed <= 5 and total_lines <= 150:
        # Несколько файлов, 50-150 строк
        points += 1
    elif files_changed > 5 or total_lines > 150:
        # Много файлов или большие изменения
        points += 2
    
    # Фактор 2: Тип MR
    mr_type = mr_data.get('mr_type', 'feature')
    if mr_type in ['bugfix', 'code_style']:
        # Обычно проще
        pass
    elif mr_type in ['feature', 'tests']:
        points += 1
    elif mr_type in ['refactoring', 'performance', 'security', 'infrastructure']:
        points += 1
        # Архитектурные и сложные типы могут быть ещё сложнее
        if files_changed > 3 or total_lines > 100:
            points += 1
    
    # Фактор 3: Сложность кода
    complexity_score = mr_data.get('complexity_score', 0)
    if complexity_score > 70:
        points += 1
    elif complexity_score > 50:
        # Уже учтено в размере
        pass
    
    # Ограничиваем максимум 5 баллами
    return min(5, max(1, points))


def detect_stack_tags(mr_data: Dict[str, Any], diff_content: Optional[str] = None) -> List[str]:
    """
    Определить теги стека на основе языка и содержимого
    
    Args:
        mr_data: Данные MR
        diff_content: Содержимое diff (опционально)
        
    Returns:
        Список тегов стека
    """
    tags = []
    language = (mr_data.get('language', '') or '').lower()
    languages = [l.lower() for l in (mr_data.get('languages', []) or [])]
    diff = (diff_content or '').lower()
    
    all_languages = [language] + languages
    combined_text = f"{' '.join(all_languages)} {diff}"
    
    # Определяем языки
    if any(lang in ['python', 'py'] for lang in all_languages):
        tags.append('python')
    if any(lang in ['javascript', 'js', 'typescript', 'ts'] for lang in all_languages):
        tags.append('javascript')
    if 'java' in all_languages:
        tags.append('java')
    if any(lang in ['go', 'golang'] for lang in all_languages):
        tags.append('go')
    
    # Определяем направление (backend/frontend)
    backend_keywords = ['django', 'flask', 'fastapi', 'express', 'spring', 'gin', 'api', 'endpoint',
                        'controller', 'service', 'repository', 'database', 'sql', 'orm']
    frontend_keywords = ['react', 'vue', 'angular', 'component', 'jsx', 'tsx', 'ui', 'frontend',
                         'browser', 'dom', 'css']
    
    if any(kw in combined_text for kw in backend_keywords):
        tags.append('backend')
    if any(kw in combined_text for kw in frontend_keywords):
        tags.append('frontend')
    
    # DevOps
    devops_keywords = ['docker', 'kubernetes', 'k8s', 'ci/cd', 'deploy', 'infrastructure']
    if any(kw in combined_text for kw in devops_keywords):
        tags.append('devops')
    
    # Database
    db_keywords = ['sql', 'postgres', 'mysql', 'mongodb', 'redis', 'database', 'db']
    if any(kw in combined_text for kw in db_keywords):
        tags.append('database')
    
    return list(set(tags))  # Убираем дубликаты


def classify_mr(mr_data: Dict[str, Any], diff_content: Optional[str] = None) -> Dict[str, Any]:
    """
    Полная классификация MR: тип, баллы сложности, теги стека
    
    Args:
        mr_data: Данные MR
        diff_content: Содержимое diff (опционально)
        
    Returns:
        Словарь с полями: mr_type, complexity_points, stack_tags
    """
    # Определяем тип
    mr_type = detect_mr_type(mr_data, diff_content)
    
    # Вычисляем баллы сложности
    complexity_points = calculate_complexity_points(mr_data, diff_content)
    
    # Определяем теги стека
    stack_tags = detect_stack_tags(mr_data, diff_content)
    
    return {
        'mr_type': mr_type,
        'complexity_points': complexity_points,
        'stack_tags': stack_tags
    }




