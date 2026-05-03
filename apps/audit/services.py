from apps.audit.models import AuditLog


def log_action(user=None, project=None, action="", obj=None, description="", metadata=None, request=None):
    ip_address = None
    user_agent = ""
    if request:
        ip_address = request.META.get("HTTP_X_FORWARDED_FOR", request.META.get("REMOTE_ADDR", "")).split(",")[0]
        user_agent = request.META.get("HTTP_USER_AGENT", "")
    return AuditLog.objects.create(
        user=user if getattr(user, "is_authenticated", False) else None,
        project=project,
        action=action,
        object_type=obj.__class__.__name__ if obj else "",
        object_id=str(getattr(obj, "pk", "")) if obj else "",
        description=description,
        metadata=metadata or {},
        ip_address=ip_address or None,
        user_agent=user_agent,
    )
