#!/usr/bin/env python3
"""
Скрипт для сбора Merge Requests из различных источников
"""
import os
import sys
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

# Добавляем путь к api модулю
# Проверяем, запущены ли мы в Docker (где /app) или на хосте
if os.path.exists('/app'):
    # В Docker контейнере
    sys.path.insert(0, '/app')
else:
    # На хосте
    sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

# Импортируем классификатор
try:
    from mr_classifier import classify_mr
except ImportError:
    # Если не можем импортировать, используем простую классификацию
    def classify_mr(mr_data, diff_content=None):
        return {
            'mr_type': mr_data.get('change_type', 'feature'),
            'complexity_points': 3,
            'stack_tags': [mr_data.get('language', 'unknown')]
        }

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def analyze_diff_complexity(diff_content: str) -> Dict[str, Any]:
    """
    Анализ сложности diff
    
    Returns:
        Словарь с метриками сложности
    """
    if not diff_content:
        return {
            "files_changed": 0,
            "lines_added": 0,
            "lines_deleted": 0,
            "diff_size": 0,
            "complexity_score": 0
        }
    
    lines = diff_content.split('\n')
    files_changed = set()
    lines_added = 0
    lines_deleted = 0
    
    for line in lines:
        if line.startswith('diff --git') or line.startswith('---') or line.startswith('+++'):
            # Извлекаем имя файла
            if line.startswith('+++'):
                file_path = line.split('+++', 1)[1].strip()
                if file_path and not file_path.startswith('/dev/null'):
                    files_changed.add(file_path)
        elif line.startswith('+') and not line.startswith('+++'):
            lines_added += 1
        elif line.startswith('-') and not line.startswith('---'):
            lines_deleted += 1
    
    # Простая оценка сложности
    total_changes = lines_added + lines_deleted
    complexity_score = min(100, (len(files_changed) * 5 + total_changes / 10))
    
    return {
        "files_changed": len(files_changed),
        "lines_added": lines_added,
        "lines_deleted": lines_deleted,
        "diff_size": len(diff_content.encode('utf-8')),
        "complexity_score": round(complexity_score, 2)
    }


def detect_language(file_path: str) -> str:
    """Определить язык программирования по расширению файла"""
    ext = Path(file_path).suffix.lower()
    language_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.java': 'java',
        '.go': 'go',
        '.cpp': 'cpp',
        '.c': 'c',
        '.rs': 'rust',
        '.php': 'php',
        '.rb': 'ruby',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.scala': 'scala',
        '.clj': 'clojure',
        '.hs': 'haskell',
        '.ml': 'ocaml',
        '.sh': 'bash',
        '.sql': 'sql'
    }
    return language_map.get(ext, 'unknown')


def determine_difficulty_level(metrics: Dict[str, Any]) -> str:
    """Определить уровень сложности на основе метрик"""
    files = metrics.get('files_changed', 0)
    lines = metrics.get('lines_added', 0) + metrics.get('lines_deleted', 0)
    complexity = metrics.get('complexity_score', 0)
    
    if files <= 3 and lines < 100 and complexity < 30:
        return 'beginner'
    elif files <= 10 and lines < 500 and complexity < 70:
        return 'intermediate'
    else:
        return 'advanced'


def collect_from_local_repo(repo_path: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Собрать MR из локального git репозитория
    
    Args:
        repo_path: Путь к репозиторию
        limit: Максимальное количество коммитов для анализа
        
    Returns:
        Список MR данных
    """
    import subprocess
    
    mrs = []
    repo_path = Path(repo_path)
    
    if not (repo_path / '.git').exists():
        logger.warning(f"Not a git repository: {repo_path}")
        return mrs
    
    try:
        # Получаем список коммитов
        result = subprocess.run(
            ['git', 'log', '--oneline', f'-{limit}'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        
        commits = result.stdout.strip().split('\n')
        
        for commit_line in commits:
            if not commit_line:
                continue
            
            commit_hash = commit_line.split()[0]
            
            # Получаем информацию о коммите
            commit_info = subprocess.run(
                ['git', 'show', '--stat', '--format=%H%n%an%n%ae%n%ad%n%s%n%b', commit_hash],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Получаем diff
            diff_result = subprocess.run(
                ['git', 'show', commit_hash],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            
            diff_content = diff_result.stdout
            
            # Анализируем метрики
            metrics = analyze_diff_complexity(diff_content)
            
            # Определяем язык (по первому изменённому файлу)
            lines = diff_content.split('\n')
            language = 'unknown'
            for line in lines:
                if line.startswith('+++'):
                    file_path = line.split('+++', 1)[1].strip()
                    if file_path and not file_path.startswith('/dev/null'):
                        language = detect_language(file_path)
                        break
            
            # Парсим информацию о коммите
            commit_lines = commit_info.stdout.split('\n')
            author = commit_lines[1] if len(commit_lines) > 1 else 'Unknown'
            date_str = commit_lines[3] if len(commit_lines) > 3 else None
            title = commit_lines[4] if len(commit_lines) > 4 else commit_line
            description = '\n'.join(commit_lines[5:]) if len(commit_lines) > 5 else ''
            
            # Парсим дату
            created_at = None
            if date_str:
                try:
                    # Простой парсинг ISO формата
                    from datetime import datetime
                    # Убираем временную зону если есть
                    date_str_clean = date_str.split('+')[0].split('-')[0:3]
                    if len(date_str_clean) >= 3:
                        # Пробуем разные форматы
                        try:
                            created_at = datetime.fromisoformat(date_str.replace('+', '').split()[0])
                        except:
                            pass
                except:
                    pass
            
            difficulty = determine_difficulty_level(metrics)
            
            mr_data = {
                'external_id': f'local_{commit_hash}',
                'title': title,
                'description': description,
                'url': None,
                'author': author,
                'created_at': created_at.isoformat() if created_at else None,
                'merged_at': created_at.isoformat() if created_at else None,
                'state': 'merged',
                'language': language,
                'languages': [language],
                'change_type': 'feature',  # По умолчанию
                'files_changed': metrics['files_changed'],
                'lines_added': metrics['lines_added'],
                'lines_deleted': metrics['lines_deleted'],
                'diff_size': metrics['diff_size'],
                'complexity_score': metrics['complexity_score'],
                'diff_content': diff_content,
                'difficulty_level': difficulty,
                'review_time_estimate': max(15, int(metrics['complexity_score'] / 2)),
                'tags': [],
                'metadata': {
                    'source': 'local_git',
                    'commit_hash': commit_hash,
                    'repo_path': str(repo_path)
                }
            }
            
            # Классифицируем MR
            classification = classify_mr(mr_data, diff_content)
            mr_data.update(classification)
            
            mrs.append(mr_data)
            logger.info(f"Collected MR: {title[:50]}... (type: {classification['mr_type']}, points: {classification['complexity_points']}, complexity: {metrics['complexity_score']:.1f})")
    
    except subprocess.CalledProcessError as e:
        logger.error(f"Git command failed: {e}")
    except Exception as e:
        logger.error(f"Error collecting from local repo: {e}", exc_info=True)
    
    return mrs


def collect_from_artifacts(artifacts_dir: str) -> List[Dict[str, Any]]:
    """
    Собрать MR из существующих diff файлов в artifacts
    
    Args:
        artifacts_dir: Путь к директории artifacts
        
    Returns:
        Список MR данных
    """
    mrs = []
    artifacts_path = Path(artifacts_dir)
    
    if not artifacts_path.exists():
        logger.warning(f"Artifacts directory not found: {artifacts_dir}")
        return mrs
    
    # Ищем все diff файлы
    diff_files = list(artifacts_path.glob('*_diff.patch'))
    
    for diff_file in diff_files:
        try:
            session_id = diff_file.stem.replace('_diff', '')
            
            with open(diff_file, 'r', encoding='utf-8') as f:
                diff_content = f.read()
            
            # Анализируем метрики
            metrics = analyze_diff_complexity(diff_content)
            
            # Определяем язык
            language = 'unknown'
            for line in diff_content.split('\n'):
                if line.startswith('+++'):
                    file_path = line.split('+++', 1)[1].strip()
                    if file_path and not file_path.startswith('/dev/null'):
                        language = detect_language(file_path)
                        break
            
            difficulty = determine_difficulty_level(metrics)
            
            mr_data = {
                'external_id': f'artifact_{session_id}',
                'title': f'Code Review Session #{session_id}',
                'description': f'Diff from session {session_id}',
                'url': None,
                'author': 'Unknown',
                'created_at': datetime.now().isoformat(),
                'merged_at': None,
                'state': 'open',
                'language': language,
                'languages': [language],
                'change_type': 'feature',
                'files_changed': metrics['files_changed'],
                'lines_added': metrics['lines_added'],
                'lines_deleted': metrics['lines_deleted'],
                'diff_size': metrics['diff_size'],
                'complexity_score': metrics['complexity_score'],
                'diff_content': diff_content,
                'difficulty_level': difficulty,
                'review_time_estimate': max(15, int(metrics['complexity_score'] / 2)),
                'tags': ['from_artifacts'],
                'metadata': {
                    'source': 'artifacts',
                    'session_id': session_id
                }
            }
            
            # Классифицируем MR
            classification = classify_mr(mr_data, diff_content)
            mr_data.update(classification)
            
            mrs.append(mr_data)
            logger.info(f"Collected MR from artifact: {diff_file.name} (type: {classification['mr_type']}, points: {classification['complexity_points']}, complexity: {metrics['complexity_score']:.1f})")
        
        except Exception as e:
            logger.error(f"Error processing {diff_file}: {e}", exc_info=True)
    
    return mrs


def main():
    """Основная функция сбора MR"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Collect Merge Requests from various sources')
    parser.add_argument('--output', '-o', default='mrs_collected.json', help='Output JSON file')
    parser.add_argument('--artifacts', default='./artifacts', help='Path to artifacts directory')
    parser.add_argument('--repo', help='Path to local git repository')
    parser.add_argument('--limit', type=int, default=10, help='Limit for commits/repos')
    
    args = parser.parse_args()
    
    all_mrs = []
    
    # Собираем из artifacts
    if os.path.exists(args.artifacts):
        logger.info(f"Collecting from artifacts: {args.artifacts}")
        mrs = collect_from_artifacts(args.artifacts)
        all_mrs.extend(mrs)
        logger.info(f"Collected {len(mrs)} MRs from artifacts")
    
    # Собираем из локального репозитория
    if args.repo and os.path.exists(args.repo):
        logger.info(f"Collecting from local repo: {args.repo}")
        mrs = collect_from_local_repo(args.repo, args.limit)
        all_mrs.extend(mrs)
        logger.info(f"Collected {len(mrs)} MRs from local repo")
    
    # Сохраняем в JSON
    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(all_mrs, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"Total collected: {len(all_mrs)} MRs")
    logger.info(f"Saved to: {output_path}")
    
    # Статистика
    if all_mrs:
        languages = {}
        difficulties = {}
        for mr in all_mrs:
            lang = mr.get('language', 'unknown')
            languages[lang] = languages.get(lang, 0) + 1
            diff = mr.get('difficulty_level', 'unknown')
            difficulties[diff] = difficulties.get(diff, 0) + 1
        
        logger.info(f"Languages: {languages}")
        logger.info(f"Difficulty levels: {difficulties}")


if __name__ == '__main__':
    main()

