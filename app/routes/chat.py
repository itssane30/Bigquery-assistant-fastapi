import time
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agent.vertex_agent import answer_question
from app.utils.logger import get_logger

logger = get_logger(__name__)

chat_router = APIRouter()

class ChatRequest(BaseModel):
    message: str

@chat_router.post("/chat")
async def chat(body: ChatRequest):
    message = body.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Field 'message' is required.")

    logger.info(f"Incoming question: {message}")
    start = time.time()

    try:
        result = await answer_question(message)  # direct await, no asyncio.run()
    except Exception as exc:
        logger.exception("Agent failed to answer question")
        raise HTTPException(status_code=500, detail=str(exc))

    logger.info(f"Answered in {round(time.time() - start, 2)}s")
    return result