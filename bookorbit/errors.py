"""Named errors (SRS Section 4.1): a service raises one, the screen that
called it catches it and shows its message; no other state is changed."""


class BookOrbitError(Exception):
    """Base class; str(e) is the user-facing message."""


class RegistrationError(BookOrbitError):
    """UC-01 E1/E2: carries the list of invalid fields."""

    def __init__(self, problems: dict):
        # problems: {field_name: short reason}
        self.problems = problems
        super().__init__("; ".join(f"{k}: {v}" for k, v in problems.items()))


class LoginError(BookOrbitError):
    """UC-02 E1-E3. kind is UNKNOWN_USER, NO_MATCH or LOCKED."""

    def __init__(self, kind: str, attempts_left: int = 0, minutes_left: int = 0):
        self.kind = kind
        self.attempts_left = attempts_left
        self.minutes_left = minutes_left
        super().__init__(kind)


class NoFaceError(BookOrbitError):
    """UC-01 E3 / UC-02 E5: zero or several faces. Not counted as a failed login."""


class NoVoiceError(BookOrbitError):
    """UC-02 E5: audio too short or unreadable. Not counted as a failed login."""


class TemplateMissingError(BookOrbitError):
    """UC-02 E6: stored template missing or corrupt."""


class ModelUnavailable(BookOrbitError):
    """A real AI model/service is not installed or not reachable."""


class NotFound(BookOrbitError):
    """UC-05 E1: book no longer exists."""
