from django.contrib import admin
from .models import Faction, Detachment, DataSheet, Unit
# Register your models here.

admin.site.register(Faction)
admin.site.register(Detachment)
admin.site.register(DataSheet)
admin.site.register(Unit)