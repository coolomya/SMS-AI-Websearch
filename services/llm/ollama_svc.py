import logging
import ollama
import asyncio
from services.llm.base import BaseLLMService
from config.settings import settings

logger = logging.getLogger("search_assistant")

class OllamaService(BaseLLMService):
    def __init__(self):
        self.model = settings.OLLAMA_MODEL

    async def generate_sms(self, query: str, context: str) -> tuple[str, dict]:
        """Generates a concise summary under 150 characters locally using Ollama."""
        system_prompt = (
            "Summarize the provided search results to directly answer the user query. "
            "CRITICAL: The entire response must be strictly under 150 characters total. "
            "Write only one short, direct sentence. No markdown, no bolding, no extra text."
        )
        user_prompt = f"User Question: {query}\n\nSearch Context:\n{context}\n\nSMS Summary:"

        # Offload blocking synchronous Ollama IO operations onto an async-safe event executor loop thread
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None, 
                lambda: ollama.generate(model=self.model, system=system_prompt, prompt=user_prompt)
            )
            raw_draft = response['response'].strip()
            
            # Map Ollama performance counters to uniform token keys
            token_stats = {
                "prompt_tokens": response.get("prompt_eval_count", 0),
                "completion_tokens": response.get("eval_count", 0)
            }
            logger.info(f"📊 [Ollama Usage - SMS] Prompt: {token_stats['prompt_tokens']} | Completion: {token_stats['completion_tokens']}")
            
            return raw_draft[:150], token_stats
        except Exception as e:
            logger.error(f"Local Ollama generation processing fault: {str(e)}")
            raise e

    async def evaluate_quality(self, query: str, content: str) -> bool:
        """Evaluates quality thresholds locally using the Ollama judge instructions workflow."""
        if not content.strip():
            return False

        is_sms_draft = len(content) <= 200

        system_instruction = (
            "You are a strict quality control judge system. Your job is to output exactly "
            "one word and nothing else. You are forbidden from writing explanations, notes, "
            "or markdown packaging."
        )

        if is_sms_draft:
            judge_prompt = (
                f"Analyze the following SMS response draft against the User Query.\n\n"
                f"User Query: {query}\n"
                f"SMS Draft: {content}\n\n"
                f"CRITERIA:\n"
                f"1. Is the text written completely in English?\n"
                f"2. Does it provide a meaningful, positive response or direct answer to the query?\n"
                f"3. Is it brief, concise, and under 150 characters?\n\n"
                f"If ALL criteria are met, output: TRUE\n"
                f"If it fails any criterion, output: FALSE"
            )
        else:
            judge_prompt = (
                f"Analyze the following search context against the User Query.\n\n"
                f"User Query: {query}\n"
                f"Search Context: {content}\n\n"
                f"CRITERIA:\n"
                f"1. Does the content contain text that could help answer the query?\n"
                f"2. Is the content written primarily in English?\n\n"
                f"If BOTH criteria are met, output: TRUE\n"
                f"If either criterion fails, output: FALSE"
            )

        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: ollama.generate(model=self.model, system=system_instruction, prompt=judge_prompt)
            )
            verdict = response['response'].strip().upper()
            logger.info(f"   [Ollama Judge Process] Raw response received: '{verdict}'")
            return "TRUE" in verdict
        except Exception as e:
            logger.error(f"Local Ollama verification fallback execution fault: {str(e)}")
            return False

    async def generate_from_knowledge_base(self, query: str) -> tuple[str, dict]:
        system_prompt = (
            "You are a helpful assistant answering from your internal knowledge base because live web search failed.\n"
            "CRITICAL CONSTRAINTS:\n"
            "1. Evaluate if the user query requires real-time/current information.\n"
            "2. If it requires real-time data, reply exactly with: 'Sorry, I couldn't retrieve real-time data to safely process this request.'\n"
            "3. If it is general knowledge, physics, history, or fiction (e.g., 'what is naruto'), answer directly.\n"
            "4. The entire summary answer must be strictly under 150 characters total, exactly one sentence, plain text only."
        )
        
        loop = asyncio.get_running_loop()
        try:
            response = await loop.run_in_executor(
                None,
                lambda: ollama.generate(model=self.model, system=system_prompt, prompt=f"User Query: {query}")
            )
            return response['response'].strip()[:150], {
                "prompt_tokens": response.get("prompt_eval_count", 0),
                "completion_tokens": response.get("eval_count", 0)
            }
        except Exception as e:
            logger.error(f"Ollama Knowledge Base execution failed: {str(e)}")
            raise e
