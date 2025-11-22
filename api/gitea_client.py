# api/gitea_client.py
"""
Gitea Client для работы с Gitea REST API
"""
import requests
import logging
import secrets
from typing import Optional, Dict, List
import json

logger = logging.getLogger(__name__)

class GiteaClient:
    """Клиент для работы с Gitea REST API"""
    
    def __init__(self, base_url: str, admin_token: str):
        """
        Инициализация клиента
        
        Args:
            base_url: Базовый URL Gitea (например, http://gitea:3000)
            admin_token: API токен администратора Gitea
        """
        self.base_url = base_url.rstrip('/')
        self.token = admin_token
        self.headers = {
            "Authorization": f"token {admin_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """
        Выполнить HTTP запрос к Gitea API
        
        Args:
            method: HTTP метод (GET, POST, PATCH, DELETE)
            endpoint: Endpoint API (например, /api/v1/users)
            **kwargs: Дополнительные параметры для requests
            
        Returns:
            JSON ответ или None при ошибке
        """
        url = f"{self.base_url}/api/v1{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            
            if response.status_code == 204:  # No Content
                return {}
            
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            # Определяем уровень логирования в зависимости от статуса ошибки
            status_code = None
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
            
            # 404 ошибки логируем как debug (файл не найден - это нормально)
            if status_code == 404:
                logger.debug(f"Gitea API {method} {endpoint}: 404 Not Found (this is normal if resource doesn't exist)")
            else:
                # Другие ошибки логируем как error
                logger.error(f"Gitea API error {method} {endpoint}: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_data = e.response.json()
                        logger.error(f"Error response: {error_data}")
                    except ValueError as json_err:
                        # Если не удалось распарсить JSON, выводим сырой текст
                        logger.error(f"Error response text (not JSON): {e.response.text[:500]}")
                        logger.error(f"JSON parse error: {json_err}")
            return None
    
    def get_user(self, username: str) -> Optional[Dict]:
        """
        Получить информацию о пользователе Gitea
        
        Args:
            username: Имя пользователя
            
        Returns:
            Данные пользователя или None если не найден
        """
        result = self._request("GET", f"/users/{username}")
        return result
    
    def create_user(self, username: str, email: str, password: Optional[str] = None) -> Optional[Dict]:
        """
        Создать пользователя в Gitea (или вернуть существующего)
        
        Args:
            username: Имя пользователя
            email: Email пользователя
            password: Пароль (если None, генерируется случайный)
            
        Returns:
            Данные созданного/существующего пользователя или None при критической ошибке
        """
        # Сначала проверяем, существует ли пользователь
        existing_user = self.get_user(username)
        if existing_user:
            logger.info(f"Gitea user already exists: {username}")
            return existing_user
        
        # Пользователь не существует - создаём
        if password is None:
            password = secrets.token_urlsafe(24)
        
        payload = {
            "username": username,
            "email": email,
            "password": password,
            "must_change_password": False,
            "send_notify": False
        }
        
        result = self._request("POST", "/admin/users", json=payload)
        if result:
            logger.info(f"Created Gitea user: {username}")
        return result
    
    def create_user_token(self, username: str, token_name: str = "code_review_token") -> Optional[str]:
        """
        Создать токен доступа для пользователя
        
        Args:
            username: Имя пользователя
            token_name: Имя токена
            
        Returns:
            Токен доступа или None
        """
        payload = {
            "name": token_name
        }
        
        result = self._request("POST", f"/users/{username}/tokens", json=payload)
        if result and "sha1" in result:
            logger.info(f"Created token for user: {username}")
            return result["sha1"]
        return None
    
    def create_repository(self, owner: str, repo_name: str, description: str = "", private: bool = True) -> Optional[Dict]:
        """
        Создать репозиторий в Gitea от имени конкретного пользователя
        
        Args:
            owner: Владелец репозитория (имя пользователя)
            repo_name: Имя репозитория
            description: Описание репозитория
            private: Приватный репозиторий
            
        Returns:
            Данные созданного репозитория или None
        """
        payload = {
            "name": repo_name,
            "description": description,
            "private": private,
            "auto_init": True,
            "default_branch": "main"
        }
        
        # Используем admin API для создания репозитория от имени пользователя
        result = self._request("POST", f"/admin/users/{owner}/repos", json=payload)
        if result:
            logger.info(f"Created repository: {owner}/{repo_name}")
        return result
    
    def create_file(self, owner: str, repo: str, file_path: str, content: str, message: str = "Initial commit", branch: str = "main", new_branch: bool = True) -> Optional[Dict]:
        """
        Создать файл в репозитории
        
        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            file_path: Путь к файлу в репозитории
            content: Содержимое файла (будет закодировано в base64)
            message: Сообщение коммита
            branch: Ветка
            new_branch: Создать новую ветку, если её нет (для пустых репозиториев)
            
        Returns:
            Данные созданного файла или None
        """
        import base64
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        # Gitea API требует author и committer для создания файлов
        # Используем системного пользователя (admin) как автора
        payload = {
            "content": content_b64,
            "message": message,
            "branch": branch,
            "author": {
                "name": "Code Review System",
                "email": "noreply@code-review.local"
            },
            "committer": {
                "name": "Code Review System",
                "email": "noreply@code-review.local"
            }
        }
        
        # new_branch не является стандартным полем Gitea API v1
        # Вместо этого просто указываем branch - Gitea создаст его автоматически если нужно
        
        result = self._request("POST", f"/repos/{owner}/{repo}/contents/{file_path}", json=payload)
        if result:
            logger.info(f"Created file: {owner}/{repo}/{file_path}")
        return result
    
    def create_branch(self, owner: str, repo: str, branch_name: str, from_branch: str = "main") -> Optional[Dict]:
        """
        Создать новую ветку от существующей
        
        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            branch_name: Имя новой ветки
            from_branch: Исходная ветка (по умолчанию main)
            
        Returns:
            Информация о созданной ветке или None
        """
        # Сначала пробуем создать ветку просто указав имя исходной ветки
        # Gitea API поддерживает создание ветки по имени без SHA
        payload = {
            "new_branch_name": branch_name,
            "old_branch_name": from_branch
        }
        
        # Пробуем создать ветку
        result = self._request("POST", f"/repos/{owner}/{repo}/branches", json=payload)
        
        # Если не получилось, пробуем получить SHA и использовать его
        if not result:
            logger.info(f"Failed to create branch with name only, trying with SHA...")
            branch_info = self._request("GET", f"/repos/{owner}/{repo}/branches/{from_branch}")
            if branch_info:
                logger.info(f"Branch info structure: {branch_info}")
                
                # Пробуем разные варианты структуры ответа Gitea
                commit_sha = None
                if isinstance(branch_info, dict):
                    # Вариант 1: branch_info["commit"]["sha"] или branch_info["commit"]["id"]
                    commit = branch_info.get("commit")
                    if commit and isinstance(commit, dict):
                        commit_sha = commit.get("sha") or commit.get("id")
                    
                    # Вариант 2: branch_info["commit_sha"] или branch_info["sha"]
                    if not commit_sha:
                        commit_sha = branch_info.get("commit_sha") or branch_info.get("sha")
                    
                    # Вариант 3: branch_info["commit"] - строка (SHA напрямую)
                    if not commit_sha and isinstance(commit, str):
                        commit_sha = commit
                
                if commit_sha:
                    logger.info(f"Found commit SHA: {commit_sha}")
                    payload = {
                        "new_branch_name": branch_name,
                        "old_branch_name": from_branch,
                        "old_ref_name": commit_sha
                    }
                    result = self._request("POST", f"/repos/{owner}/{repo}/branches", json=payload)
                else:
                    logger.error(f"Failed to get commit SHA for branch {from_branch}. Branch info: {branch_info}")
            else:
                logger.error(f"Failed to get branch info for {from_branch}")
        
        if result:
            logger.info(f"Created branch: {owner}/{repo}/{branch_name}")
        else:
            logger.error(f"Failed to create branch {branch_name} from {from_branch}")
        return result
    
    def get_file_info(self, owner: str, repo: str, file_path: str, branch: str = "main") -> Optional[Dict]:
        """
        Получить информацию о файле в репозитории
        
        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            file_path: Путь к файлу
            branch: Ветка
            
        Returns:
            Информация о файле (включая SHA) или None если файл не существует
        """
        try:
            result = self._request("GET", f"/repos/{owner}/{repo}/contents/{file_path}", params={"ref": branch})
            return result if result and isinstance(result, dict) else None
        except Exception as e:
            # Файл не существует или другая ошибка
            logger.debug(f"File {file_path} not found or error: {e}")
            return None
    
    def update_file(self, owner: str, repo: str, file_path: str, content: str, message: str = "Update file", branch: str = "main", sha: str = None) -> Optional[Dict]:
        """
        Обновить файл в репозитории
        
        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            file_path: Путь к файлу
            content: Новое содержимое файла
            message: Сообщение коммита
            branch: Ветка
            sha: SHA текущего файла (обязательно для обновления)
            
        Returns:
            Данные обновлённого файла или None
        """
        import base64
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        if not sha:
            # Получаем SHA текущего файла
            file_info = self._request("GET", f"/repos/{owner}/{repo}/contents/{file_path}", params={"ref": branch})
            if file_info and isinstance(file_info, dict):
                sha = file_info.get("sha")
            else:
                logger.error(f"Failed to get file SHA for {file_path}")
                return None
        
        payload = {
            "content": content_b64,
            "message": message,
            "branch": branch,
            "sha": sha,
            "author": {
                "name": "Code Review System",
                "email": "noreply@code-review.local"
            },
            "committer": {
                "name": "Code Review System",
                "email": "noreply@code-review.local"
            }
        }
        
        result = self._request("PUT", f"/repos/{owner}/{repo}/contents/{file_path}", json=payload)
        if result:
            logger.info(f"Updated file: {owner}/{repo}/{file_path} in branch {branch}")
        return result
    
    def create_pull_request(self, owner: str, repo: str, title: str, body: str, head: str, base: str = "main") -> Optional[Dict]:
        """
        Создать Pull Request
        
        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            title: Заголовок PR
            body: Описание PR
            head: Исходная ветка (например, candidate_15:feature/candidate_work или просто feature/candidate_work)
            base: Целевая ветка (по умолчанию main)
            
        Returns:
            Данные созданного PR или None
        """
        # Если head не содержит owner, добавляем его
        if ":" not in head:
            head = f"{owner}:{head}"
        
        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": base
        }
        
        result = self._request("POST", f"/repos/{owner}/{repo}/pulls", json=payload)
        if result:
            logger.info(f"Created PR: {owner}/{repo} #{result.get('number')}")
        return result
    
    def get_pull_request(self, owner: str, repo: str, pr_index: int) -> Optional[Dict]:
        """
        Получить данные Pull Request
        
        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            pr_index: Номер PR
            
        Returns:
            Данные PR или None
        """
        result = self._request("GET", f"/repos/{owner}/{repo}/pulls/{pr_index}")
        return result
    
    def get_pull_request_diff(self, owner: str, repo: str, pr_index: int) -> Optional[str]:
        """
        Получить diff Pull Request
        
        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            pr_index: Номер PR
            
        Returns:
            Diff в текстовом формате или None
        """
        url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/pulls/{pr_index}.diff"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting PR diff: {e}")
            return None
    
    def get_pull_request_comments(self, owner: str, repo: str, pr_index: int) -> List[Dict]:
        """
        Получить review comments (комментарии к строкам кода) к Pull Request
        Использует несколько стратегий для получения всех комментариев
        """
        all_comments = []
        
        # Способ 1: Получаем все reviews и их комментарии
        reviews_url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/pulls/{pr_index}/reviews"
        try:
            reviews_response = requests.get(reviews_url, headers=self.headers)
            if reviews_response.status_code == 200:
                reviews = reviews_response.json() if reviews_response.content else []
                logger.info(f"Found {len(reviews)} reviews for PR {owner}/{repo}#{pr_index}")
                
                # Собираем все комментарии из всех reviews
                for review in reviews:
                    review_id = review.get("id")
                    
                    # Проверяем, есть ли комментарии прямо в структуре review
                    if "comments" in review and isinstance(review["comments"], list):
                        logger.info(f"Found {len(review['comments'])} comments directly in review {review_id}")
                        all_comments.extend(review["comments"])
                    
                    # Также пробуем получить комментарии через отдельный endpoint
                    if review_id:
                        comments_url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/pulls/{pr_index}/reviews/{review_id}/comments"
                        try:
                            comments_response = requests.get(comments_url, headers=self.headers)
                            if comments_response.status_code == 200:
                                review_comments = comments_response.json() if comments_response.content else []
                                logger.info(f"Found {len(review_comments)} comments via review comments endpoint for review {review_id}")
                                # Объединяем, избегая дубликатов
                                existing_ids = {c.get("id") for c in all_comments if c.get("id")}
                                for comment in review_comments:
                                    if comment.get("id") not in existing_ids:
                                        all_comments.append(comment)
                        except requests.exceptions.RequestException as e:
                            logger.warning(f"Failed to get comments for review {review_id}: {e}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get reviews: {e}")
        
        # Способ 2: Получаем файлы PR и комментарии к ним
        # В Gitea review comments могут быть привязаны к файлам
        files_url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/pulls/{pr_index}/files"
        try:
            files_response = requests.get(files_url, headers=self.headers)
            if files_response.status_code == 200:
                files = files_response.json() if files_response.content else []
                logger.info(f"Found {len(files)} files in PR {owner}/{repo}#{pr_index}")
                
                # Проверяем, есть ли комментарии в структуре файлов
                for file_info in files:
                    if "comments" in file_info and isinstance(file_info["comments"], list):
                        file_comments = file_info["comments"]
                        logger.info(f"Found {len(file_comments)} comments in file {file_info.get('filename', 'unknown')}")
                        # Объединяем, избегая дубликатов
                        existing_ids = {c.get("id") for c in all_comments if c.get("id")}
                        for comment in file_comments:
                            if comment.get("id") not in existing_ids:
                                all_comments.append(comment)
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get PR files: {e}")
        
        # Способ 3: Пробуем получить комментарии напрямую (может работать в некоторых версиях Gitea)
        # Используем _request для консистентного логирования (404 будет логироваться как debug)
        direct_comments_result = self._request("GET", f"/repos/{owner}/{repo}/pulls/{pr_index}/comments")
        if direct_comments_result and isinstance(direct_comments_result, list):
            logger.info(f"Found {len(direct_comments_result)} comments via direct endpoint")
            # Объединяем, избегая дубликатов
            existing_ids = {c.get("id") for c in all_comments if c.get("id")}
            for comment in direct_comments_result:
                if comment.get("id") not in existing_ids:
                    all_comments.append(comment)
        
        logger.info(f"Total review comments found: {len(all_comments)}")
        if all_comments:
            logger.info(f"Sample comment structure: {json.dumps(all_comments[0], indent=2)}")
        
        return all_comments
    
    def get_pull_request_issue_comments(self, owner: str, repo: str, pr_index: int) -> List[Dict]:
        """
        Получить общие комментарии к Pull Request (issue comments, не review comments)
        
        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            pr_index: Номер PR (в Gitea PR - это тоже issue)
            
        Returns:
            Список комментариев
        """
        # В Gitea PR - это issue, поэтому используем issue comments endpoint
        url = f"{self.base_url}/api/v1/repos/{owner}/{repo}/issues/{pr_index}/comments"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            return response.json() if response.content else []
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code != 404:
                logger.error(f"Gitea API error GET /repos/{owner}/{repo}/issues/{pr_index}/comments: {e}")
            return []
    
    def create_pull_request_comment(self, owner: str, repo: str, pr_index: int, body: str, 
                                   path: str, line: int, side: str = "RIGHT") -> Optional[Dict]:
        """
        Добавить комментарий к Pull Request
        
        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            pr_index: Номер PR
            body: Текст комментария
            path: Путь к файлу
            line: Номер строки
            side: Сторона (LEFT или RIGHT, по умолчанию RIGHT)
            
        Returns:
            Данные созданного комментария или None
        """
        payload = {
            "body": body,
            "path": path,
            "line": line,
            "side": side
        }
        
        result = self._request("POST", f"/repos/{owner}/{repo}/pulls/{pr_index}/comments", json=payload)
        if result:
            logger.info(f"Created PR comment: {owner}/{repo} PR#{pr_index}")
        return result
    
    def merge_pull_request(self, owner: str, repo: str, pr_index: int, merge_type: str = "merge") -> Optional[Dict]:
        """
        Слить Pull Request
        
        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            pr_index: Номер PR
            merge_type: Тип слияния (merge, rebase, squash)
            
        Returns:
            Результат слияния или None
        """
        payload = {
            "Do": merge_type
        }
        
        result = self._request("POST", f"/repos/{owner}/{repo}/pulls/{pr_index}/merge", json=payload)
        if result:
            logger.info(f"Merged PR: {owner}/{repo} PR#{pr_index}")
        return result
    
    def close_pull_request(self, owner: str, repo: str, pr_index: int) -> Optional[Dict]:
        """
        Закрыть Pull Request
        
        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            pr_index: Номер PR
            
        Returns:
            Обновлённые данные PR или None
        """
        payload = {
            "state": "closed"
        }
        
        result = self._request("PATCH", f"/repos/{owner}/{repo}/pulls/{pr_index}", json=payload)
        if result:
            logger.info(f"Closed PR: {owner}/{repo} PR#{pr_index}")
        return result
    
    def get_repository_clone_url(self, owner: str, repo: str, protocol: str = "http") -> str:
        """
        Получить URL для клонирования репозитория
        
        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            protocol: Протокол (http или ssh)
            
        Returns:
            URL для клонирования
        """
        if protocol == "ssh":
            return f"git@{self.base_url.replace('http://', '').replace('https://', '')}:{owner}/{repo}.git"
        else:
            # HTTP с токеном для доступа
            return f"{self.base_url}/{owner}/{repo}.git"

