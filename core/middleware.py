from .audit import log_audit


class AuditMiddleware:
    """Capture IP et User-Agent pour le journal d'audit."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.audit_meta = {
            'ip_address': self._get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
        response = self.get_response(request)
        return response

    @staticmethod
    def _get_client_ip(request):
        x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded:
            return x_forwarded.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')


def get_audit_meta(request):
    return getattr(request, 'audit_meta', {'ip_address': None, 'user_agent': ''})
