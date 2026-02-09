"""Exception classes for chorelib."""


class RuleError(Exception):
    """General error related to rule definitions or dependency cycles."""

    pass


class RuleNotFoundError(Exception):
    """Raised when no rule is found to build a requested target."""

    def __repr__(self) -> str:
        return f"RuleNotFoundError: {self!s}"

    def __str__(self) -> str:
        return f"No rule found to build target '{self.args[0]}'"


class TargetNotFoundError(Exception):
    """Raised when a target file or resource does not exist and has no builder."""

    def __repr__(self) -> str:
        return f"TargetNotFoundError: {self!s}"

    def __str__(self) -> str:
        return f"Target '{self.args[0]}' not found"
