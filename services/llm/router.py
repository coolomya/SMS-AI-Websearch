# services/llm/router.py
import logging
from services.llm.openai_svc import OpenAIService
from services.llm.ollama_svc import OllamaService
from services.llm.base import BaseLLMService

logger = logging.getLogger("search_assistant")

class LLMRouter(BaseLLMService):
    def __init__(self):
        self.primary = OpenAIService()
        self.fallback = OllamaService()

    async def generate_sms(self, query: str, context: str) -> str:
        try:
            logger.info("Attempting generation via Primary LLM (OpenAI)...")
            return await self.primary.generate_sms(query, context)
        except Exception as e:
            logger.warning(f"Primary LLM failed: {e}. Cascading down to Fallback LLM (Ollama)...")
            return await self.fallback.generate_sms(query, context)

    async def evaluate_quality(self, query: str, content: str) -> bool:
        try:
            logger.info("Evaluating via Primary LLM (OpenAI)...")
            return await self.primary.evaluate_quality(query, content)
        except Exception as e:
            # FIX: Fallback to local Ollama judge if OpenAI URL breaks or errors out
            logger.warning(f"Primary evaluation failed: {e}. Diverting evaluation to local Ollama...")
            return await self.fallback.evaluate_quality(query, content)

    async def generate_from_knowledge_base(self, query: str) -> tuple[str, dict]:
        try:
            logger.info("Attempting Knowledge Base recovery pass via Primary LLM (OpenAI)...")
            return await self.primary.generate_from_knowledge_base(query)
        except Exception as e:
            logger.warning(f"Primary Knowledge Base pass failed: {e}. Cascading down to local Ollama...")
            return await self.fallback.generate_from_knowledge_base(query)

