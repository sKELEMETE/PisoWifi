from schemas.response import ApiError, ApiResponse


def success(data=None, message=""):
    return ApiResponse(
        success=True,
        message=message,
        data=data,
    )


def error(message="", errors=None):
    return ApiError(
        success=False,
        message=message,
        errors=errors or [],
    )
