from django.core.exceptions import ValidationError
from django.test import TestCase

from army_app.models import Faction, Detachment, Unit, UnitPointBracket, ArmyList, ArmyListEntry


class UnitPointBracketTierTest(TestCase):
    # Behaviours:
    # Brackets default to applying to every copy of a unit (1st+)
    # A unit can cost more once you take more than a certain number of copies
    #   e.g. 1st-3rd unit costs 240, 4th+ unit costs 270
    # Tiers combine with model-count brackets (5 models / 10 models per tier)
    # An army list entry is priced by which copy of the unit it is, in the order added

    def setUp(self):
        self.faction = Faction.objects.create(name="SOR")
        self.detachment = Detachment.objects.create(name="Test Detachment", faction=self.faction)
        self.army_list = ArmyList.objects.create(
            name="Test List", faction=self.faction, detachment=self.detachment,
            point_limit=2000, battle_size="strike",
        )

        # Tiered single-model unit: 1st-3rd 240, 4th+ 270
        self.tank = Unit.objects.create(
            name="Exorcist", faction=self.faction, movement='10"', toughness=10,
            armour_save="3+", wounds=11, ld="7+", objective_control=3,
        )
        self.bracket(self.tank, 1, 1, 1, 3, 240)
        self.bracket(self.tank, 1, 1, 4, None, 270)

        # Tiered squad: 1st-2nd 75/150, 3rd+ 85/170
        self.squad = Unit.objects.create(
            name="Battle Sisters Squad", faction=self.faction, movement='6"', toughness=3,
            armour_save="3+", wounds=1, ld="7+", objective_control=2,
        )
        self.bracket(self.squad, 5, 5, 1, 2, 75)
        self.bracket(self.squad, 10, 10, 1, 2, 150)
        self.bracket(self.squad, 5, 5, 3, None, 85)
        self.bracket(self.squad, 10, 10, 3, None, 170)

        # Untiered unit: defaults apply to every copy
        self.character = Unit.objects.create(
            name="Canoness", faction=self.faction, movement='6"', toughness=3,
            armour_save="3+", wounds=5, ld="6+", objective_control=1,
        )
        self.bracket(self.character, 1, 1, points=60)

    def bracket(self, unit, min_models, max_models, min_unit_number=None, max_unit_number=None, points=0):
        kwargs = {"unit": unit, "min_models": min_models, "max_models": max_models, "points": points}
        if min_unit_number is not None:
            kwargs["min_unit_number"] = min_unit_number
            kwargs["max_unit_number"] = max_unit_number
        b = UnitPointBracket(**kwargs)
        b.full_clean()
        b.save()
        return b

    def add(self, unit, model_count=1):
        return ArmyListEntry.objects.create(army_list=self.army_list, unit=unit, model_count=model_count)

    # --- model ---

    def test_defaults_apply_to_every_copy(self):
        b = self.character.point_brackets.get()
        self.assertEqual(b.min_unit_number, 1)
        self.assertIsNone(b.max_unit_number)
        self.assertFalse(b.is_tiered)
        self.assertEqual(str(b), "Canoness : 1 - 1 = 60")

    def test_tier_display(self):
        low, high = self.tank.point_brackets.all()
        self.assertEqual(low.unit_number_display, "1st-3rd")
        self.assertEqual(high.unit_number_display, "4th+")
        self.assertEqual(str(high), "Exorcist : 1 - 1 = 270 (4th+ unit)")

    def test_same_model_count_allowed_in_different_tiers(self):
        # Covered by setUp creating both tiers; a true duplicate is rejected
        with self.assertRaises(ValidationError):
            self.bracket(self.tank, 1, 1, 4, None, 300)

    def test_invalid_ranges(self):
        with self.assertRaises(ValidationError):
            self.bracket(self.character, 1, 1, 3, 2, 60)
        with self.assertRaises(ValidationError):
            self.bracket(self.character, 1, 1, 0, None, 60)
        with self.assertRaises(ValidationError):
            self.bracket(self.character, 5, 3, points=60)

    def test_unit_points_for(self):
        self.assertEqual(self.tank.points_for(1, unit_number=1), 240)
        self.assertEqual(self.tank.points_for(1, unit_number=3), 240)
        self.assertEqual(self.tank.points_for(1, unit_number=4), 270)
        self.assertEqual(self.tank.points_for(1, unit_number=9), 270)
        self.assertEqual(self.squad.points_for(10, unit_number=3), 170)
        self.assertEqual(self.character.points_for(1, unit_number=7), 60)

    def test_composition_display(self):
        self.assertEqual(
            self.tank.composition_and_points_display,
            "1st-3rd unit: 1 Exorcist (240) pts; 4th+ unit: 1 Exorcist (270) pts",
        )
        self.assertEqual(self.character.composition_and_points_display, "1 Canoness (60) pts")

    # --- army list ---

    def test_fourth_copy_costs_more(self):
        entries = [self.add(self.tank) for _ in range(5)]
        self.assertEqual([e.get_unit_number() for e in entries], [1, 2, 3, 4, 5])
        self.assertEqual([e.get_unit_points() for e in entries], [240, 240, 240, 270, 270])

    def test_tiers_with_model_counts(self):
        a = self.add(self.squad, 10)
        b = self.add(self.squad, 5)
        c = self.add(self.squad, 10)
        self.assertEqual([a.get_unit_points(), b.get_unit_points(), c.get_unit_points()], [150, 75, 170])

    def test_other_units_do_not_count(self):
        self.add(self.squad, 5)
        self.add(self.character)
        self.add(self.squad, 5)
        tanks = [self.add(self.tank) for _ in range(3)]
        self.assertEqual([t.get_unit_points() for t in tanks], [240, 240, 240])

    def test_removing_a_copy_reprices_later_copies(self):
        entries = [self.add(self.tank) for _ in range(4)]
        self.assertEqual(entries[3].get_unit_points(), 270)
        entries[0].delete()
        self.assertEqual(entries[3].get_unit_points(), 240)

    def test_unsaved_entry_priced_as_next_copy(self):
        for _ in range(3):
            self.add(self.tank)
        new = ArmyListEntry(army_list=self.army_list, unit=self.tank, model_count=1)
        self.assertEqual(new.get_unit_number(), 4)
        self.assertEqual(new.get_total_points(), 270)

    # --- overlap protection ---

    def test_overlapping_tiers_rejected(self):
        # An old "every copy" row left next to a new "4th+" row would make the 4th copy ambiguous
        with self.assertRaises(ValidationError):
            self.bracket(self.character, 1, 1, 4, None, 70)
        with self.assertRaises(ValidationError):
            self.bracket(self.tank, 1, 1, 3, 5, 250)

    def test_non_overlapping_model_ranges_allowed_in_same_tier(self):
        self.bracket(self.squad, 6, 9, 1, 2, 120)

    def test_editing_a_bracket_does_not_clash_with_itself(self):
        b = self.tank.point_brackets.get(min_unit_number=1)
        b.points = 250
        b.full_clean()
        b.save()

    def test_converting_existing_unit_via_csv(self):
        import csv, tempfile
        from army_app.data import load_unit_point_brackets
        # Canoness has an old-style "every copy = 60" row; the new CSV splits it into tiers
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, newline="") as f:
            w = csv.writer(f)
            w.writerow(["id", "unit", "min_models", "max_models", "min_unit_number", "max_unit_number", "points"])
            w.writerow([0, "Canoness", 1, 1, 1, 3, 60])
            w.writerow([1, "Canoness", 1, 1, 4, "", 75])
        errors, _ = load_unit_point_brackets(f.name)
        self.assertEqual(errors, [])
        rows = list(self.character.point_brackets.values_list("min_unit_number", "max_unit_number", "points"))
        self.assertEqual(rows, [(1, 3, 60), (4, None, 75)])
