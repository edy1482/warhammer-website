from django.test import TestCase
from django.core.exceptions import ValidationError
from .models import KeyWord, Faction, Detachment, Stratagem

# Create your tests here.

# Universal tests:
# Assert valid model entry
# Assert invalid model entry
# Assert that field may be blank

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
    
    def assertActiveKeyWord(self, obj, keywords):
        for keyword in keywords:
            obj.keywords.add(keyword)
            self.assertIn(keyword, obj.keywords.all())
        obj.full_clean()
        obj.save()
        return obj


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

    model_class = Faction

    def setUp(self):
        self.keyword1 = KeyWord.objects.create(name="ADEPTUS ASTARTES")
        self.keyword2 = KeyWord.objects.create(name="INFANTRY")
        self.required_fields = {
            "name" : "SPM",
            "rule_name" : "OATH OF MOMENT",
        }

    def test_valid_faction(self):
        # Test for valid creation with all fields except keyword
        faction = self.assertValid(name=self.required_fields["name"], rule_name=self.required_fields["rule_name"], rule_description="Re-roll hit rolls on selected target")
        # Test for valid creation with keywords and that they are in the faction
        faction = self.assertActiveKeyWord(faction, [self.keyword1, self.keyword2])
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

    model_class = Detachment
    
    def setUp(self):
        self.keyword1 = KeyWord.objects.create(name="ADEPTUS ASTARTES")
        self.model_class = Faction
        self.faction = self.assertValid(name="SPM", rule_name="OATH OF MOMENT")
        self.faction = self.assertActiveKeyWord(self.faction, [self.keyword1])
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
        # Test for valid creation with keywords and that they are in the faction
        detachment = self.assertActiveKeyWord(detachment, [self.keyword1])
        # Test that the str function is working
        self.assertEqual(str(detachment), "Gladius Taskforce")

    def test_invalid_detachment(self):
        # Currently the only invalid factions can force an error
        # Future - make large detachment list for choice?
        #        - make certain factions invalid for certain Detachments?

        # Test for invalid faction
        self.assertInvalid(name="TEST", faction=Faction(name="TEST", rule_name="TEST"))
        # Test for no faction found
        self.assertInvalid(name="TEST")
        # Test for no name found
        self.assertInvalid(faction=self.faction)

    def test_blank_description(self):
        self.assertBlankAllowed("description", **self.required_fields)

class StratagemTestCase(BaseModelTest):
    # Behaviours:
    # Stratagem must have a name
    # Stratagem may have a description (can be blank)
    # Stratagem may have a detachment (can be blank)
    # Stratagem must have a cost
    # Stratagem may have keywords(s)
    model_class = Stratagem

    def setUp(self):
        self.keyword1 = KeyWord.objects.create(name="ADEPTUS ASTARTES")
        self.model_class = Faction
        self.faction = self.assertValid(name="SPM", rule_name="OATH OF MOMENT")
        self.faction = self.assertActiveKeyWord(self.faction, [self.keyword1])
        self.model_class = Detachment
        self.detachment = self.assertValid(name="OATH OF MOMENT", faction=self.faction)


    

