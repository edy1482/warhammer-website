from django.shortcuts import render
from army_app.models import Faction
from django.http import Http404


# Create your views here.
def home(request):
    return render(request, 'home.html')

def factions(request):
    try:
        all_factions = Faction.objects.all()
    except:
        raise Http404("Factions not found")
    return render(request, 'factions.html', {"all_factions" : all_factions})