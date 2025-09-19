import datetime
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth.models import User
from army_app.models import KeyWord, Faction, Detachment, Enhancement, Stratagem
from army_app.models import Unit, UnitPointBracket, DataSheet
from army_app.models import Leadership
from army_app.models import ArmyList, ArmyListEntry, AssignedLeader

# Create your tests here.

# Universal tests:
# Assert valid model entry
# Assert invalid model entry
# Assert that Char/Text field may be blank
# Assert that field may be none

class BaseModelTest(TestCase):
    model_class = None

    def assertValid(self, **kwargs):
        obj = self.model_class(**kwargs)
        obj.full_clean()
        obj.save()
        return obj
    
    def assertInvalid(self, **kwargs):
        with self.assertRaises(ValidationError):
            obj = self.model_class(**kwargs)
            obj.full_clean()
    
    def assertBlankAllowed(self, field_name, **kwargs):
        kwargs[field_name] = ""
        obj = self.model_class(**kwargs)
        obj.full_clean()
        obj.save()
        return obj
    
    def assertNoneAllowed(self, field_name, **kwargs):
        kwargs[field_name] = None
        obj = self.model_class(**kwargs)
        obj.full_clean()
        obj.save()
        return obj
    
    def assertActiveKeyWord(self, keywords, obj=None, **kwargs):
        # Two modes - an inplace mode, where we modify an existing obj, and a new mode where we make a new obj
        if obj is None:
            obj = self.assertValid(**kwargs)
        for keyword in keywords:
            obj.keywords.add(keyword)
            self.assertIn(keyword, obj.keywords.all())
        obj.full_clean()
        obj.save()
        return obj
    
    def assertIsRecent(self, upload_flag=True, **kwargs):
        obj = self.assertValid(**kwargs)
        now = timezone.now()
        # Upload flag checks if the field is upload_at or created_at
        if upload_flag:
            recent = now - datetime.timedelta(seconds=10) <= obj.uploaded_at <= now
        else:
            recent = now - datetime.timedelta(seconds=10) <= obj.created_at <= now
        self.assertIs(recent, True)

class KeyWordTestCase(BaseModelTest):
    # Behaviours:
    # Keywords should be unique
    model_class = KeyWord

    def setUp(self):
        KeyWord.objects.create(name="TEST")
    
    def test_unique_keyword(self):
        self.assertInvalid(name="TEST")

class FactionTestCase(BaseModelTest):
    # Behaviours:
    # Faction name should only be chosen from a dict: Faction.FACTION_CHOICES
    # Faction has a rule name (not blank)
    # Faction may have a rule description (can be blank)
    # Faction may have keyword(s)

    def setUp(self):
        self.keyword1 = KeyWord.objects.create(name="ADEPTUS ASTARTES")
        self.keyword2 = KeyWord.objects.create(name="INFANTRY")
        self.required_fields = {
            "name" : "SPM",
            "rule_name" : "OATH OF MOMENT",
        }
        self.model_class = Faction

    def test_valid_faction(self):
        # Test for valid creation with all fields except keyword
        faction = self.assertValid(name=self.required_fields["name"], 
                                   rule_name=self.required_fields["rule_name"], 
                                   rule_description="Re-roll hit rolls on selected target")
        # Test for valid creation with keywords and that they are in the faction
        faction = self.assertActiveKeyWord(keywords=[self.keyword1, self.keyword2], **self.required_fields)
        # Test that the str function is working
        self.assertEqual(str(faction), "SPM")
        # Test that the name is in the choices (should be brought up by the validation, but double check)
        self.assertIn(faction.name, Faction.FACTION_CHOICES)
    
    def test_invalid_faction(self):
        # Test for invalid name
        self.assertInvalid(name="Invalid")
        # Test for no rule_name
        self.assertInvalid(name=self.required_fields["name"])

    def test_blank_rule_description(self):
        self.assertBlankAllowed("rule_description", **self.required_fields)

class DetachmentTestCase(BaseModelTest):
    # Behaviours: 
    # Detachment must have a name
    # Detachment must have a Faction
    # Detachment may have a description (can be blank)
    # Detachment may have keyword(s) (can be empty)
    
    def setUp(self):
        self.keyword1 = KeyWord.objects.create(name="ADEPTUS ASTARTES")
        self.model_class = Faction
        self.faction = self.assertValid(name="SPM", rule_name="OATH OF MOMENT")
        self.faction = self.assertActiveKeyWord(keywords=[self.keyword1], obj=self.faction)
        self.required_fields = {
            "name" : "Gladius Taskforce",
            "faction" : self.faction,
        }
        self.model_class = Detachment

    def test_valid_detachment(self):
        # Test for valid creation with all fields except keyword
        detachment = self.assertValid(name=self.required_fields["name"], 
                                      faction=self.required_fields["faction"], 
                                      description="Once per battle, choose one effect lasting a battleturn: " \
                                      "Advance and shoot, Fall back and shoot and charge, Advance and charge")
        # Test for valid creation with keywords and that they are in the detachment
        detachment = self.assertActiveKeyWord(keywords=[self.keyword1], **self.required_fields)
        # Test that the str function is working
        self.assertEqual(str(detachment), "Gladius Taskforce")

    def test_invalid_detachment(self):
        # Currently the only invalid factions can force an error
        # Future - make large detachment list for choice?
        #        - make certain factions invalid for certain Detachments?

        # Test for invalid faction
        self.assertInvalid(name="TEST", faction=Faction(name="TEST", rule_name="TEST"))
        # Test for no faction found
        self.assertInvalid(name="TEST", faction=None)
        # Test for no name found
        self.assertInvalid(name=None, faction=self.faction)

    def test_blank_description(self):
        self.assertBlankAllowed("description", **self.required_fields)

class StratagemTestCase(BaseModelTest):
    # Behaviours:
    # Stratagem must have a name
    # Stratagem may have a description (can be blank)
    # Stratagem may have a detachment (can be blank)
    # Stratagem must have a cost (default of 1)
    # Stratagem may have keywords(s)

    def setUp(self):
        self.keyword1 = KeyWord.objects.create(name="ADEPTUS ASTARTES")
        self.model_class = Faction
        self.faction = self.assertValid(name="SPM", rule_name="OATH OF MOMENT")
        self.faction = self.assertActiveKeyWord(keywords=[self.keyword1], obj=self.faction)
        self.model_class = Detachment
        self.detachment = self.assertValid(name="OATH OF MOMENT", faction=self.faction)
        self.required_fields = {
            "name" : "Armour of Contempt",
            "cost" : 1,
        }
        self.model_class = Stratagem

    def test_valid_stratagem(self):
        # Test for valid stratagem creation with all fields except keyword
        stratagem = self.assertValid(name=self.required_fields["name"], description="Test", detachment=self.detachment, cost=self.required_fields["cost"])
        # Test for valid creation with keywords and that they are in the stratagem
        stratagem = self.assertActiveKeyWord(keywords=[self.keyword1], **self.required_fields)
        # Test that the str function is working
        self.assertEqual(str(stratagem), "Armour of Contempt")

    def test_invalid_stratagem(self):
        # Test that name is required
        self.assertInvalid(name=None, cost=self.required_fields["cost"])

    def test_default_cost(self):
        # Test that cost has a default value of 1
        stratagem = self.assertValid(name=self.required_fields["name"])
        self.assertEqual(stratagem.cost, 1)
    
    def test_blank_description(self):
        # Test that description can be blank
        self.assertBlankAllowed("description", **self.required_fields)

    def test_none_faction(self):
        # Test that faction can be none
        self.assertNoneAllowed("detachment", **self.required_fields)

class UnitTestCase(BaseModelTest):
    # Behaviours:
    # Unit must have a name
    # Unit must have a faction
    # Unit may have keyword(s)

    def setUp(self):
        self.keyword1 = KeyWord.objects.create(name="ADEPTUS ASTARTES")
        self.keyword2 = KeyWord.objects.create(name="CHARACTER")
        self.model_class = Faction
        self.faction = self.assertValid(name="SPM", rule_name="OATH OF MOMENT")
        self.faction = self.assertActiveKeyWord(keywords=[self.keyword1], obj=self.faction)
        self.required_fields = {
            "name" : "Captain",
            "faction" : self.faction,
        }
        self.model_class = Unit

    def test_valid_unit(self):
        # Test for valid unit creation with all fields except keywords
        unit = self.assertValid(**self.required_fields)
        # Test for valid creation with keywords and that they are in the unit
        unit = self.assertActiveKeyWord(keywords=[self.keyword1, self.keyword2], **self.required_fields)
        # Test that the str function is working
        self.assertEqual(str(unit), "Captain")

    def test_invalid_unit(self):
        # Test that name is required
        self.assertInvalid(name=None, faction=self.faction)
        # Test that faction is reuired
        self.assertInvalid(faction=None, name=self.required_fields["name"])

class LeadershipTestCase(BaseModelTest):
    def setUp(self):
        pass
    model_class = Leadership

class UnitPointBracketCase(BaseModelTest):
    # Behaviours:
    # UnitPointBracket must have a unit
    # UnitPointBracket has a default min_models: 1
    # UnitPointBracket has a default max_models: 1
    # UnitPointBracket must have points

    def setUp(self):
        self.model_class = Faction
        self.faction = self.assertValid(name="SPM", rule_name="OATH OF MOMENT")
        self.model_class = Unit
        self.unit = self.assertValid(name="Captain", faction=self.faction)
        self.required_fields = {
            "unit" : self.unit,
            "points" : 80
        }
        self.model_class = UnitPointBracket

    def test_valid_unit_point_bracket(self):
        # Test for valid unit point bracket creation with all fields
        unit_point_bracket = self.assertValid(unit=self.required_fields["unit"], min_models=1, max_models=1, points=self.required_fields["points"])
        # Test that the str function is working
        self.assertEqual(str(unit_point_bracket), f"{self.unit.name} : {unit_point_bracket.min_models} - {unit_point_bracket.max_models} = {unit_point_bracket.points}")

    def test_invalid_unit_point_bracket(self):
        # Test that unit is required
        self.assertInvalid(unit=None, points=self.required_fields["points"])
        # Test that points is required
        self.assertInvalid(points=None, unit=self.required_fields["unit"])

    def test_default_min_max_models(self):
        # Test that min_models and max_models have a default value of 1
        unit_point_bracket = self.assertValid(**self.required_fields)
        self.assertEqual(unit_point_bracket.min_models, 1)
        self.assertEqual(unit_point_bracket.max_models, 1)
    
class EnhancementCase(BaseModelTest):
    # Behaviours:
    # Enhancement must have a name
    # Enhancement must have a detachemnt
    # Enhancement may have a description (can be blank)
    # Enhancement must have points
    # Enhancement may have keywords (can be blank)    

    def setUp(self):
        self.keyword1 = KeyWord.objects.create(name="CHARACTER")
        self.keyword2 = KeyWord.objects.create(name="CAPTAIN")
        self.model_class = Faction
        self.faction = self.assertValid(name="SPM", rule_name="OATH OF MOMENT")
        self.model_class = Detachment
        self.detachment = self.assertValid(name="Gladius Taskforce", faction=self.faction)
        self.required_fields = {
            "name" : "Adept of the Codex",
            "detachment" : self.detachment,
            "points" : 20
        }
        self.model_class = Enhancement

    def test_valid_enhancement(self):
        # Test for valid enhancement creation with all fields except keywords
        enhancement = self.assertValid(name=self.required_fields["name"], 
                                       detachment=self.required_fields["detachment"], 
                                       description="test", 
                                       points=self.required_fields["points"])
        # Test for valid creation with keywords and that the keywords are in it
        enhancement = self.assertActiveKeyWord([self.keyword1, self.keyword2], **self.required_fields)
        # Test that str function works
        self.assertEqual(str(enhancement), "Adept of the Codex")

    def test_invalid_enhancement(self):
        # Test that name is required
        self.assertInvalid(name=None, detachment=self.required_fields["detachment"], points=self.required_fields["points"])
        # Test that detachment is required
        self.assertInvalid(detachment=None, name=self.required_fields["name"], points=self.required_fields["points"])
        # Test that points is required
        self.assertInvalid(points=None, name=self.required_fields["name"], detachment=self.required_fields["detachment"])

    def test_blank_description(self):
        # Test that description can be blank
        self.assertBlankAllowed("description", **self.required_fields)

class DataSheetCase(BaseModelTest):
    # Behaviours:
    # Datasheet has a one-to-one relationship with Unit
    # Datasheet may have an upload_file (can be blank)
    # Datasheet has an uploaded_at that auto_adds to now
    # Datasheet may have a source (can be blank)

    def setUp(self):
        self.model_class = Faction
        self.faction = self.assertValid(name="SPM", rule_name="OATH OF MOMENT")
        self.model_class = Unit
        self.unit = self.assertValid(name="Captain", faction=self.faction)
        self.required_fields = {
            "unit" : self.unit,
        }
        self.model_class = DataSheet

    def test_valid_datasheet(self):
        # Test for valid datasheet creation with no upload_file
        datasheet = self.assertValid(unit=self.required_fields["unit"], source="Test")
        # Test that str function works
        self.assertEqual(str(datasheet), "Captain : Datasheet")
    
    def test_invalid_datasheet(self):
        # Test that unit is required
        self.assertInvalid(unit=None, source="Test")

    def test_uploaded_at(self):
        self.assertIsRecent(**self.required_fields)

    def test_blank_upload_file(self):
        # Test that the upload file can be blank
        self.assertBlankAllowed("upload_file", **self.required_fields)

    def test_blank_source(self):
        # Test that the source can be blank
        self.assertBlankAllowed("source", **self.required_fields)

class ArmyListCase(BaseModelTest):
    # Behaviours:
    # ArmyList must have a user
    # ArmyList may have a name (can be blank)
    # ArmyList must have a faction
    # ArmyList must have a detachment
    # ArmyList has a created_at field that auto_adds to now
    def setUp(self):
        self.model_class = User
        self.user = self.assertValid(username="test", password="test")
        self.model_class = Faction
        self.faction = self.assertValid(name="SPM", rule_name="OATH OF MOMENT")
        self.model_class = Detachment
        self.detachment = self.assertValid(name="Gladius Taskforce", faction=self.faction)
        self.required_fields = {
            "user" : self.user,
            "faction" : self.faction,
            "detachment" : self.detachment,
        }
        self.model_class = ArmyList

    def test_army_list_creation(self):
        # Test for valid army_list creation with all fields except created_at which autofills
        army_list = self.assertValid(user=self.required_fields["user"], name="Test List", faction=self.required_fields["faction"], detachment=self.required_fields["detachment"])
        # Test that str function works
        self.assertEqual(str(army_list), "Test List")

    def test_invalid_army_list_creation(self):
        # Test that user is required
        self.assertInvalid(user=None, name="Test List", faction=self.required_fields["faction"], detachment=self.required_fields["detachment"])
        # Test that faction is required
        self.assertInvalid(user=self.required_fields["user"], name="Test List", faction=None, detachment=self.required_fields["detachment"])
        # Test that detachment is required
        self.assertInvalid(user=self.required_fields["user"], name="Test List", faction=self.required_fields["faction"], detachment=None)

    def test_blank_name(self):
        self.assertBlankAllowed("name", **self.required_fields)

    def test_created_at(self):
        self.assertIsRecent(upload_flag=False, **self.required_fields)

class ArmyListEntryCase(BaseModelTest):
    # Behaviours:
    # ArmyListEntry must have an ArmyList
    # ArmyListEntry must have a Unit
    # ArmyListEntry has a default model count of 1
    # ArmyListEntry may have an Enhancement (can be blank)
    # ArmyListEntry may only have an Enhancement if the entry has the required keywords (CHARACTER ...)
    # ArmyListEntry may only have an Enhancement if it is unique to the ArmyList (no repeating enhancements)
    # ArmyListEntry may only have an Enhancement if it matches the detachment from the ArmyList
    # ArmyListEntry must have is_warlord bool (default False)
    # ArmyListEntry must not save if there is another warlord in the same ArmyList (no multiple warlords)

    def setUp(self):
        self.keyword1 = KeyWord.objects.create(name="ADEPTUS ASTARTES")
        self.keyword2 = KeyWord.objects.create(name="CHARACTER")
        self.model_class = User
        self.user = self.assertValid(username="test", password="test")
        self.model_class = Faction
        self.faction = self.assertValid(name="SPM", rule_name="OATH OF MOMENT")
        self.faction = self.assertActiveKeyWord(keywords=[self.keyword1], obj=self.faction)
        self.model_class = Unit
        self.unit = self.assertValid(name="Captain", faction=self.faction)
        self.unit = self.assertActiveKeyWord(keywords=[self.keyword1, self.keyword2], obj=self.unit)
        # Create another unit in the same faction without the required keywords
        # Create another unit in a different faction for testing
        self.model_class = Detachment
        self.detachment = self.assertValid(name="Gladius Taskforce", faction=self.faction)
        self.model_class = ArmyList
        self.army_list = self.assertValid(user=self.user, faction=self.faction, detachment=self.detachment)
        self.required_fields = {
            "army_list" : self.army_list,
            "unit" : self.unit,
        }
        self.model_class = ArmyListEntry

class AssignedLeaderCase(BaseModelTest):
    def setUp(self):
        pass
    model_class = AssignedLeader
