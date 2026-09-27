from django.urls import path

from . import views

app_name = "genealogy"

urlpatterns = [
    path("qarindoshlar/", views.people_list, name="people"),
    path("qarindoshlar/yangi/", views.person_create, name="person_create"),
    path("qarindoshlar/<int:pk>/", views.person_detail, name="person"),
    path("qarindoshlar/<int:pk>/tahrirlash/", views.person_edit, name="person_edit"),
    path("qarindoshlar/<int:pk>/ochirish/", views.person_delete, name="person_delete"),
    path("qarindoshlar/<int:pk>/qarindosh-qoshish/", views.relative_add, name="relative_add"),
    path("qarindoshlar/<int:pk>/men/", views.set_self, name="set_self"),
    path("qarindoshlar/<int:pk>/pdf/", views.person_pdf, name="person_pdf"),
    path("nikoh/<int:pk>/", views.marriage_edit, name="marriage_edit"),
    path("shajara/", views.tree_page, name="tree"),
    path("shajara/kitob.pdf", views.family_book, name="family_book"),
    path("shajara/<str:username>/", views.tree_page, name="tree_for"),
    path("shajara/<str:username>/malumot.json", views.tree_data, name="tree_data_for"),
    path("shajara/<str:username>/shajara.pdf", views.tree_pdf, name="tree_pdf_for"),
    path("shajara/<str:username>/kitob.pdf", views.family_book, name="family_book_for"),
    path("hikoyalar/", views.story_list, name="stories"),
    path("hikoyalar/yangi/", views.story_create, name="story_create"),
    path("hikoyalar/<int:pk>/", views.story_detail, name="story"),
    path("hikoyalar/<int:pk>/tahrirlash/", views.story_edit, name="story_edit"),
    path("hikoyalar/<int:pk>/ochirish/", views.story_delete, name="story_delete"),
    path("qidiruv/", views.search, name="search"),
]
