#!/usr/bin/env python3

import filecmp
import os
import sys
import unittest
import unittest.mock
from contextlib import contextmanager
from pathlib import Path

from owlready2.class_construct import Restriction

import ontor


class TestCore(unittest.TestCase):

    test_dir = Path(__file__).parent
    fname = "./onto-ex.owl"
    iri = "http://example.org/onto-ex.owl"

    def setUp(self):
        """ set up standardized minimal onto for tests
        """
        ensure_file_absent(self.fname)

        self.classes = [["human", None],
                        ["vegetarian", "human"],
                        ["food", None],
                        ["pizza", "food"],
                        ["pizza_base", "food"],
                        ["pizza_topping", "food"],
                        ["meat", "pizza_topping"],
                        ["vegetarian_pizza", "pizza"],
                        ["margherita", "vegetarian_pizza"],
                        ["mozzarella", "pizza_topping"]]
        self.ops = [["likes", None, "human", None, False, False, False, False, False, False, False, None],
                    ["has_part", None, None, None, False, False, False, False, False, False, False, None],
                    ["has_topping", "has_part", "pizza", "pizza_topping", False, False, False, False, False, False, False, None]]
        self.dps = [["diameter_in_cm", None, True, "pizza", "integer", None, None, None, None, None],
                    ["weight_in_grams", None, True, "pizza", "float", 0, None, None, None, None],
                    ["description", None, False, "food", "string", None, None, None, None, None],
                    ["price", None, True, "food", "float", None, None, None, None, None]]
        self.axs = [["human", None, "likes", None, "some", None, "food", None, None, None, None, None, None, None, False],
                    ["vegetarian", None, "likes", None, "only", None, "vegetarian_pizza", None, None, None, None, None, None, None, False],
                    ["vegetarian_pizza", None, "has_topping", None, "exactly", 0, "meat", None, None, None, None, None, None, None, False]]
        self.ins = [["John", "vegetarian", None, None, None],
                    ["His_pizza", "margherita", None, None, None],
                    ["Veggie_individual", "vegetarian_pizza", "diameter_in_cm", 32, "integer"],
                    ["John", "vegetarian", "likes", "His_pizza", None]]

        self.ontor1 = ontor.OntoEditor(self.iri, self.fname)
        self.ontor1.add_taxo(self.classes)
        self.ontor1.add_ops(self.ops)
        self.ontor1.add_dps(self.dps)
        self.ontor1.add_instances(self.ins)
        self.ontor1.add_axioms(self.axs)

    def tearDown(self):
        """ remove temporary files: ontology and logs
        """
        ensure_file_absent(self.fname)
        ontor.cleanup(True, "log")

    def test_onto_creation(self):
        """ test ontology creation functions for adding classes, properties,
        instances, and axioms
        """
        self.assertEqual(len(list(self.ontor1.onto.classes())), len(self.classes), "number of classes not as expected")
        self.assertEqual(len(list(self.ontor1.onto.object_properties())), len(self.ops), "number of object properties not as expected")
        self.assertEqual(len(list(self.ontor1.onto.data_properties())), len(self.dps), "number of datatype properties not as expected")
        self.assertEqual(len(list(self.ontor1.onto.individuals())), len(set([i[0] for i in self.ins])), "number of instances not as expected")
        self.assertIn(self.ontor1.onto["likes"].some(self.ontor1.onto["food"]), self.ontor1.onto["human"].is_a, "axiom not created as expected")
        self.assertIn(self.ontor1.onto["has_topping"].exactly(0, self.ontor1.onto["meat"]), self.ontor1.onto["vegetarian_pizza"].is_a, "axiom not created as expected")
        self.assertEqual(len(self.ontor1.onto["weight_in_grams"].range), 1, "number of dp range elements not as expected")
        self.assertEqual(self.ontor1.onto["weight_in_grams"].range[0].min_exclusive, 0, "limit of dp range not as expected")
        self.assertTrue(os.path.isfile(self.fname))

    def test_label_creation(self):
        """ check label creation, also with localized strings
        """
        labels = [["human", "human", "en"],
                  ["human", "homme", "fr"],
                  ["food", "food"]]
        self.assertEqual(self.ontor1.onto["human"].label, [])
        self.assertEqual(self.ontor1.onto["food"].label, [])

        for l in labels:
            self.ontor1.add_label(*l)

        self.assertEqual(len(self.ontor1.onto["human"].label) + len(self.ontor1.onto["food"].label), len(labels), "number of labels not as expected")
        self.assertEqual(len([l for l in self.ontor1.onto["human"].label if l.lang=="fr"]), 1, "number of French labels not as expected")
        self.assertEqual(self.ontor1.onto["food"].label.first(), "food", "label without language not as expected")

    def test_element_removal_full(self):
        """ test removal of a class, its subclasses, instancees, and appearances in axiom
        """
        self.ontor1.remove_elements(["vegetarian_pizza"])
        self.assertNotIn("vegetarian_pizza", [c.name for c in self.ontor1.onto.classes()], "onto class not removed as expected")
        self.assertNotIn("margherita", [c.name for c in self.ontor1.onto.classes()], "onto subclass not removed as expected")
        self.assertNotIn("His_pizza", [c.name for c in self.ontor1.onto.individuals()], "onto individual not removed as expected")
        self.assertNotIn("onto-ex.likes.only(onto-ex.vegetarian_pizza)", [str(ax) for ax in self.ontor1.onto["vegetarian"].is_a], "onto axiom not removed as expected")

    def test_element_removal_selected(self):
        """ test removal of a class only, but when its subclasses, instances,
        and axioms are reparented
        """
        self.ontor1.remove_from_taxo(elem_list=["vegetarian_pizza"], reassign=True)
        self.assertNotIn("vegetarian_pizza", [c.name for c in self.ontor1.onto.classes()], "onto class not removed as expected")
        self.assertIn(self.ontor1.onto["pizza"], self.ontor1.onto["margherita"].is_a, "onto subclass not reparented as expected")
        self.assertIn(self.ontor1.onto["pizza"], self.ontor1.onto["Veggie_individual"].is_a, "onto individual not reparented as expected")
        self.assertNotIn("onto-ex.likes.only(onto-ex.vegetarian_pizza)", [str(ax) for ax in self.ontor1.onto["vegetarian"].is_a], "onto axiom not removed as expected")
        self.assertIn("onto-ex.has_topping.exactly(0, onto-ex.meat)", [str(ax) for ax in self.ontor1.onto["margherita"].is_a], "onto axiom not propagated as expected")

    def test_restriction_removal(self):
        """ test removal of class restrictions
        """
        self.ontor1.remove_restrictions_on_class("vegetarian_pizza")
        self.assertTrue(all([type(p) != Restriction for p in self.ontor1.onto["vegetarian_pizza"].is_a]), "class restrictions not removed as expected")

    def test_restriction_removal_by_prop(self):
        """ test removal of all class restrictions including a certain property
        """
        self.ontor1.remove_restrictions_including_prop("likes")
        self.assertNotIn(self.ontor1.onto["likes"].some(self.ontor1.onto["food"]), self.ontor1.onto["human"].is_a, "axiom not removed as expected")
        self.assertNotIn(self.ontor1.onto["likes"].only(self.ontor1.onto["vegetarian_pizza"]), self.ontor1.onto["vegetarian"].is_a, "axiom not removed as expected")
        self.assertIn(self.ontor1.onto["has_topping"].exactly(0, self.ontor1.onto["meat"]), self.ontor1.onto["vegetarian_pizza"].is_a, "axiom not kept as expected")

    def test_debugging(self):
        """ check interactive debugging process; adds two contradicting axioms
        """
        contr_axs = [["pizza_topping", None, "has_part", None, "min", 4, "pizza_topping", None, None, None, None, None, None, None, False],
                     ["mozzarella", None, "has_part", None, "max", 2, "pizza_topping", None, None, None, None, None, None, None, False]]
        self.ontor1.add_axioms(contr_axs)

        debug_inputs = {
            "Show further information? [y(es), n(o), q(uit)]": "n",
            "Potentially inconsistent axiom: mozzarella is_a onto-ex.pizza_topping\nDelete is_a axiom? [y(es), n(o), q(uit)]": "n",
            "Potentially inconsistent axiom: mozzarella is_a onto-ex.has_part.max(2, onto-ex.pizza_topping)\nDelete is_a axiom? [y(es), n(o), q(uit)]": "y",
        }
        with suppress():
            with unittest.mock.patch('builtins.input', side_effect=debug_inputs.values()):
                self.ontor1.debug_onto(reasoner="hermit", assume_correct_taxo=False)

    def test_visu(self):
        """ test html creation for visu using a minimal example
        """
        self.ontor1.visualize(classes=["human", "pizza"], properties=["likes"], focusnode="John", radius=1)
        html_file = self.ontor1.path.rsplit(".", 1)[0] + ".html"
        gold_visu = self.test_dir / "data/gold_visu.html"
        self.assertTrue(filecmp.cmp(html_file, gold_visu), "html generated for ontology visu not as expected")
        # bespoke teardown
        ensure_file_absent(html_file)

    def test_gca(self):
        """ test reasoning with general class axiom
        """
        gca_ex = [[["diameter_in_cm", None, "value", None, None, "integer", None, None, 32, None, None, None, True],
                   ["price", None, "value", None, None, "float", None, None, 5.0, None, None, None, True]]]
        self.ontor1.add_gcas(gca_ex)
        self.ontor1.reasoning(reasoner="pellet", save=True)
        self.assertEqual(getattr(self.ontor1.onto["Veggie_individual"], "price"), 5,
                         "GCA inference not as expected")

    def test_nested_axiom(self):
        """ test whether nested axioms that include logical operators are added correctly
        """
        compl_axs = [{"and": [["human", None, "likes", None, "some", None, "pizza", None, None, None, None, None, None, None, False],
                              ["human", None, "likes", None, "some", None, "human", None, None, None, None, None, None, None, False]]}]
        self.ontor1.add_axioms(compl_axs)
        self.assertIn(self.ontor1.onto["likes"].some(self.ontor1.onto["pizza"]) &
                      self.ontor1.onto["likes"].some(self.ontor1.onto["human"]), self.ontor1.onto["human"].is_a,
                      "complex axiom not added as expected")


# auxiliary functions for unit tests


@contextmanager
def suppress():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


def ensure_file_absent(path):
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


if __name__ == "__main__":
    unittest.main()
