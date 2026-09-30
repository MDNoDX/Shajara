from django.urls import path

from . import views

app_name = "friends"

urlpatterns = [
    path("", views.friends_list, name="list"),
    path("yangi/", views.contact_create, name="create"),
    path("<int:pk>/tahrirlash/", views.contact_edit, name="edit"),
    path("<int:pk>/ochirish/", views.contact_delete, name="delete"),
    path("ulashish/", views.sharing, name="sharing"),
    path("ulashish/sorov/<int:user_id>/", views.send_request, name="send"),
    path("ulashish/sorov/<int:pk>/javob/", views.answer_request, name="answer"),
    path("ulashish/sorov/<int:pk>/bekor/", views.cancel_request, name="cancel"),
    path("ulashish/<int:user_id>/ochirish/", views.remove_friend, name="remove"),
]
