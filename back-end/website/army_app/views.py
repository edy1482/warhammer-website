from django.shortcuts import render
from army_app.models import Faction, ArmyList
from .forms import ArmyListForm
from django.http import Http404, HttpResponse
from django.urls import reverse


# Create your views here.
def home(request):
    return render(request, 'home.html')

def factions(request):
    try:
        all_factions = Faction.objects.all()
    except:
        raise Http404("Factions not found")
    return render(request, 'factions.html', {"all_factions" : all_factions})

def create_army_list_form(request, faction_id):
    if request.method == "POST":
        form = ArmyListForm(request.POST)
        if form.is_valid():
            army_list = form.save(commit=False)
            army_list.faction_id = faction_id
            army_list.save()
            
            # HTMX will follow this redirect automatically
            response = HttpResponse()
            response["HX-Redirect"] = reverse("army_list", args=[army_list.id])
            return response
    else:
        form = ArmyListForm()
        
    return render(request, 'partials/army_list_form.html', {"form" : form})

def army_list(request, army_list_id):
    army_list = ArmyList.objects.get(pk=army_list_id)
    return render(request, "army_list_blank.html")
            