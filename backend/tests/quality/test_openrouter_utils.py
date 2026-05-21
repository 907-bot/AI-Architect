import time

from backend.models.openrouter import CircuitBreakerState, TokenBudget


def test_circuit_breaker_behavior():
    cb = CircuitBreakerState(failure_threshold=2, recovery_timeout=1)
    # Initially allowed
    assert cb.can_attempt()

    # Record failures until threshold
    cb.record_failure()
    assert cb.failure_count == 1
    assert cb.can_attempt()

    cb.record_failure()
    assert cb.failure_count == 2
    # Circuit should be open now
    assert not cb.can_attempt()

    # After recovery timeout, circuit should allow attempts again
    time.sleep(1.1)
    assert cb.can_attempt()

    # Record success clears failures
    cb.record_success()
    assert cb.failure_count == 0
    assert cb.can_attempt()


def test_token_budget():
    tb = TokenBudget(max_tokens_per_call=100)
    assert tb.can_use(50)
    tb.add_usage(50)
    assert tb.used_tokens == 50
    # Exceeding budget
    assert not tb.can_use(60)
    tb.add_usage(50)
    assert tb.used_tokens == 100
    tb.reset()
    assert tb.used_tokens == 0
