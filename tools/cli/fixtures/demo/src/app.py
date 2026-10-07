"""Synthetic input only; never execute this fixture."""


def unsafe_expression(user_input):
    """Marker consumed by the canned model to exercise report transport."""
    return eval(user_input)  # TITVO_TEST_VULNERABILITY
