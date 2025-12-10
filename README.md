# Code Review Platform

🚀 **Автоматизированная платформа для проведения технических интервью и code review**


### Локальный запуск (Docker)

```bash
# Клонирование репозитория
git clone <repository-url>
cd conversations

# Запуск
docker compose up -d

# Доступ
# Frontend: http://localhost:8000
# API: http://localhost:8000/api
```

### Другие варианты развертывания

Подробные инструкции: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)

---

## ✨ Основные возможности

- ✅ Автоматическое создание репозиториев в GitHub
- ✅ Асинхронная оценка кода
- ✅ Генерация PDF отчетов
- ✅ Синхронизация комментариев с GitHub
- ✅ Трекинг времени сессий
- ✅ Мониторинг производительности
- ✅ CI/CD с автоматическим тестированием и деплоем
- ✅ Автоматическая очистка старых сессий (через 2 дня)

---

## 📚 Документация

- [Описание проекта](./PROJECT_DESCRIPTION.md)
- [Краткое описание](./PROJECT_DESCRIPTION_SHORT.md)
- [Детальная презентация](./PROJECT_DESCRIPTION_DETAILED.md)
- [Руководство по развертыванию](./DEPLOYMENT_GUIDE.md)
- [CI/CD и автоматизация](./CI_CD_GUIDE.md)
- [Рабочий процесс кандидата](./CANDIDATE_WORKFLOW.md)
- [Мониторинг RQ](./RQ_PERFORMANCE_MONITORING.md)

---

## 🛠 Технологии

- **Backend**: FastAPI (Python)
- **Frontend**: React + Vite
- **База данных**: SQLite
- **Очереди**: Redis + RQ
- **Git-хостинг**: GitHub
- **Контейнеризация**: Docker


---

*Сделано с ❤️ для упрощения процесса технических интервью*


