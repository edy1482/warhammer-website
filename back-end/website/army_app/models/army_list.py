from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from .core import KeyWord, Faction, Detachment, Enhancement, Stratagem
from .units import Unit
from .leadership import Leadership

MAX_CHARFIELD_LENGTH = 255

class ArmyList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=MAX_CHARFIELD_LENGTH, blank=True, default="")
    # Do we need faction, if we have detachment?
    faction = models.ForeignKey(Faction, on_delete=models.CASCADE)
    detachment = models.ForeignKey(Detachment, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Class functions
    def __str__(self):
        return self.name
    
    def valid_enhancements(self):
        return Enhancement.objects.filter(detachment=self.detachment).distinct()
    
class ArmyListEntry(models.Model):
    army_list = models.ForeignKey(ArmyList, on_delete=models.CASCADE, related_name="entries")
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    model_count = models.PositiveIntegerField(default=1)
    enhancement = models.ForeignKey(Enhancement, on_delete=models.SET_NULL, blank=True, null=True)
    is_warlord = models.BooleanField(default=False)
    
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["army_list", "enhancement"], 
                name="unique_enhancement_per_army_list", 
                condition = models.Q(enhancement__isnull=False)),
            ]
    
    # Class functions
    def __str__(self):
        return f"{self.army_list} - {self.unit} → [Entry: {self.id}]"
    
    def get_unit_points(self):
        bracket = self.unit.point_brackets.filter(min_models__lte=self.model_count, max_models__gte=self.model_count).first()
        return bracket.points if bracket else 0
    
    def get_enhancement_points(self):
        return self.enhancement.points if self.enhancement else 0
    
    def get_total_points(self):
        return self.get_unit_points() + self.get_enhancement_points()
    
    def get_valid_strats(self):
        # Grab all CORE strats
        core_strats = Stratagem.objects.filter(keywords__name="CORE")
        # Grab all detachment strats, and filter for necessary keywords
        detachment_strats = Stratagem.objects.filter(detachment=self.army_list.detachment).filter(keywords__in=self.unit.keywords.all())

        return (core_strats | detachment_strats).distinct()
    
    def get_all_leadership_options(self):
        # Return all possible leadership options for this Entry
        return Leadership.objects.filter(attached_unit=self.unit)
    
    def get_available_leadership(self):
        # Return all leadership options inside the ArmyList
        # Get all the leaders in the list
        valid_leader_ids = self.get_all_leadership_options().values_list("leader_id", flat=True)
        return self.army_list.entries.filter(unit_id__in=valid_leader_ids)

    
    def clean(self):
        super().clean()

        # Warlord Validation
        # Check if Entry is a Warlord
        if self.is_warlord:
            # Must have character key word
            if not self.unit.keywords.filter(name__iexact="CHARACTER").exists():
                raise ValidationError(f"Missing Keyword: {self.unit.name} is not a CHARACTER")
            
            # There must not be an existing Warlord
            other_warlords = ArmyListEntry.objects.filter(army_list=self.army_list, is_warlord=True).exclude(pk=self.pk)
            if other_warlords.exists():
                # Do a join on the whole object in case there are multiple duplicates - this should not happen but it is good to check 
                warlord_names = ", ".join(warlord.unit.name for warlord in other_warlords)
                raise ValidationError(f"Duplicate Warlord: {self.unit.name} cannot be the Warlord - there is already an existing Warlord: {warlord_names}")
        
        # Enhancement Validation
        # Check if there is an enhancement
        if self.enhancement:
            # Check to see if the enhancement already exists
            duplicate_enhancement = ArmyListEntry.objects.filter(army_list=self.army_list, enhancement=self.enhancement).exclude(pk=self.pk)
            if duplicate_enhancement.exists():
                # Join on the whole object in case there are multiple duplicates - this should not happen but it is good to check 
                unit_names = ", ".join(dup.unit.name for dup in duplicate_enhancement)
                raise ValidationError(f"Duplicate Enhancement: the enhancement {self.enhancement.name} is already assigned to another unit: {unit_names} in this list")
            # Check to see if the keywords match 
            enhancement_keywords = set(self.enhancement.keywords.all().values_list("name", flat=True))
            unit_keywords = set(self.unit.keywords.all().values_list("name", flat=True))
            if not enhancement_keywords.issubset(unit_keywords):
                difference = enhancement_keywords.difference(unit_keywords)
                missing_keywords = ", ".join(name for name in difference)
                raise ValidationError(f"Missing Keyword(s): {missing_keywords}")
            # Check to see if the enhancement detachment matches the detachment of the ArmyList
            if self.army_list.detachment != self.enhancement.detachment:
                raise ValidationError(f"Conflicting detachment: Enhancement Detachment: {self.enhancement.detachment} - Army List Detachment {self.army_list.detachment}")        

    def save(self, *args, **kwargs):
        # Ensure clean() is called when saving from shell or script
        self.full_clean()
        # Save to ensure id field
        super().save(*args, **kwargs)
        
        # WARLORD keyword insertion/deletion
        warlord_keyword, _ = KeyWord.objects.get_or_create(name = "WARLORD")
        if self.is_warlord:
            # Add WARLORD keyword
            if not self.unit.keywords.filter(pk=warlord_keyword.pk).exists():
                self.unit.keywords.add(warlord_keyword)
        else:
            # Remove WARLORD keyword
            if self.unit.keywords.filter(pk=warlord_keyword.pk).exists():
                self.unit.keywords.remove(warlord_keyword)
                
    def delete(self, *args, **kwargs):
        warlord_key_word = KeyWord.objects.filter(name__iexact="WARLORD").first()
        if self.is_warlord and warlord_key_word:
            if self.unit.keywords.filter(pk=warlord_key_word.pk).exists():
                self.unit.keywords.remove(warlord_key_word)
        
        return super().delete(*args, **kwargs)
    
class AssignedLeader(models.Model):
    entry = models.ForeignKey(ArmyListEntry, on_delete=models.CASCADE, related_name="assigned_leaders")
    leader_entry = models.ForeignKey(ArmyListEntry, on_delete=models.CASCADE, related_name="leading_assignments")

    class Meta:
        constraints = [
            # Prevent the same leader_entry to be assigned twice to the same entry
            models.UniqueConstraint(
                fields=["entry", "leader_entry"],
                name="unique_leader_assignment"
            ),
        ]
        indexes = [
            # Speed up duplicate checks
            models.Index(fields=["entry", "leader_entry"])
        ]

    def __str__(self):
        return f"{self.leader_entry.unit} [Entry {self.leader_entry.id}] → {self.entry.unit} [Entry {self.entry.id}]"
    
    def clean(self):
        super().clean()
        unit = self.entry.unit
        leader_unit = self.leader_entry.unit

        # Check if the entry and leader_entry are in the same ArmyList
        if self.entry.army_list != self.leader_entry.army_list:
            raise ValidationError(f"{self.entry} and {self.leader_entry} are from two seperate ArmyLists")

        # Ensure Leadership rule exists
        leadership = Leadership.objects.filter(leader=leader_unit, attached_unit=unit).first()
        if not leadership:
            raise ValidationError(f"Leader Error: {leader_unit} cannot lead {unit}")
        
        # Check if any required keyword exists
        required = set(leadership.keywords.values_list("name", flat=True))
        leader_keywords = set(leader_unit.keywords.values_list("name", flat=True))
        missing_keywords = required - leader_keywords
        if missing_keywords:
            raise ValidationError(f"Missing Keyword(s): {leader_unit} lacks required {', '.join(missing_keywords)}")
        
        # Check co-leading rule if another leader is already assigned,
        existing_leaders = self.entry.assigned_leaders.exclude(pk=self.pk)
        for existing in existing_leaders:
            # Get the Leadership object for the existing leader
            existing_leadership = Leadership.objects.filter(leader=existing.leader_entry.unit, attached_unit=unit).first()
            if not existing_leadership:
                # Should not happen but extra guard
                raise ValidationError(f"Leader Error: {existing.leader_entry.unit} cannot lead {unit}")
            can_co_lead = leadership.co_leaders.filter(pk=existing_leadership.leader.pk).exists()
            if not can_co_lead:
                raise ValidationError(f"{leader_unit} cannot share leadership with {existing.leader_entry.unit}")
        
        # Prevent leader from leading multiple separate units
        duplicate_assignments = AssignedLeader.objects.filter(leader_entry=self.leader_entry).exclude(pk=self.pk)
        if duplicate_assignments.exists():
            units = ", ".join(f"{assign.entry.unit.name} [Entry {assign.entry.id}]" for assign in duplicate_assignments)
            raise ValidationError(f"{leader_unit} [Entry {self.leader_entry.id}] is already assigned to {units}")
        
        # Prevent two leaders of the same unit type from leading same entry
        if existing_leaders.filter(leader_entry__unit=leader_unit).exists():
            raise ValidationError(f"{unit} cannot have more than one {leader_unit} leading it")
        
    def save(self, *args, **kwargs):
        # Ensure that we clean when using CSV files or shell
        self.full_clean()
        # Now we save
        super().save(*args, **kwargs)