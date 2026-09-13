import logging
from openai import AsyncOpenAI

from services.llm.base import BaseLLMService
from config.settings import settings

logger = logging.getLogger("search_assistant")


class OpenAIService(BaseLLMService):

    # ============================================================
    # MODEL CAPABILITY MAP
    # ============================================================
    #
    # Keep model-specific API differences here.
    #
    # When adding/changing a model, normally you only need to
    # update this map.
    #
    MODEL_CAPABILITIES = {

        # Legacy / older chat models
        "gpt-4o-mini": {
            "token_parameter": "max_tokens",
            "supports_temperature": True,
        },

        # Newer GPT-5.x model
        "gpt-5.6-luna": {
            "token_parameter": "max_completion_tokens",
            "supports_temperature": False,
        },
    }

    def __init__(self):
        self.client = (
            AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
            if settings.OPENAI_API_KEY
            else None
        )

        self.model = settings.OPENAI_MODEL

        if not self.client:
            logger.warning(
                "OpenAI API token key variable is completely empty. "
                "Structural cascades will trigger fallback automatically."
            )

        self.capabilities = self._get_model_capabilities()

        logger.info(
            f"[OpenAI] Model: {self.model} | "
            f"Capabilities: {self.capabilities}"
        )

    # ============================================================
    # CAPABILITY RESOLUTION
    # ============================================================

    def _get_model_capabilities(self) -> dict:
        """
        Resolve capabilities for the configured model.

        Fails early if the model is not explicitly configured.
        This is safer than silently guessing model behavior.
        """

        capabilities = self.MODEL_CAPABILITIES.get(self.model)

        if not capabilities:
            raise ValueError(
                f"Unsupported OpenAI model '{self.model}'. "
                f"Add its capabilities to MODEL_CAPABILITIES."
            )

        return capabilities

    # ============================================================
    # TOKEN PARAMETER
    # ============================================================

    def _get_token_limit_param(self, token_limit: int) -> dict:
        """
        Convert our generic token_limit into the parameter
        expected by the configured model.
        """

        parameter_name = self.capabilities["token_parameter"]

        return {
            parameter_name: token_limit
        }

    # ============================================================
    # GENERIC CHAT COMPLETION
    # ============================================================

    async def _chat_completion(
        self,
        messages: list,
        token_limit: int,
        temperature: float = 0.3,
    ):
        """
        Centralized OpenAI completion call.

        Business logic should call this method instead of
        client.chat.completions.create() directly.
        """

        request = {
            "model": self.model,
            "messages": messages,

            # Automatically becomes either:
            #
            # max_tokens=60
            #
            # OR
            #
            # max_completion_tokens=60
            #
            **self._get_token_limit_param(token_limit),
        }

        # Some model families may not support temperature.
        if self.capabilities.get("supports_temperature", True):
            request["temperature"] = temperature

        return await self.client.chat.completions.create(**request)

    # ============================================================
    # SMS GENERATION
    # ============================================================

    async def generate_sms(
        self,
        query: str,
        context: str
    ) -> tuple[str, dict]:

        if not self.client:
            raise ValueError(
                "OpenAI client missing active token initialization contexts."
            )

        system_prompt = (
            "Summarize the provided search results to directly answer "
            "the user query. "
            "CRITICAL: The entire response must be strictly under "
            "150 characters total. "
            "Write only one short, direct sentence. "
            "No markdown, no bolding, no extra text."
        )

        user_prompt = (
            f"User Question: {query}\n\n"
            f"Search Context:\n{context}\n\n"
            f"SMS Summary:"
        )

        try:
            response = await self._chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ],
                token_limit=150,
                temperature=0.3
            )

            raw_draft = response.choices[0].message.content.strip()

            usage = response.usage

            token_stats = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens
            }

            logger.info(
                f"📊 [OpenAI Usage - SMS] "
                f"Prompt: {usage.prompt_tokens} | "
                f"Completion: {usage.completion_tokens}"
            )

            return raw_draft[:150], token_stats

        except Exception as e:
            logger.error(
                f"OpenAI completion library call failed: {str(e)}"
            )
            raise

    # ============================================================
    # QUALITY EVALUATION
    # ============================================================

    async def evaluate_quality(
        self,
        query: str,
        content: str
    ) -> tuple[bool, dict]:

        if not self.client:
            raise ValueError(
                "OpenAI client missing active token initialization contexts."
            )

        if not content.strip():
            return False, {
                "prompt_tokens": 0,
                "completion_tokens": 0
            }
        
        system_instruction = (
            "You are a strict quality control judge system. "
            "Your job is to output exactly one word and nothing else. "
            "You are forbidden from writing explanations, notes, "
            "or markdown packaging."
        )

        is_sms_draft = len(content) <= 200

        if is_sms_draft:

            judge_prompt = (
                f"Analyze the following SMS response draft against "
                f"the User Query.\n\n"
                f"User Query: {query}\n"
                f"SMS Draft: {content}\n\n"

                f"CRITERIA:\n"
                f"1. Is the text written completely in English?\n"

                f"2. Does it provide a meaningful, positive response "
                f"or direct answer to the user's intent? "
                f"(Note: The query may contain typos or misspellings. "
                f"If the search context corrected the term and the SMS "
                f"accurately answers the intended question, consider "
                f"this criterion MET).\n"

                f"3. Is it brief, concise, and under 150 characters?\n\n"

                f"If ALL criteria are met, output: TRUE\n"
                f"If it fails any criterion, output: FALSE"
            )

        else:

            judge_prompt = (
                f"Analyze the following search context against "
                f"the User Query.\n\n"

                f"User Query: {query}\n"
                f"Search Context: {content}\n\n"

                f"CRITERIA:\n"
                f"1. Does the content contain text that could help "
                f"answer the query's core intent "
                f"(accounting for potential user typos)?\n"

                f"2. Is the content written primarily in English?\n\n"

                f"If BOTH criteria are met, output: TRUE\n"
                f"If either criterion fails, output: FALSE"
            )

        try:

            response = await self._chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": system_instruction
                    },
                    {
                        "role": "user",
                        "content": judge_prompt
                    }
                ],
                token_limit=60,
                temperature=0.0
            )

            verdict = (
                response.choices[0]
                .message.content
                .strip()
                .upper()
            )

            logger.info(
                f"⚖️ [OpenAI Judge Raw Verdict] {verdict!r}"
            )

            usage = response.usage

            token_stats = {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens
            }

            logger.info(
                f"📊 [OpenAI Usage - Judge] "
                f"Prompt: {usage.prompt_tokens} | "
                f"Completion: {usage.completion_tokens}"
            )

            return "TRUE" in verdict, token_stats

        except Exception as e:

            logger.error(
                f"OpenAI library evaluation call failed: {str(e)}"
            )

            raise

    # ============================================================
    # KNOWLEDGE BASE FALLBACK
    # ============================================================

    async def generate_from_knowledge_base(
        self,
        query: str
    ) -> tuple[str, dict]:

        if not self.client:
            raise ValueError(
                "OpenAI client missing active token initialization contexts."
            )

        system_prompt = (
            "You are a helpful assistant answering from your internal "
            "knowledge base because live web search failed.\n"

            "CRITICAL CONSTRAINTS:\n"

            "1. Evaluate if the user query requires real-time/current "
            "information (e.g., live weather, stock prices, today's news).\n"

            "2. If it requires real-time data you do not possess, "
            "reply exactly with: "
            "'Sorry, I couldn't retrieve real-time data to safely "
            "process this request.'\n"

            "3. If it is general knowledge, physics, math, history, "
            "or fiction (e.g., 'what is naruto'), answer directly.\n"

            "4. The entire summary answer must be strictly under "
            "150 characters total, exactly one sentence, plain text only."
        )

        try:

            response = await self._chat_completion(
                messages=[
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"User Query: {query}"
                    }
                ],
                token_limit=60,
                temperature=0.3
            )

            raw_draft = response.choices[0].message.content.strip()

            return raw_draft[:150], {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens
            }

        except Exception as e:

            logger.error(
                f"OpenAI Knowledge Base execution failed: {str(e)}"
            )

            raise
