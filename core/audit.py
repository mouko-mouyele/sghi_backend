from django.forms.models import model_to_dict

from .models import AuditLog


def log_audit(
    *,
    user,
    action_type: str,
    model_name: str,
    object_id: str = '',
    old_value=None,
    new_value=None,
    ip_address=None,
    user_agent: str = '',
):
    AuditLog.objects.create(
        user=user if user and user.is_authenticated else None,
        action_type=action_type,
        model_name=model_name,
        object_id=str(object_id) if object_id else '',
        old_value=old_value,
        new_value=new_value,
        ip_address=ip_address,
        user_agent=user_agent[:512],
    )


def snapshot(instance, exclude=None):
    if instance is None:
        return None
    data = model_to_dict(instance)
    if exclude:
        for key in exclude:
            data.pop(key, None)
    for key, value in list(data.items()):
        if hasattr(value, 'pk'):
            data[key] = value.pk
    return data
