# filepath: common/errors.py
class ConflictError(Exception):
    """The caller must reload state or submit a new action."""

    def __init__(self, message: str = 'Data sudah berubah atau aksi tidak dapat diulang.') -> None:
        super().__init__(message)
