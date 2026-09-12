from abc import ABC, abstractmethod

class BaseLLMService(ABC):
    @abstractmethod
    async def generate_sms(self, query: str, context: str) -> str:
        """Asynchronously converts raw context payloads into an under-150-char SMS response."""
        pass

    @abstractmethod
    async def evaluate_quality(self, query: str, content: str) -> bool:
        """Asynchronously checks whether context documents or SMS outputs pass safety criteria."""
        pass

    @abstractmethod
    async def generate_from_knowledge_base(self, query: str) -> tuple[str, dict]:
        """Generate answers using purely internal parameters, checking real-time constraints."""
        pass