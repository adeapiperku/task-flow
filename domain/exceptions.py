
class RepositoryError(Exception):
    """Generic persistence error."""


class JobAlreadyExistsError(RepositoryError):
    """Raised when trying to insert a job whose ID already exists."""
    pass
