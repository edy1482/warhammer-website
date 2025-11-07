from django import forms
from army_app.models import ArmyList

class ArmyListForm(forms.ModelForm):
    class Meta:
        model = ArmyList
        fields = ["name", "point_limit", "battle_size"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "My Army Name", "class": "input input-bordered w-full"}),
            "point_limit": forms.NumberInput(attrs={"class": "input input-bordered w-full", "id": "point-limit"}),
            "battle_size": forms.Select(
                attrs={"class": "select select-bordered w-full", "id": "battle-size"},
                choices=[
                    ("incursion", "Incursion (0–1000 pts)"),
                    ("strike", "Strike Force (1000–2000 pts)"),
                    ("onslaught", "Onslaught (2000–3000 pts)"),
                ],
            ),
        }