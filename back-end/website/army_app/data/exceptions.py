class LoaderValidationError(Exception):
    """Raised when a loader function returns a non-empty errors list.

    Carries the original error list so callers can log/report the
    individual row-level messages without re-parsing exception text.
    """
    def __init__(self, errors):
        self.errors = errors
        super().__init__(f"{len(errors)} validation error(s)")