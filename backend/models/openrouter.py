"""
OpenRouter AI client with intelligent fallback chain
Manages free and paid models with circuit breaker and token budgeting
"""
import httpx
import structlog
from typing import Optional, Dict, List, Any
from enum import Enum
import time

log = structlog.get_logger()


class ModelTier(str, Enum):
    FREE = "free"
    PAID = "paid"


# ====================================================
# Available Models on OpenRouter (Free Tier)
# ====================================================

AVAILABLE_MODELS = {
    "deepseek/deepseek-r1:free": {
        "tier": ModelTier.FREE,
        "purpose": "reasoning",
        "max_tokens": 8000,
        "description": "Deep reasoning with structured thinking"
    },
    "google/gemini-2.5-flash-preview:free": {
        "tier": ModelTier.FREE,
        "purpose": "planning",
        "max_tokens": 8000,
        "description": "Fast multi-modal planning"
    },
    "qwen/qwen3-235b-a22b:free": {
        "tier": ModelTier.FREE,
        "purpose": "coding",
        "max_tokens": 4000,
        "description": "Code generation and analysis"
    },
    "meta-llama/llama-3.3-70b-instruct:free": {
        "tier": ModelTier.FREE,
        "purpose": "general",
        "max_tokens": 4000,
        "description": "General purpose conversational"
    }
}

# Fallback chain for different purposes
FALLBACK_CHAINS = {
    "orchestrator": [
        "deepseek/deepseek-r1:free",
        "google/gemini-2.5-flash-preview:free",
        "meta-llama/llama-3.3-70b-instruct:free"
    ],
    "planner": [
        "google/gemini-2.5-flash-preview:free",
        "deepseek/deepseek-r1:free",
        "meta-llama/llama-3.3-70b-instruct:free"
    ],
    "coder": [
        "qwen/qwen3-235b-a22b:free",
        "deepseek/deepseek-r1:free",
        "meta-llama/llama-3.3-70b-instruct:free"
    ],
    "evaluator": [
        "deepseek/deepseek-r1:free",
        "meta-llama/llama-3.3-70b-instruct:free",
        "google/gemini-2.5-flash-preview:free"
    ],
    "default": [
        "meta-llama/llama-3.3-70b-instruct:free",
        "deepseek/deepseek-r1:free",
        "google/gemini-2.5-flash-preview:free"
    ]
}


class CircuitBreakerState:
    """Track model failures for circuit breaker"""
    
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 300):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.last_failure_time = None
        self.recovery_timeout = recovery_timeout
        self.is_open = False
    
    def record_failure(self) -> None:
        """Record a failure"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            self.is_open = True
            log.warning("circuit_breaker_opened", failure_count=self.failure_count)
    
    def can_attempt(self) -> bool:
        """Check if circuit is closed"""
        if not self.is_open:
            return True
        
        # Check recovery timeout
        if time.time() - self.last_failure_time > self.recovery_timeout:
            self.is_open = False
            self.failure_count = 0
            log.info("circuit_breaker_recovered")
            return True
        
        return False
    
    def record_success(self) -> None:
        """Record successful call"""
        self.failure_count = 0
        self.is_open = False


class TokenBudget:
    """Track token usage per agent"""
    
    def __init__(self, max_tokens_per_call: int = 2000):
        self.max_tokens_per_call = max_tokens_per_call
        self.used_tokens = 0
    
    def can_use(self, estimated_tokens: int) -> bool:
        """Check if within budget"""
        return self.used_tokens + estimated_tokens <= self.max_tokens_per_call
    
    def add_usage(self, tokens: int) -> None:
        """Record token usage"""
        self.used_tokens += tokens
    
    def reset(self) -> None:
        """Reset budget"""
        self.used_tokens = 0


class OpenRouterClient:
    """
    OpenRouter API client with:
    - Intelligent model fallback
    - Circuit breaker for failing models
    - Token budget tracking
    - Cost estimation
    """
    
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://ai-architect.vercel.app",
                "X-Title": "AI Architect"
            },
            timeout=60.0
        )
        
        # Circuit breakers per model
        self.circuit_breakers: Dict[str, CircuitBreakerState] = {
            model: CircuitBreakerState() for model in AVAILABLE_MODELS
        }
        
        # Token budgets per agent
        self.token_budgets: Dict[str, TokenBudget] = {}
        
        log.info("openrouter_client_initialized", base_url=base_url)
    
    def get_fallback_chain(self, agent_type: str) -> List[str]:
        """Get fallback model chain for agent type"""
        return FALLBACK_CHAINS.get(agent_type, FALLBACK_CHAINS["default"])
    
    async def call(
        self,
        messages: List[Dict[str, str]],
        agent_type: str = "default",
        agent_id: str = None,
        max_tokens: int = 2000,
        temperature: float = 0.7,
        retry_count: int = 0
    ) -> tuple[str, Dict[str, Any]]:
        """
        Call OpenRouter with intelligent fallback.
        
        Returns:
            (response_text, metadata)
        """
        fallback_chain = self.get_fallback_chain(agent_type)
        
        # Initialize token budget for agent if needed
        if agent_id and agent_id not in self.token_budgets:
            self.token_budgets[agent_id] = TokenBudget()
        
        for attempt, model in enumerate(fallback_chain):
            if attempt >= 3:  # Max 3 retries
                error = f"All models failed after {attempt} attempts"
                log.error("all_models_failed", agent_type=agent_type, error=error)
                return "", {"error": error, "model": None, "tokens_used": 0}
            
            # Check circuit breaker
            if not self.circuit_breakers[model].can_attempt():
                log.warning("model_circuit_breaker_open", model=model)
                continue
            
            try:
                response = await self.client.post(
                    "/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": min(max_tokens, AVAILABLE_MODELS[model]["max_tokens"]),
                        "temperature": temperature,
                        "stream": False
                    }
                )
                
                if response.status_code != 200:
                    self.circuit_breakers[model].record_failure()
                    log.warning(
                        "model_call_failed",
                        model=model,
                        status_code=response.status_code
                    )
                    continue
                
                data = response.json()
                result = data["choices"][0]["message"]["content"]
                tokens_used = data.get("usage", {}).get("total_tokens", 0)
                
                # Record success
                self.circuit_breakers[model].record_success()
                
                # Track token usage
                if agent_id:
                    self.token_budgets[agent_id].add_usage(tokens_used)
                
                log.info(
                    "model_call_success",
                    model=model,
                    agent_type=agent_type,
                    tokens_used=tokens_used
                )
                
                return result, {
                    "model": model,
                    "tokens_used": tokens_used,
                    "attempt": attempt + 1
                }
                
            except Exception as e:
                self.circuit_breakers[model].record_failure()
                log.error(
                    "model_call_error",
                    model=model,
                    error=str(e),
                    attempt=attempt + 1
                )
                continue
        
        # All attempts failed
        error = "No available models"
        log.error("no_available_models", agent_type=agent_type)
        return "", {"error": error, "model": None, "tokens_used": 0}
    
    def estimate_tokens(self, text: str) -> int:
        """Rough token estimation (4 chars = 1 token)"""
        return len(text) // 4
    
    def get_token_budget_status(self, agent_id: str) -> Dict[str, int]:
        """Get token budget status for agent"""
        if agent_id not in self.token_budgets:
            return {"used": 0, "max": 2000, "remaining": 2000}
        
        budget = self.token_budgets[agent_id]
        return {
            "used": budget.used_tokens,
            "max": budget.max_tokens_per_call,
            "remaining": budget.max_tokens_per_call - budget.used_tokens
        }
    
    def reset_agent_budget(self, agent_id: str) -> None:
        """Reset token budget for agent"""
        if agent_id in self.token_budgets:
            self.token_budgets[agent_id].reset()
    
    async def close(self) -> None:
        """Close HTTP client"""
        await self.client.aclose()


# Global instance
_openrouter_client: Optional[OpenRouterClient] = None


def get_openrouter_client(api_key: str) -> OpenRouterClient:
    """Factory to get or create OpenRouter client"""
    global _openrouter_client
    if _openrouter_client is None:
        _openrouter_client = OpenRouterClient(api_key)
    return _openrouter_client
