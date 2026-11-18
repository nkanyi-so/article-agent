"""Prices in one dated table. Cost is computed from each response's own usage figures."""

# US dollars per million tokens (input, output), from the pricing page on 2026-11-18.
# Thinking tokens are billed as output tokens and are already inside the output count.
PRICES_PER_MILLION: dict[str, tuple[float, float]] = {
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-opus-5-5": (4.0, 20.0),
}


def cost_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    """Raises KeyError for a model with no price: a silent zero would understate the spend."""
    price_in, price_out = PRICES_PER_MILLION[model]
    return (input_tokens * price_in + output_tokens * price_out) / 1_000_000
