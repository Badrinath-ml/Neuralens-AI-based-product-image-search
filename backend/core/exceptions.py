from fastapi import HTTPException, status


class AppError(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR):
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status.HTTP_400_BAD_REQUEST)
