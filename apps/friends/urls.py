from django.urls import path

from . import views

app_name = "friends"

urlpatterns = [
    path("", views.friends_list, name="list"),
    path("sorov/<int:user_id>/", views.send_request, name="send"),
    path("sorov/<int:pk>/javob/", views.answer_request, name="answer"),
    path("sorov/<int:pk>/bekor/", views.cancel_request, name="cancel"),
    path("<int:user_id>/ochirish/", views.remove_friend, name="remove"),
]
