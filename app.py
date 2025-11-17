from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import requests
from reportlab.pdfgen import canvas
import os

app = FastAPI()


# Pydantic модель для валидации webhook от Huntflow
class HuntflowWebhook(BaseModel):
    event: str
    candidate_id: int
    github_url: str | None = None


# Mock Huntflow API (json-server на localhost:3000)
HUNTFLOW_MOCK_API = "http://localhost:3000"


@app.post("/webhook/huntflow")
async def handle_webhook(webhook: HuntflowWebhook):
    """Обработчик webhook от Huntflow для запуска code review"""
    if webhook.event != "tech_interview":
        raise HTTPException(status_code=400, detail="Invalid event")

    # Получи данные кандидата (mock)
    candidate_data = await get_candidate(webhook.candidate_id)

    # AI-анализ кода (Grok mock)
    score = await ai_grade(candidate_data.get("github_url", ""))

    # Генерация PDF
    pdf_path = await generate_pdf(webhook.candidate_id, score)

    # Push фидбека в Huntflow (mock)
    feedback_response = await push_feedback(webhook.candidate_id, score, pdf_path)

    return {"success": True, "feedback_id": feedback_response.get("id")}


async def get_candidate(candidate_id: int):
    """Получить данные кандидата из mock Huntflow"""
    try:
        response = requests.get(f"{HUNTFLOW_MOCK_API}/candidates/{candidate_id}")
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to get candidate: {str(e)}")


async def ai_grade(github_url: str) -> str:
    """Mock AI для анализа GitHub (замени на Grok/ChatGPT free)"""
    # Здесь интегрируй Grok API или локальный анализ
    return "8/10 по SOLID"


async def generate_pdf(candidate_id: int, score: str) -> str:
    """Генерация PDF с фидбеком (как 'интервьюилка' тим-лида)"""
    pdf_path = f"feedback_{candidate_id}.pdf"
    p = canvas.Canvas(pdf_path)
    p.drawString(100, 750, f"Candidate ID: {candidate_id}")
    p.drawString(100, 700, f"Code Review Score: {score}")
    p.drawString(100, 650, "Comment: Strong in React, improve SOLID principles")
    p.save()
    return pdf_path


async def push_feedback(candidate_id: int, score: str, pdf_path: str):
    """Push фидбека в Huntflow (mock)"""
    try:
        feedback_data = {
            "candidate_id": candidate_id,
            "text": f"Code review: {score}",
            "attached_pdf": pdf_path
        }
        response = requests.post(f"{HUNTFLOW_MOCK_API}/feedback", json=feedback_data)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Failed to push feedback: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)