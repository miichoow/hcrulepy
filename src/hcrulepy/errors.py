"""Exceptions raised by the rule engine."""


class InvalidRule(ValueError):
    """Raised when a rule line cannot be parsed (unknown command, bad args)."""


class RejectCandidate(Exception):
    """Raised by a rejection rule to drop the current candidate (no output)."""
