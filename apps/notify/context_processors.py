def notifications(request):
    user = getattr(request, "user", None)
    if user is None or not user.is_authenticated:
        return {}
    unread = user.notifications.filter(read_at=None)
    return {"unread_count": unread.count(), "latest_notifications": list(user.notifications.all()[:6])}
