import logging
from openai import AsyncOpenAI
from services.llm.base import BaseLLMService
from config.settings import settings

logger = logging.getLogger("search_assistant")

class OpenAIService(BaseLLMService):
    def __init__(self):
        # Initialize official asynchronous client SDK wrapper safely
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY) if settings.OPENAI_API_KEY else None
        self.model = settings.OPENAI_MODEL
        
        if not self.client:
            logger.warning("OpenAI API token key variable is completely empty. Structural cascades will trigger fallback automatically.")

    async def generate_sms(self, query: str, context: str) -> tuple[str, dict]:        
        """Generates a concise summary under 150 characters using OpenAI SDK."""
        if not self.client:
            raise ValueError("OpenAI client missing active token initialization contexts.")

        system_prompt = (
            "Summarize the provided search results to directly answer the user query. "
            "CRITICAL: The entire response must be strictly under 150 characters total. "
            "Write only one short, direct sentence. No markdown, no bolding, no extra text."
        )
        user_prompt = f"User Question: {query}\n\nSearch Context:\n{context}\n\nSMS Summary:"

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=60,
                temperature=0.3
            )
            raw_draft = response.choices.message.content.strip()
            
            # Extract native SDK token metrics
            usage = response.usage
            token_stats = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens
            }
            logger.info(f"📊 [OpenAI Usage - SMS] Prompt: {usage.prompt_tokens} | Completion: {usage.completion_tokens}")
            
            return raw_draft[:150], token_stats
        except Exception as e:
            logger.error(f"OpenAI completion library call failed: {str(e)}")
            raise e

    async def evaluate_quality(self, query: str, content: str) -> tuple[bool, dict]:
        """Evaluates content criteria requirements using an isolated OpenAI agent pass."""
        if not self.client:
            raise ValueError("OpenAI client missing active token initialization contexts.")
            
        if not content.strip():
            return False

        # FIX: Explicitly declare the system constant at the root of the execution scope block
        system_instruction = (
            "You are a strict quality control judge system. Your job is to output exactly "
            "one word and nothing else. You are forbidden from writing explanations, notes, "
            "or markdown packaging."
        )

        is_sms_draft = len(content) <= 200

        if is_sms_draft:
            judge_prompt = (
                f"Analyze the following SMS response draft against the User Query.\n\n"
                f"User Query: {query}\n"
                f"SMS Draft: {content}\n\n"
                f"CRITERIA:\n"
                f"1. Is the text written completely in English?\n"
                f"2. Does it provide a meaningful, positive response or direct answer to the user's intent? "
                f"(Note: The query may contain typos or misspellings. If the search context corrected the term "
                f"and the SMS accurately answers the intended question, consider this criterion MET).\n"
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
                f"1. Does the content contain text that could help answer the query's core intent (accounting for potential user typos)?\n"
                f"2. Is the content written primarily in English?\n\n"
                f"If BOTH criteria are met, output: TRUE\n"
                f"If either criterion fails, output: FALSE"
            )

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_instruction},
                    {"role": "user", "content": judge_prompt}
                ],
                max_tokens=10,
                temperature=0.0
            )
            verdict = response.choices.message.content.strip().upper()
            
            # Extract native SDK token metrics
            usage = response.usage
            token_stats = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens
            }
            logger.info(f"📊 [OpenAI Usage - Judge] Prompt: {usage.prompt_tokens} | Completion: {usage.completion_tokens}")
            
            return "TRUE" in verdict, token_stats
        except Exception as e:
            logger.error(f"OpenAI library evaluation call failed: {str(e)}")
            raise e
