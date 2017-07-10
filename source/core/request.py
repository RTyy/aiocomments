from .exceptions import CoreException


def json_request_required(method):
    """Decorator to check request content type."""
    def wrapper(self, *args, **kwargs):
        if not self.request.content_type == 'application/json':
            raise CoreException(400, 'Request should be application/json')
        return method(self, *args, **kwargs)
    return wrapper
