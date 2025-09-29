import datetime
from django.test import TestCase
from django.utils import timezone
from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.contrib.auth.models import User
# This is in the dependancy order
from army_app.models import KeyWord, Ability, Faction, Detachment, Enhancement, Stratagem
from army_app.models import Weapon
from army_app.models import Unit, UnitPointBracket, DataSheet
from army_app.models import Leadership
from army_app.models import ArmyList, ArmyListEntry, AssignedLeader

# Create your tests here.

#TODO decide on wargear_ability restrictions implementation (KeyWord or Ability or new model: Wargear)
#   - e.g. only Captain with relic shield can lead bladeguard vets

#TODO clean up test names

# Universal tests:
# Assert valid model entry
# Assert invalid model entry
# Assert that Char/Text field may be blank
# Assert that field may be none

class BaseModelTest(TestCase):
    model_class = None
    required_fields = {}

    def assertValid(self, **kwargs):
        obj = self.model_class(**kwargs)
        obj.full_clean()
        obj.save()
        return obj
    
    def assertInvalid(self, **kwargs):
        with self.assertRaises((ValidationError, ObjectDoesNotExist)):
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
        # Two modes: 
        # an inplace mode, where we modify an existing obj
        # new mode where we make a new obj and return it
        if obj is None:
            obj = self.assertValid(**kwargs)
        for keyword in keywords:
            obj.keywords.add(keyword)
            self.assertIn(keyword, obj.keywords.all())
        obj.full_clean()
        obj.save()
        return obj
    
    def assertActiveAbility(self, abilities, obj=None, **kwargs):
        # Two modes: 
        # an inplace mode, where we modify an existing obj
        # new mode where we make a new obj and return it
        if obj is None:
            obj = self.assertValid(**kwargs)
        for ability in abilities:
            obj.abilities.add(ability)
            self.assertIn(ability, obj.abilities.all())
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

    def assertRequired(self):
        # Test for required fields
        keys = list(self.required_fields.keys())
        for key in keys:
            # Remove key
            popped = self.required_fields.pop(key)
            # Test for invalidity
            self.assertInvalid(**self.required_fields)
            # Add key, value pair back in
            self.required_fields[key] = popped

class KeyWordTestCase(BaseModelTest):
    # Behaviours:
    # Keywords should be unique (name is unique)
    # name field is required

    def setUp(self):
        self.model_class = KeyWord
        self.required_fields = {
            "name" : "TEST"
        }
        KeyWord.objects.create(**self.required_fields)
    
    def test_required_name(self):
        # Test for required fields
        self.assertRequired()

    def test_unique_keyword(self):
        self.assertInvalid(name="TEST")

class FactionTestCase(BaseModelTest):
    # Behaviours:
    # Faction name should only be chosen from a dict: Faction.FACTION_CHOICES
    # Faction must have a rule name
    # Faction may have a rule description (can be blank)
    # Faction may have keyword(s)

    def setUp(self):
        self.model_class = KeyWord
        self.keyword1 = self.assertValid(name="ADEPTUS ASTARTES")
        self.keyword2 = self.assertValid(name="INFANTRY")
        self.required_fields = {
            "name" : "SPM",
            "rule_name" : "OATH OF MOMENT",
        }
        self.model_class = Faction

    def test_valid_faction(self):
        # Test for valid creation with all fields except keyword
        faction = self.assertValid(rule_description="Re-roll hit rolls on selected target", **self.required_fields)
        # Test for valid creation with keywords and that they are in the faction
        faction = self.assertActiveKeyWord(keywords=[self.keyword1, self.keyword2], **self.required_fields)
        # Test that the str function is working
        self.assertEqual(str(faction), "SPM")
        # Test that the name is in the choices (should be brought up by the validation, but double check)
        self.assertIn(faction.name, Faction.FACTION_CHOICES)
    
    def test_invalid_faction(self):
        # Test for required fields
        self.assertRequired()

    def test_blank_rule_description(self):
        self.assertBlankAllowed("rule_description", **self.required_fields)

class DetachmentTestCase(BaseModelTest):
    # Behaviours: 
    # Detachment must have a name
    # Detachment must have a Faction
    # Detachment may have a description (can be blank)
    # Detachment may have keyword(s) (can be empty)
    
    def setUp(self):
        self.model_class = KeyWord
        self.keyword1 = self.assertValid(name="ADEPTUS ASTARTES")
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
        detachment = self.assertValid(
            description="Once per battle, choose one effect lasting a battleturn: " \
            "Advance and shoot, Fall back and shoot and charge, Advance and charge",
            **self.required_fields
            )
        # Test for valid creation with keywords and that they are in the detachment
        detachment = self.assertActiveKeyWord(keywords=[self.keyword1], **self.required_fields)
        # Test that the str function is working
        self.assertEqual(str(detachment), "Gladius Taskforce")

    def test_invalid_detachment(self):
        # Currently the only invalid factions can force an error
        # Future - make large detachment list for choice?
        #        - make certain factions invalid for certain Detachments?
        # Test for required fields
        self.assertRequired()
        # Test for invalid faction
        self.assertInvalid(name="TEST", faction=Faction(name="TEST", rule_name="TEST"))

    def test_blank_description(self):
        self.assertBlankAllowed("description", **self.required_fields)

class EnhancementCase(BaseModelTest):
    # Behaviours:
    # Enhancement must have a name
    # Enhancement must have a detachemnt
    # Enhancement may have a description (can be blank)
    # Enhancement must have points
    # Enhancement may have keywords (can be blank)    

    def setUp(self):
        self.model_class = KeyWord
        self.keyword1 = self.assertValid(name="CHARACTER")
        self.keyword2 = self.assertValid(name="CAPTAIN")
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
        enhancement = self.assertValid(description="test", **self.required_fields)
        # Test for valid creation with keywords and that the keywords are in it
        enhancement = self.assertActiveKeyWord([self.keyword1, self.keyword2], **self.required_fields)
        # Test that str function works
        self.assertEqual(str(enhancement), "Adept of the Codex")

    def test_invalid_enhancement(self):
        # Test for required fields
        self.assertRequired()

    def test_blank_description(self):
        # Test that description can be blank
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
        }
        self.model_class = Stratagem

    def test_valid_stratagem(self):
        # Test for valid stratagem creation with all fields except keyword
        stratagem = self.assertValid(description="Test", **self.required_fields)
        # Test for valid creation with keywords and that they are in the stratagem
        stratagem = self.assertActiveKeyWord(keywords=[self.keyword1], **self.required_fields)
        # Test that the str function is working
        self.assertEqual(str(stratagem), "Armour of Contempt")

    def test_invalid_stratagem(self):
        # Test for required fields
        self.assertRequired()

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

class AbilityTestCase(BaseModelTest):
    # Behaviours:
    # Ability names are required and unique
    # Ability descriptions are required

    def setUp(self):
        self.required_fields = {
            "name" : "TEST",
            "description" : "TEST"
        }
        self.model_class = Ability

    def test_valid_ability(self):
        # Test for valid creation of Ability with all fields
        ability = self.assertValid(**self.required_fields)
        # Test that the str function is working
        self.assertEqual(str(ability), "TEST")

    def test_required_description(self):
        # Test for required fields
        self.assertRequired()

    def test_unique_ability_name(self):
        self.assertValid(**self.required_fields)
        self.assertInvalid(name="TEST", description="yes")

class WeaponTestCase(BaseModelTest):
    # Behaviours:
    # Weapon name is required
    # Weapon type is required, and must be one of the following: Ranged, Melee
    # Weapon range is not required, may be blank or null
    # Weapon attacks is required
    # Weapon skill is required
    # Weapon strength is required
    # Weapon ap is required
    # Weapon damage is required
    # Weapon abilities are not required, may be blank
    def setUp(self):
        self.model_class = Ability
        self.ability_1 = self.assertValid(name="ASSAULT", description="can be shot even if the bearer's unit Advanced")
        self.ability_2 = self.assertValid(name="HEAVY", description="Add 1 to hit rolls if bearer's unit REmained Stationary this turn")
        self.model_class = Weapon
        self.required_fields = {
            "name" : "Bolt rifle",
            "weapon_type" : "RANGED",
            "attacks" : "2",
            "skill" : "3+",
            "strength" : "4",
            "ap" : "-1",
            "damage" : "1",
        }
    
    def test_valid_weapon(self):
        # Test with only required fields
        self.assertValid(**self.required_fields)
        # Test with all fields added - range
        bolt_rifle = self.assertValid(weapon_range='24"', **self.required_fields)
        # Test with added abilities
        bolt_rifle = self.assertActiveAbility(abilities=[self.ability_1, self.ability_2], obj=bolt_rifle)
        # Test that str function is working
        self.assertEqual(str(bolt_rifle), "Bolt rifle")

    def test_invalid_weapon(self):
        # Test for required fields
        self.assertRequired()
        
        # Test for invalid weapon_type
        self.required_fields["weapon_type"] = "invalid"
        self.assertInvalid(**self.required_fields)
        # Revert back to valid weapon_type
        self.required_fields["weapon_type"] = "RANGED"

    def test_blank_weapon_range(self):
        self.assertBlankAllowed("weapon_range", **self.required_fields)

    def test_none_weapon_range(self):
        self.assertNoneAllowed("weapon_range", **self.required_fields)

class UnitTestCase(BaseModelTest):
    # Behaviours:
    # Unit must have a name
    # Unit must have a faction
    # Unit may have keyword(s)

    def setUp(self):
        self.model_class = KeyWord
        self.keyword1 = self.assertValid(name="ADEPTUS ASTARTES")
        self.keyword2 = self.assertValid(name="CHARACTER")
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
        # Test for required fields
        self.assertRequired()

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
        unit_point_bracket = self.assertValid(min_models=1, max_models=1, **self.required_fields)
        # Test that the str function is working
        self.assertEqual(str(unit_point_bracket), f"{self.unit.name} : {unit_point_bracket.min_models} - {unit_point_bracket.max_models} = {unit_point_bracket.points}")

    def test_invalid_unit_point_bracket(self):
        # Test for required fields
        self.assertRequired()

    def test_default_min_max_models(self):
        # Test that min_models and max_models have a default value of 1
        unit_point_bracket = self.assertValid(**self.required_fields)
        self.assertEqual(unit_point_bracket.min_models, 1)
        self.assertEqual(unit_point_bracket.max_models, 1)

class DataSheetCase(BaseModelTest):
    # Behaviours:
    # Datasheet has a one-to-one relationship with Unit

    def setUp(self):
        # Let's make the SPM Captain Datasheet
        self.model_class = Ability
        self.unit_ability = self.assertValid(
            name="Rites of Battle", 
            description="Once per battle round, one unit from your army with this ability can use it " \
            "when its unit is targeted with a Stratagem. If it does, reduce the CP cost of that use of " \
            "that Stratagem by 1CP.")
        self.unit_wargear_abilities = self.assertValid(
            name="Relic Shield",
            description="The bearer has a Wounds characteristic of 6"
        )
        self.model_class = Faction
        self.faction = self.assertValid(name="SPM", rule_name="OATH OF MOMENT")
        self.model_class = Unit
        self.unit = self.assertValid(name="Captain", faction=self.faction)
        self.model_class = Weapon
        self.bolt_gun = self.assertValid(
            name="Heavy bolt pistol", weapon_type="RANGED", weapon_range='18"', attacks="1", skill="2+",
            strength="4", ap="-1", damage="1"
            )
        self.required_fields = {
            "unit" : self.unit,
            "movement" : '6"',
            "toughness" : 4,
            "armour_save" : "3+",
            "wounds" : 5,
            "leadership" : "6+",
            "objective_control" : 1,
        }
        self.model_class = DataSheet

    def test_valid_datasheet(self):
        # Test for valid creation without m2m fields
        captain_datasheet = self.assertValid(invulnerable_save="4+", wargear_options="loadouts", **self.required_fields)
        # Add unit_ability
        captain_datasheet = self.assertActiveAbility(abilities=[self.unit_ability], obj=captain_datasheet)
        # Add wargear_ability
        captain_datasheet.wargear_abilities.add(self.unit_wargear_abilities)
        self.assertIn(self.unit_wargear_abilities, captain_datasheet.wargear_abilities.all())
        # Test str method
        self.assertEqual(str(captain_datasheet), "Captain : Datasheet")

    def test_invalid_datasheet(self):
        self.assertRequired()

    def test_blank_invulnerable_save(self):
        self.assertBlankAllowed("invulnerable_save", **self.required_fields)

    def test_null_invulnerable_save(self):
        self.assertNoneAllowed("invulnerable_save", **self.required_fields)

    def test_blank_wargear_options(self):
        self.assertBlankAllowed("wargear_options", **self.required_fields)

    def test_created_at(self):
        self.assertIsRecent(upload_flag=False, **self.required_fields)

class LeadershipTestCase(BaseModelTest):
    def setUp(self):
        self.model_class = KeyWord
        self.keyword1 = self.assertValid(name="LEADER")
        self.model_class = Faction
        self.faction = self.assertValid(name="SPM", rule_name="OATH OF MOMENT")
        self.model_class = Unit
        self.captain = self.assertValid(name="Captain", faction=self.faction)
        self.captain = self.assertActiveKeyWord(keywords=[self.keyword1], obj=self.captain)
        self.lieutenant = self.assertValid(name="Lieutenant", faction=self.faction)
        self.lieutenant = self.assertActiveKeyWord(keywords=[self.keyword1], obj=self.lieutenant)
        self.intercessors = self.assertValid(name="Intercessor Squad", faction=self.faction)
        self.required_fields = {
            "leader" : self.captain,
            "attached_unit" : self.intercessors,
        }
        self.model_class = Leadership

    def test_valid_leadership(self):
        # Test object creation with all fields except m2m
        test_lead = self.assertValid(**self.required_fields)
        # Add Lieutenant co_leader
        test_lead.co_leaders.add(self.lieutenant)
        # Test to see if added properly
        self.assertIn(self.lieutenant, test_lead.co_leaders.all())
        # Save to check that the co_leader validation works
        test_lead.save()

    def test_required_fields(self):
        self.assertRequired()

    def test_invalid_leadership(self):
        # Make intercessors the leader - invalid due to no LEADERSHIP keyword
        self.assertInvalid(leader=self.intercessors, attached_unit=self.intercessors)
        # Make Captain lead Lieutenant - invalid due to Lieutenant having LEADERSHIP keyword and being led
        self.assertInvalid(leader=self.captain, attached_unit=self.lieutenant)
        # Make the co_leader Intercessor, which is invalid due to no LEADERSHIP keyword
        with self.assertRaises(ValidationError):
            test_lead = self.assertValid(**self.required_fields)
            # Add Intercessor co_leader
            test_lead.co_leaders.add(self.intercessors)
            # Save to raise error
            test_lead.save()
        # Test keyword restrictions? 

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
        army_list = self.assertValid(name="Test", **self.required_fields)
        # Test that str function works
        self.assertEqual(str(army_list), "Test")

    def test_invalid_army_list_creation(self):
        # Test required fields
        self.assertRequired()
        
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
        self.model_class = KeyWord
        self.keyword1 = self.assertValid(name="ADEPTUS ASTARTES")
        self.keyword2 = self.assertValid(name="CHARACTER")
        self.model_class = User
        self.user = self.assertValid(username="test", password="test")
        self.model_class = Faction
        self.spm = self.assertValid(name="SPM", rule_name="OATH OF MOMENT")
        self.necron = self.assertValid(name="NEC", rule_name="REANIMATION PROTOCOLS")
        self.spm = self.assertActiveKeyWord(keywords=[self.keyword1], obj=self.spm)
        self.model_class = Unit
        self.captain = self.assertValid(name="Captain", faction=self.spm)
        self.captain = self.assertActiveKeyWord(keywords=[self.keyword1, self.keyword2], obj=self.captain)
        # Create another unit in the same faction without the required keywords
        self.intercessor = self.assertValid(name="Intercessor Squad", faction=self.spm)
        # Create another unit in a different faction for testing
        self.warrior = self.assertValid(name="Necron Warriors", faction=self.necron)
        self.model_class = Detachment
        self.gladius = self.assertValid(name="Gladius Taskforce", faction=self.spm)
        self.anvil = self.assertValid(name="Avil Seige Force", faction=self.spm)
        # Create an enhancement for the captain
        self.model_class = Enhancement
        self.enhancement = self.assertValid(name="Adept of the Codex", detachment=self.gladius, points=20)
        self.enhancement = self.assertActiveKeyWord(keywords=[self.keyword2], obj=self.enhancement)
        self.wrong_enhancement = self.assertValid(name="Stoic Defender", detachment=self.anvil, points=15)
        self.wrong_enhancement = self.assertActiveKeyWord(keywords=[self.keyword2], obj=self.wrong_enhancement)
        self.model_class = ArmyList
        self.army_list = self.assertValid(user=self.user, faction=self.spm, detachment=self.gladius)
        self.required_fields = {
            "army_list" : self.army_list,
            "unit" : self.captain,
        }
        self.model_class = ArmyListEntry

    def test_valid_army_list_entry(self):
        # Create the first entry (which is the captain) give it an enhancement and make it the warlord
        captain_entry = self.assertValid(is_warlord=True, enhancement=self.enhancement, **self.required_fields)
        # Create the second entry (which is the intercessor squad, with no enhancement)
        self.assertValid(unit=self.intercessor, army_list=self.army_list)
        # Check that the str method works
        self.assertEqual(str(captain_entry), f"{self.army_list} - {self.captain} → [Entry: {captain_entry.id}]")

    def test_required_fields_army_list_entry(self):
        # Test required fields
        self.assertRequired()
    
    def test_invalid_army_list_entry(self):
        # Add intercessor and set it to warlord - doesn't have character keyword
        self.assertInvalid(unit=self.intercessor, army_list=self.army_list, is_warlord=True)
        # Add intercessor and give it enhancement - doesn't have character keyword (must add it to the enhancement)
        self.assertInvalid(unit=self.intercessor, army_list=self.army_list, enhancement=self.enhancement)
        # Add valid captain who is warlord with enhancement
        self.assertValid(is_warlord=True, enhancement=self.enhancement, **self.required_fields)
        # Add necron warriors - wrong faction
        self.assertInvalid(army_list=self.army_list, unit=self.warrior)
        # Add another captain and set it to warlord - existing warlord
        self.assertInvalid(is_warlord=True, **self.required_fields)
        # Add another captain and give it the same enhancement - duplicate enhancement
        self.assertInvalid(enhancement=self.enhancement, **self.required_fields)
        # Add another captain and give it an enhancement from a different detachement, same faction
        self.assertInvalid(enhancement=self.wrong_enhancement, **self.required_fields)

    def test_default_values(self):
        captain_entry = self.assertValid(**self.required_fields)
        self.assertEqual(captain_entry.model_count, 1)
        self.assertEqual(captain_entry.is_warlord, False)

class AssignedLeaderCase(BaseModelTest):
    def setUp(self):
        self.model_class = KeyWord
        self.keyword1 = self.assertValid(name="LEADER")
        self.model_class = User
        self.user = self.assertValid(username="test", password="test")
        self.model_class = Faction
        self.spm = self.assertValid(name="SPM", rule_name="OATH OF MOMENT")
        self.model_class = Unit
        self.captain = self.assertValid(name="Captain", faction=self.spm)
        self.captain = self.assertActiveKeyWord(keywords=[self.keyword1], obj=self.captain)
        self.lieutenant = self.assertValid(name="Lieutenant", faction=self.spm)
        self.lieutenant = self.assertActiveKeyWord(keywords=[self.keyword1], obj=self.lieutenant)
        self.chaplain = self.assertValid(name="Chaplain", faction=self.spm)
        self.chaplain = self.assertActiveKeyWord(keywords=[self.keyword1], obj=self.chaplain)
        self.intercessors = self.assertValid(name="Intercessor Squad", faction=self.spm)
        self.model_class = Leadership
        self.captain_leadership = self.assertValid(leader=self.captain, attached_unit=self.intercessors)
        self.captain_leadership.co_leaders.add(self.lieutenant)
        self.lieutenant_leadership = self.assertValid(leader=self.lieutenant, attached_unit=self.intercessors)
        self.lieutenant_leadership.co_leaders.add(self.captain)
        self.chaplain_leadership = self.assertValid(leader=self.chaplain, attached_unit=self.intercessors)
        self.model_class = Detachment
        self.gladius = self.assertValid(name="Gladius Taskforce", faction=self.spm)
        self.anvil = self.assertValid(name="Avil Seige Force", faction=self.spm)
        self.model_class = ArmyList
        self.army_list = self.assertValid(user=self.user, faction=self.spm, detachment=self.gladius)
        self.other_list = self.assertValid(user=self.user, faction=self.spm, detachment=self.anvil)
        self.model_class = ArmyListEntry
        self.captain_entry = self.assertValid(army_list=self.army_list, unit=self.captain)
        self.captain_entry2 = self.assertValid(army_list=self.army_list, unit=self.captain)
        self.lieutenant_entry = self.assertValid(army_list=self.army_list, unit=self.lieutenant)
        self.chaplain_entry = self.assertValid(army_list=self.army_list, unit=self.chaplain)
        self.intercessors_entry = self.assertValid(army_list=self.army_list, unit=self.intercessors)
        self.intercessors_entry2 = self.assertValid(army_list=self.army_list, unit=self.intercessors)
        self.other_inter_entry = self.assertValid(army_list=self.other_list, unit=self.intercessors)
        self.required_fields = {
            "entry" : self.intercessors_entry,
            "leader_entry" : self.captain_entry
        }
        self.model_class = AssignedLeader

    def test_valid_AssignedLeader(self):
        # Create a valid Assigned Leader for an army_list
        test_assigned_leader = self.assertValid(**self.required_fields)
        # Add a valid co_leader
        self.assertValid(entry=self.intercessors_entry, leader_entry=self.lieutenant_entry)
        # Test str function
        self.assertEqual(str(test_assigned_leader), f"{self.captain_entry.unit} [Entry {self.captain_entry.id}] → {self.intercessors_entry.unit} [Entry {self.intercessors_entry.id}]")

    def test_required_fields(self):
        self.assertRequired()

    def test_invalid_assigned_leader(self):
        # Check if the entry and leader_entry are in the same ArmyList
        self.assertInvalid(entry=self.other_inter_entry, leader_entry=self.captain_entry)
        # Ensure Leadership rule exists
        self.assertInvalid(entry=self.captain_entry, leader_entry=self.intercessors_entry)
        # Check if any required keyword exists - skip?
        # Check co-leading rule if another leader is already assigned,
        self.assertValid(**self.required_fields)
        self.assertInvalid(entry=self.intercessors_entry, leader_entry=self.chaplain_entry)
        # Prevent leader from leading multiple separate units
        self.assertInvalid(entry=self.intercessors_entry2, leader_entry=self.captain_entry)
        # Prevent two leaders of the same unit type from leading same entry
        self.assertInvalid(entry=self.intercessors_entry, leader_entry=self.captain_entry2)