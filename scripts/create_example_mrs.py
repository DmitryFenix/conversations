#!/usr/bin/env python3
"""
Скрипт для создания примеров MR для тестирования
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta

# Добавляем путь к api модулю
if os.path.exists('/app'):
    sys.path.insert(0, '/app')
else:
    sys.path.insert(0, str(Path(__file__).parent.parent / "api"))

from mr_classifier import classify_mr

# Примеры MR с разными типами и сложностью
EXAMPLE_MRS = [
    {
        'external_id': 'example_bugfix_1',
        'title': 'Fix null pointer exception in user authentication',
        'description': 'Fixed a critical bug where the application crashed when user object was null during authentication. Added proper null checks and error handling.',
        'url': None,
        'author': 'John Doe',
        'created_at': (datetime.now() - timedelta(days=5)).isoformat(),
        'merged_at': (datetime.now() - timedelta(days=4)).isoformat(),
        'state': 'merged',
        'language': 'python',
        'languages': ['python'],
        'change_type': 'bugfix',
        'files_changed': 2,
        'lines_added': 15,
        'lines_deleted': 8,
        'diff_size': 500,
        'complexity_score': 25.0,
        'diff_content': '''diff --git a/auth.py b/auth.py
index abc123..def456 100644
--- a/auth.py
+++ b/auth.py
@@ -10,6 +10,10 @@ def authenticate_user(username, password):
     if not username or not password:
         return None
     
+    # Fix: Add null check for user object
+    user = get_user_by_username(username)
+    if user is None:
+        return None
+    
     if user.check_password(password):
         return user
     return None
''',
        'difficulty_level': 'beginner',
        'review_time_estimate': 15,
        'tags': [],
        'metadata': {'source': 'example'}
    },
    {
        'external_id': 'example_feature_2',
        'title': 'Add user profile editing functionality',
        'description': 'Implemented user profile editing with validation. Added new API endpoints for updating user information, email verification, and password change.',
        'url': None,
        'author': 'Jane Smith',
        'created_at': (datetime.now() - timedelta(days=10)).isoformat(),
        'merged_at': (datetime.now() - timedelta(days=8)).isoformat(),
        'state': 'merged',
        'language': 'python',
        'languages': ['python'],
        'change_type': 'feature',
        'files_changed': 5,
        'lines_added': 180,
        'lines_deleted': 20,
        'diff_size': 3500,
        'complexity_score': 55.0,
        'diff_content': '''diff --git a/api/users.py b/api/users.py
index xyz789..abc123 100644
--- a/api/users.py
+++ b/api/users.py
@@ -1,5 +1,8 @@
 from fastapi import APIRouter, Depends
+from pydantic import EmailStr
+from sqlalchemy.orm import Session
 
+router = APIRouter(prefix="/users", tags=["users"])
 
+@router.put("/profile")
+async def update_profile(
+    email: EmailStr,
+    full_name: str,
+    db: Session = Depends(get_db)
+):
+    user = get_current_user(db)
+    user.email = email
+    user.full_name = full_name
+    db.commit()
+    return {"message": "Profile updated"}
''',
        'difficulty_level': 'intermediate',
        'review_time_estimate': 30,
        'tags': [],
        'metadata': {'source': 'example'}
    },
    {
        'external_id': 'example_refactoring_3',
        'title': 'Refactor authentication service to use dependency injection',
        'description': 'Refactored authentication service to follow SOLID principles. Extracted interfaces, implemented dependency injection pattern, improved testability.',
        'url': None,
        'author': 'Bob Johnson',
        'created_at': (datetime.now() - timedelta(days=15)).isoformat(),
        'merged_at': (datetime.now() - timedelta(days=12)).isoformat(),
        'state': 'merged',
        'language': 'python',
        'languages': ['python'],
        'change_type': 'refactoring',
        'files_changed': 8,
        'lines_added': 250,
        'lines_deleted': 180,
        'diff_size': 6000,
        'complexity_score': 75.0,
        'diff_content': '''diff --git a/services/auth_service.py b/services/auth_service.py
index old123..new456 100644
--- a/services/auth_service.py
+++ b/services/auth_service.py
@@ -1,20 +1,35 @@
-class AuthService:
-    def __init__(self):
-        self.db = Database()
-        self.cache = RedisCache()
+from abc import ABC, abstractmethod
+
+class IUserRepository(ABC):
+    @abstractmethod
+    def get_user(self, username: str):
+        pass
+
+class AuthService:
+    def __init__(self, user_repo: IUserRepository, cache: ICache):
+        self.user_repo = user_repo
+        self.cache = cache
     
     def authenticate(self, username, password):
-        user = self.db.get_user(username)
+        user = self.user_repo.get_user(username)
         if user and user.check_password(password):
-            self.cache.set(f"auth:{username}", user)
+            self.cache.set(f"auth:{username}", user)
             return user
         return None
''',
        'difficulty_level': 'advanced',
        'review_time_estimate': 45,
        'tags': [],
        'metadata': {'source': 'example'}
    },
    {
        'external_id': 'example_tests_4',
        'title': 'Add unit tests for payment processing module',
        'description': 'Added comprehensive unit tests for payment processing. Coverage increased from 45% to 85%. Tests include edge cases and error scenarios.',
        'url': None,
        'author': 'Alice Brown',
        'created_at': (datetime.now() - timedelta(days=7)).isoformat(),
        'merged_at': (datetime.now() - timedelta(days=6)).isoformat(),
        'state': 'merged',
        'language': 'python',
        'languages': ['python'],
        'change_type': 'tests',
        'files_changed': 3,
        'lines_added': 200,
        'lines_deleted': 5,
        'diff_size': 4500,
        'complexity_score': 40.0,
        'diff_content': '''diff --git a/tests/test_payments.py b/tests/test_payments.py
new file mode 100644
index 0000000..abc123
--- /dev/null
+++ b/tests/test_payments.py
@@ -0,0 +1,50 @@
+import pytest
+from unittest.mock import Mock, patch
+from services.payment import PaymentProcessor
+
+@pytest.fixture
+def payment_processor():
+    return PaymentProcessor()
+
+def test_successful_payment(payment_processor):
+    result = payment_processor.process(amount=100, card="1234567890")
+    assert result.success == True
+    assert result.amount == 100
+
+def test_insufficient_funds(payment_processor):
+    with patch('services.payment.BankAPI') as mock_bank:
+        mock_bank.return_value.charge.side_effect = InsufficientFundsError()
+        result = payment_processor.process(amount=1000, card="1234567890")
+        assert result.success == False
+        assert "insufficient" in result.error.lower()
+
+def test_invalid_card_number(payment_processor):
+    result = payment_processor.process(amount=100, card="invalid")
+    assert result.success == False
+    assert "invalid" in result.error.lower()
''',
        'difficulty_level': 'intermediate',
        'review_time_estimate': 25,
        'tags': [],
        'metadata': {'source': 'example'}
    },
    {
        'external_id': 'example_performance_5',
        'title': 'Optimize database queries with eager loading',
        'description': 'Fixed N+1 query problem in user list endpoint. Implemented eager loading for related objects, reduced query count from 150+ to 3 queries per request.',
        'url': None,
        'author': 'Charlie Wilson',
        'created_at': (datetime.now() - timedelta(days=12)).isoformat(),
        'merged_at': (datetime.now() - timedelta(days=10)).isoformat(),
        'state': 'merged',
        'language': 'python',
        'languages': ['python'],
        'change_type': 'performance',
        'files_changed': 4,
        'lines_added': 45,
        'lines_deleted': 30,
        'diff_size': 1800,
        'complexity_score': 50.0,
        'diff_content': '''diff --git a/api/users.py b/api/users.py
index old123..new456 100644
--- a/api/users.py
+++ b/api/users.py
@@ -5,7 +5,7 @@ from sqlalchemy.orm import Session
 @router.get("/users")
 async def list_users(db: Session = Depends(get_db)):
-    users = db.query(User).all()
+    users = db.query(User).options(joinedload(User.profile), joinedload(User.orders)).all()
     return [{"id": u.id, "name": u.name, "profile": u.profile.email, "orders_count": len(u.orders)} for u in users]
''',
        'difficulty_level': 'intermediate',
        'review_time_estimate': 20,
        'tags': [],
        'metadata': {'source': 'example'}
    },
    {
        'external_id': 'example_security_6',
        'title': 'Fix SQL injection vulnerability in search endpoint',
        'description': 'Fixed critical SQL injection vulnerability. Replaced string concatenation with parameterized queries. Added input validation and sanitization.',
        'url': None,
        'author': 'David Lee',
        'created_at': (datetime.now() - timedelta(days=3)).isoformat(),
        'merged_at': (datetime.now() - timedelta(days=2)).isoformat(),
        'state': 'merged',
        'language': 'python',
        'languages': ['python'],
        'change_type': 'security',
        'files_changed': 2,
        'lines_added': 25,
        'lines_deleted': 15,
        'diff_size': 800,
        'complexity_score': 35.0,
        'diff_content': '''diff --git a/api/search.py b/api/search.py
index old123..new456 100644
--- a/api/search.py
+++ b/api/search.py
@@ -3,5 +3,8 @@ from sqlalchemy import text
 @router.get("/search")
 async def search(query: str, db: Session = Depends(get_db)):
-    sql = f"SELECT * FROM products WHERE name LIKE '%{query}%'"
-    result = db.execute(text(sql))
+    # Fix: Use parameterized query to prevent SQL injection
+    sql = "SELECT * FROM products WHERE name LIKE :pattern"
+    pattern = f"%{query}%"
+    result = db.execute(text(sql), {"pattern": pattern})
     return result.fetchall()
''',
        'difficulty_level': 'intermediate',
        'review_time_estimate': 20,
        'tags': [],
        'metadata': {'source': 'example'}
    },
    {
        'external_id': 'example_infrastructure_7',
        'title': 'Add Docker Compose configuration for local development',
        'description': 'Added Docker Compose setup with PostgreSQL, Redis, and application services. Includes health checks and volume mounts for hot reload.',
        'url': None,
        'author': 'Emma Davis',
        'created_at': (datetime.now() - timedelta(days=20)).isoformat(),
        'merged_at': (datetime.now() - timedelta(days=18)).isoformat(),
        'state': 'merged',
        'language': 'yaml',
        'languages': ['yaml'],
        'change_type': 'infrastructure',
        'files_changed': 3,
        'lines_added': 120,
        'lines_deleted': 0,
        'diff_size': 2500,
        'complexity_score': 30.0,
        'diff_content': '''diff --git a/docker-compose.yml b/docker-compose.yml
new file mode 100644
index 0000000..abc123
--- /dev/null
+++ b/docker-compose.yml
@@ -0,0 +1,40 @@
+version: '3.8'
+services:
+  api:
+    build: .
+    ports:
+      - "8000:8000"
+    environment:
+      - DATABASE_URL=postgresql://user:pass@postgres:5432/db
+    depends_on:
+      - postgres
+      - redis
+  
+  postgres:
+    image: postgres:15
+    environment:
+      - POSTGRES_DB=db
+      - POSTGRES_USER=user
+      - POSTGRES_PASSWORD=pass
+    volumes:
+      - postgres_data:/var/lib/postgresql/data
+  
+  redis:
+    image: redis:7-alpine
+    ports:
+      - "6379:6379"
+
+volumes:
+  postgres_data:
''',
        'difficulty_level': 'beginner',
        'review_time_estimate': 15,
        'tags': [],
        'metadata': {'source': 'example'}
    },
    {
        'external_id': 'example_code_style_8',
        'title': 'Fix code style issues and improve readability',
        'description': 'Fixed PEP8 violations, improved variable naming, added docstrings. No functional changes, only code quality improvements.',
        'url': None,
        'author': 'Frank Miller',
        'created_at': (datetime.now() - timedelta(days=6)).isoformat(),
        'merged_at': (datetime.now() - timedelta(days=5)).isoformat(),
        'state': 'merged',
        'language': 'python',
        'languages': ['python'],
        'change_type': 'code_style',
        'files_changed': 6,
        'lines_added': 30,
        'lines_deleted': 25,
        'diff_size': 1200,
        'complexity_score': 15.0,
        'diff_content': '''diff --git a/utils/helpers.py b/utils/helpers.py
index old123..new456 100644
--- a/utils/helpers.py
+++ b/utils/helpers.py
@@ -1,5 +1,8 @@
-def proc_data(d):
-    return d*2
+def process_data(data: float) -> float:
+    """
+    Process input data by doubling its value.
+    
+    Args:
+        data: Input numeric value
+    
+    Returns:
+        Doubled value
+    """
+    return data * 2
''',
        'difficulty_level': 'beginner',
        'review_time_estimate': 10,
        'tags': [],
        'metadata': {'source': 'example'}
    },
    {
        'external_id': 'example_javascript_9',
        'title': 'Add React component for user dashboard',
        'description': 'Created new React component for user dashboard with real-time data updates. Includes charts, statistics, and user activity feed.',
        'url': None,
        'author': 'Grace Taylor',
        'created_at': (datetime.now() - timedelta(days=9)).isoformat(),
        'merged_at': (datetime.now() - timedelta(days=7)).isoformat(),
        'state': 'merged',
        'language': 'javascript',
        'languages': ['javascript', 'typescript'],
        'change_type': 'feature',
        'files_changed': 7,
        'lines_added': 350,
        'lines_deleted': 50,
        'diff_size': 8000,
        'complexity_score': 65.0,
        'diff_content': '''diff --git a/src/components/Dashboard.tsx b/src/components/Dashboard.tsx
new file mode 100644
index 0000000..abc123
--- /dev/null
+++ b/src/components/Dashboard.tsx
@@ -0,0 +1,80 @@
+import React, { useState, useEffect } from 'react';
+import { LineChart, BarChart } from 'recharts';
+
+interface DashboardProps {
+  userId: string;
+}
+
+export const Dashboard: React.FC<DashboardProps> = ({ userId }) => {
+  const [stats, setStats] = useState(null);
+  const [loading, setLoading] = useState(true);
+
+  useEffect(() => {
+    fetch(`/api/users/${userId}/stats`)
+      .then(res => res.json())
+      .then(data => {
+        setStats(data);
+        setLoading(false);
+      });
+  }, [userId]);
+
+  if (loading) return <div>Loading...</div>;
+
+  return (
+    <div className="dashboard">
+      <h1>User Dashboard</h1>
+      <LineChart data={stats.activity} />
+      <BarChart data={stats.performance} />
+    </div>
+  );
+};
''',
        'difficulty_level': 'intermediate',
        'review_time_estimate': 35,
        'tags': [],
        'metadata': {'source': 'example'}
    },
    {
        'external_id': 'example_senior_10',
        'title': 'Implement microservices architecture with event-driven communication',
        'description': 'Major refactoring: split monolithic application into microservices. Implemented event bus using RabbitMQ, added service discovery, API gateway pattern.',
        'url': None,
        'author': 'Henry Adams',
        'created_at': (datetime.now() - timedelta(days=25)).isoformat(),
        'merged_at': (datetime.now() - timedelta(days=20)).isoformat(),
        'state': 'merged',
        'language': 'python',
        'languages': ['python', 'yaml'],
        'change_type': 'refactoring',
        'files_changed': 25,
        'lines_added': 1200,
        'lines_deleted': 800,
        'diff_size': 25000,
        'complexity_score': 95.0,
        'diff_content': '''diff --git a/services/event_bus.py b/services/event_bus.py
new file mode 100644
index 0000000..abc123
--- /dev/null
+++ b/services/event_bus.py
@@ -0,0 +1,150 @@
+"""
+Event-driven communication bus for microservices
+"""
+import pika
+from typing import Callable, Dict, Any
+import json
+
+class EventBus:
+    def __init__(self, connection_string: str):
+        self.connection = pika.BlockingConnection(
+            pika.URLParameters(connection_string)
+        )
+        self.channel = self.connection.channel()
+    
+    def publish(self, event_type: str, payload: Dict[str, Any]):
+        """Publish event to message queue"""
+        self.channel.basic_publish(
+            exchange='events',
+            routing_key=event_type,
+            body=json.dumps(payload)
+        )
+    
+    def subscribe(self, event_type: str, handler: Callable):
+        """Subscribe to event type"""
+        self.channel.queue_declare(queue=event_type)
+        self.channel.basic_consume(
+            queue=event_type,
+            on_message_callback=handler
+        )
''',
        'difficulty_level': 'advanced',
        'review_time_estimate': 90,
        'tags': [],
        'metadata': {'source': 'example'}
    }
]


def main():
    """Создать JSON файл с примерами MR"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Create example MRs for testing')
    parser.add_argument('--output', '-o', default='example_mrs.json', help='Output JSON file')
    
    args = parser.parse_args()
    
    # Классифицируем каждый MR
    classified_mrs = []
    for mr in EXAMPLE_MRS:
        # Классифицируем MR
        classification = classify_mr(mr, mr.get('diff_content', ''))
        mr.update(classification)
        classified_mrs.append(mr)
        print(f"Created MR: {mr['title'][:50]}... (type: {classification['mr_type']}, points: {classification['complexity_points']}, tags: {classification['stack_tags']})")
    
    # Сохраняем в JSON
    output_path = Path(args.output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(classified_mrs, f, indent=2, ensure_ascii=False, default=str)
    
    print(f"\n✅ Created {len(classified_mrs)} example MRs")
    print(f"📁 Saved to: {output_path}")
    print(f"\n💡 To import into database, run:")
    print(f"   docker compose exec api python scripts/import_mrs.py {output_path}")


if __name__ == '__main__':
    main()

