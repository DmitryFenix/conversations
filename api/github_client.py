# api/github_client.py
"""
GitHub Client для работы с GitHub REST API
"""
import requests
import logging
import secrets
from typing import Optional, Dict, List
import json
import base64

logger = logging.getLogger(__name__)

class GitHubClient:
    """Клиент для работы с GitHub REST API"""
    
    def __init__(self, token: str, organization: Optional[str] = None):
        """
        Инициализация клиента
        
        Args:
            token: GitHub Personal Access Token (PAT) или GitHub App token
            organization: Название организации (опционально, если репозитории создаются в организации)
        """
        self.token = token
        self.organization = organization
        self.base_url = "https://api.github.com"
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        # Проверяем токен при инициализации
        self._verify_token()
    
    def _verify_token(self):
        """Проверить валидность токена"""
        try:
            response = requests.get(f"{self.base_url}/user", headers=self.headers)
            response.raise_for_status()
            user_data = response.json()
            self.username = user_data.get("login")
            logger.info(f"GitHub client initialized for user: {self.username}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to verify GitHub token: {e}")
            raise
    
    def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        """
        Выполнить HTTP запрос к GitHub API
        
        Args:
            method: HTTP метод (GET, POST, PATCH, DELETE)
            endpoint: Endpoint API (например, /user или /repos/owner/repo)
            **kwargs: Дополнительные параметры для requests
            
        Returns:
            JSON ответ или None при ошибке
        """
        url = f"{self.base_url}{endpoint}"
        try:
            response = requests.request(method, url, headers=self.headers, **kwargs)
            response.raise_for_status()
            
            if response.status_code == 204:  # No Content
                return {}
            
            return response.json() if response.content else {}
        except requests.exceptions.RequestException as e:
            status_code = None
            if hasattr(e, 'response') and e.response is not None:
                status_code = e.response.status_code
            
            if status_code == 404:
                logger.debug(f"GitHub API {method} {endpoint}: 404 Not Found")
            else:
                logger.error(f"GitHub API error {method} {endpoint}: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    try:
                        error_data = e.response.json()
                        logger.error(f"Error response: {error_data}")
                    except ValueError:
                        logger.error(f"Error response text: {e.response.text[:500]}")
            return None
    
    def get_user(self, username: str) -> Optional[Dict]:
        """
        Получить информацию о пользователе GitHub
        
        Args:
            username: Имя пользователя
            
        Returns:
            Данные пользователя или None если не найден
        """
        result = self._request("GET", f"/users/{username}")
        return result
    
    def create_user(self, username: str, email: str, password: Optional[str] = None) -> Optional[Dict]:
        """
        В GitHub нельзя создавать пользователей через API
        Вместо этого возвращаем информацию о существующем пользователе или None
        
        Args:
            username: Имя пользователя
            email: Email (не используется)
            password: Пароль (не используется)
            
        Returns:
            Данные пользователя или None
        """
        # В GitHub мы не можем создавать пользователей
        # Проверяем, существует ли пользователь
        user = self.get_user(username)
        if user:
            logger.info(f"GitHub user exists: {username}")
            return user
        else:
            logger.warning(f"GitHub user not found: {username}. Note: GitHub users must be created manually.")
            return None
    
    def create_user_token(self, username: str, token_name: str = "code_review_token") -> Optional[str]:
        """
        В GitHub нельзя создавать токены для других пользователей через API
        Возвращаем None, так как каждый пользователь должен создать свой токен
        
        Args:
            username: Имя пользователя
            token_name: Имя токена (не используется)
            
        Returns:
            None (токены создаются пользователями вручную)
        """
        logger.warning(f"Cannot create token for user {username} via GitHub API. Users must create their own tokens.")
        return None
    
    def create_repository(self, owner: str, repo_name: str, description: str = "", private: bool = True) -> Optional[Dict]:
        """
        Создать репозиторий в GitHub
        
        Args:
            owner: Владелец репозитория (имя пользователя или организации)
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
        
        # Если owner - это организация, используем /orgs/{org}/repos
        # Иначе используем /user/repos (создаст от имени текущего пользователя)
        if owner == self.username or owner == self.organization:
            if self.organization and owner == self.organization:
                endpoint = f"/orgs/{self.organization}/repos"
            else:
                endpoint = "/user/repos"
        else:
            # Не можем создать репозиторий для другого пользователя
            logger.error(f"Cannot create repository for user {owner} (not the authenticated user or organization)")
            return None
        
        result = self._request("POST", endpoint, json=payload)
        if result:
            logger.info(f"Created repository: {result.get('full_name', f'{owner}/{repo_name}')}")
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
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        payload = {
            "message": message,
            "content": content_b64,
            "branch": branch
        }
        
        result = self._request("PUT", f"/repos/{owner}/{repo}/contents/{file_path}", json=payload)
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
        # Получаем SHA коммита из исходной ветки
        branch_info = self._request("GET", f"/repos/{owner}/{repo}/git/ref/heads/{from_branch}")
        if not branch_info:
            logger.error(f"Failed to get branch info for {from_branch}")
            return None
        
        sha = branch_info.get("object", {}).get("sha")
        if not sha:
            logger.error(f"Failed to get SHA for branch {from_branch}")
            return None
        
        # Создаём новую ветку
        payload = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha
        }
        
        result = self._request("POST", f"/repos/{owner}/{repo}/git/refs", json=payload)
        if result:
            logger.info(f"Created branch: {owner}/{repo}/{branch_name}")
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
        result = self._request("GET", f"/repos/{owner}/{repo}/contents/{file_path}", params={"ref": branch})
        return result if result and isinstance(result, dict) else None
    
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
        content_b64 = base64.b64encode(content.encode('utf-8')).decode('utf-8')
        
        if not sha:
            # Получаем SHA текущего файла
            file_info = self.get_file_info(owner, repo, file_path, branch)
            if file_info:
                sha = file_info.get("sha")
            else:
                logger.error(f"Failed to get file SHA for {file_path}")
                return None
        
        payload = {
            "message": message,
            "content": content_b64,
            "branch": branch,
            "sha": sha
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
        # Если head содержит owner, убираем его (GitHub использует просто имя ветки)
        if ":" in head:
            head = head.split(":")[-1]
        
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
        url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_index}"
        try:
            response = requests.get(url, headers={**self.headers, "Accept": "application/vnd.github.v3.diff"})
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting PR diff: {e}")
            return None
    
    def get_pull_request_comments(self, owner: str, repo: str, pr_index: int) -> List[Dict]:
        """
        Получить review comments (комментарии к строкам кода) к Pull Request
        """
        all_comments = []
        
        # Получаем review comments (комментарии к строкам кода)
        comments_url = f"{self.base_url}/repos/{owner}/{repo}/pulls/{pr_index}/comments"
        try:
            response = requests.get(comments_url, headers=self.headers)
            if response.status_code == 200:
                comments = response.json() if response.content else []
                logger.info(f"Found {len(comments)} review comments for PR {owner}/{repo}#{pr_index}")
                all_comments.extend(comments)
        except requests.exceptions.RequestException as e:
            logger.warning(f"Failed to get review comments: {e}")
        
        return all_comments
    
    def get_pull_request_issue_comments(self, owner: str, repo: str, pr_index: int) -> List[Dict]:
        """
        Получить общие комментарии к Pull Request (issue comments, не review comments)
        
        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            pr_index: Номер PR
            
        Returns:
            Список комментариев
        """
        url = f"{self.base_url}/repos/{owner}/{repo}/issues/{pr_index}/comments"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 404:
                return []
            response.raise_for_status()
            return response.json() if response.content else []
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None and e.response.status_code != 404:
                logger.error(f"GitHub API error GET /repos/{owner}/{repo}/issues/{pr_index}/comments: {e}")
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
        # GitHub использует "LEFT" и "RIGHT" для side
        # Также нужно получить commit_id для комментария
        pr = self.get_pull_request(owner, repo, pr_index)
        if not pr:
            logger.error(f"Failed to get PR {pr_index} for comment")
            return None
        
        commit_id = pr.get("head", {}).get("sha")
        if not commit_id:
            logger.error(f"Failed to get commit SHA for PR {pr_index}")
            return None
        
        payload = {
            "body": body,
            "commit_id": commit_id,
            "path": path,
            "line": line,
            "side": side.lower()  # GitHub использует lowercase
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
            "merge_method": merge_type
        }
        
        result = self._request("PUT", f"/repos/{owner}/{repo}/pulls/{pr_index}/merge", json=payload)
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
    
    def get_repository_clone_url(self, owner: str, repo: str, protocol: str = "https") -> str:
        """
        Получить URL для клонирования репозитория
        
        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            protocol: Протокол (https или ssh)
            
        Returns:
            URL для клонирования
        """
        if protocol == "ssh":
            return f"git@github.com:{owner}/{repo}.git"
        else:
            # HTTPS с токеном для доступа
            return f"https://github.com/{owner}/{repo}.git"
    
    def get_repository_web_url(self, owner: str, repo: str) -> str:
        """
        Получить веб-URL репозитория
        
        Args:
            owner: Владелец репозитория
            repo: Имя репозитория
            
        Returns:
            Веб-URL репозитория
        """
        return f"https://github.com/{owner}/{repo}"

