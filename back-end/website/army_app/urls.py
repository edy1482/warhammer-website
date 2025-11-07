from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("factions", views.factions, name="factions"),
    path("factions/form/<int:faction_id>/", views.create_army_list_form, name="create_army_list_form"),
    path("army_list/<int:army_list_id>", views.army_list, name="army_list"),
]