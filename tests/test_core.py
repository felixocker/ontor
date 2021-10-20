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


    def tearDown(self):
        """ remove temporary files: ontology and logs
        """
        ensure_file_absent(self.fname)
        ontor.cleanup(True, "log")


    def test_onto_creation(self):
        """ basic test for ontology creation functions
        """
        iri = "http://example.org/onto-ex.owl"
        fname = "./onto-ex.owl"

        ensure_file_absent(fname)

        classes = [["human", None, None, None, None, None, None],\
                   ["vegetarian", "human", None, None, None, None, None],\
                   ["food", None, None, None, None, None, None],\
                   ["pizza", "food", None, None, None, None, None],\
                   ["pizza_base", "food", None, None, None, None, None],\
                   ["pizza_topping", "food", None, None, None, None, None],\
                   ["vegetarian_pizza", "pizza", None, None, None, None, None],\
                   ["margherita", "vegetarian_pizza", None, None, None, None, None]]
        ops = [["likes", None, "human", None, False, False, False, False, False, False, False, None]]
        dps = [["diameter_in_cm", None, True, "pizza", "integer", None, None, None, None, None],
               ["weight_in_grams", None, True, "pizza", "float", None, None, None, None, None],
               ["description", None, False, "food", "string", None, None, None, None, None]]
        axs = [["human", None, "likes", None, "some", None, "food", None, None, None, None, None, None, None, False]]
        ins = [["John", "vegetarian", None, None, None],\
               ["His_pizza", "margherita", None, None, None],\
               ["John", "vegetarian", "likes", "His_pizza", None]]
        ontor1 = ontor.OntoEditor(iri, fname)

        self.assertEqual(len(list(ontor1.onto.classes())), 0)
        self.assertEqual(len(list(ontor1.onto.object_properties())), 0)
        self.assertEqual(len(list(ontor1.onto.data_properties())), 0)
        self.assertEqual(len(list(ontor1.onto.individuals())), 0)

        ontor1.add_axioms(classes)
        ontor1.add_ops(ops)
        ontor1.add_dps(dps)
        ontor1.add_instances(ins)
        ontor1.add_axioms(axs)

        self.assertEqual(len(list(ontor1.onto.classes())), len(classes), "number of classes not as expected")
        self.assertEqual(len(list(ontor1.onto.object_properties())), len(ops), "number of object properties not as expected")
        self.assertEqual(len(list(ontor1.onto.data_properties())), len(dps), "number of datatype properties not as expected")
        self.assertEqual(len(list(ontor1.onto.individuals())), len(set([i[0] for i in ins])), "number of instances not as expected")
        self.assertIn(ontor1.onto["likes"].some(ontor1.onto["food"]), ontor1.onto["human"].is_a, "axiom not created as expected")
        self.assertTrue(os.path.isfile(fname))


    def test_label_creation(self):
        """ check label creation, also with localized strings
        """
        iri = "http://example.org/onto-ex.owl"
        fname = "./onto-ex.owl"

        ensure_file_absent(fname)

        classes = [["ex-r-01", None, None, None, None, None, None],\
                   ["ex-r-02", None, None, None, None, None, None]]
        labels = [["ex-r-01", "human", "en"],
                  ["ex-r-01", "homme", "fr"],
                  ["ex-r-02", "food"]]

        ontor1 = ontor.OntoEditor(iri, fname)
        ontor1.add_axioms(classes)

        self.assertEqual(ontor1.onto["ex-r-01"].label, [])
        self.assertEqual(ontor1.onto["ex-r-02"].label, [])

        for l in labels:
            ontor1.add_label(*l)

        self.assertEqual(len(ontor1.onto["ex-r-01"].label) + len(ontor1.onto["ex-r-02"].label), len(labels), "number of labels not as expected")
        self.assertEqual(len([l for l in ontor1.onto["ex-r-01"].label if l.lang=="fr"]), 1, "number of French labels not as expected")
        self.assertEqual(ontor1.onto["ex-r-02"].label.first(), "food", "label without language not as expected")


    def test_removal(self):
        """ check removal functions
        """
        iri = "http://example.org/onto-ex.owl"
        fname = "./onto-ex.owl"

        ensure_file_absent(fname)

        classes = [["a", None, None, None, None, None, None],\
                   ["b", "a", None, None, None, None, None],\
                   ["c", "b", None, None, None, None, None],\
                   ["d", None, None, None, None, None, None]]
        ins = [["A", "a", None, None, None],
               ["B", "b", None, None, None]]
        ops = [["rel", None, None, None, False, False, False, False, False, False, False, None],
               ["rel2", None, None, None, False, False, False, False, False, False, False, None]]
        axs = [["d", None, "rel", None, "max", 1, "a", None, None, None, None, None, None, None, False],
               ["d", None, "rel", None, "max", 1, "b", None, None, None, None, None, None, None, False],
               ["b", None, "rel2", None, "some", None, "d", None, None, None, None, None, None, None, False]]

        def _init_example() -> ontor.OntoEditor:
            ontor1 = ontor.OntoEditor(iri, fname)
            ontor1.add_axioms(classes)
            ontor1.add_ops(ops)
            ontor1.add_axioms(axs)
            ontor1.add_instances(ins)
            # check onto creation
            self.assertTrue(all([ontor1.onto[i[0]] in ontor1.onto.classes() for i in classes]), "onto classes not created as expected")
            self.assertTrue(all([ontor1.onto[i[0]] in ontor1.onto.individuals() for i in ins]), "onto individuals not created as expected")
            self.assertIn(ontor1.onto["rel"].max(1, ontor1.onto["a"]), ontor1.onto["d"].is_a, "axiom not created as expected")
            self.assertIn(ontor1.onto["rel"].max(1, ontor1.onto["b"]), ontor1.onto["d"].is_a, "axiom not created as expected")
            self.assertIn(ontor1.onto["rel2"].some(ontor1.onto["d"]), ontor1.onto["b"].is_a, "axiom not created as expected")
            return ontor1

        # remove class, its subclasses, instancees, and appearances in axiom
        ontor1 = _init_example()
        ontor1.remove_elements(["a"])
        self.assertNotIn("a", [c.name for c in ontor1.onto.classes()], "onto class not removed as expected")
        self.assertNotIn("b", [c.name for c in ontor1.onto.classes()], "onto subclass not removed as expected")
        self.assertNotIn("A", [c.name for c in ontor1.onto.individuals()], "onto individual not removed as expected")
        self.assertNotIn("onto-ex.rel2.max(1, onto-ex.a)", [str(ax) for ax in ontor1.onto["d"].is_a], "onto axiom not removed as expected")
        ensure_file_absent(fname)

        # remove class only, reparent its subclasses, instances, and axioms
        ontor1 = _init_example()
        ontor1.remove_from_taxo(elem_list=["b"], reassign=True)
        self.assertNotIn("b", [c.name for c in ontor1.onto.classes()], "onto class not removed as expected")
        self.assertIn(ontor1.onto["a"], ontor1.onto["c"].is_a, "onto subclass not reparented as expected")
        self.assertIn(ontor1.onto["a"], ontor1.onto["B"].is_a, "onto individual not reparented as expected")
        self.assertNotIn("onto-ex.rel.max(1, onto-ex.b)", [str(ax) for ax in ontor1.onto["d"].is_a], "onto axiom not removed as expected")
        self.assertNotIn("onto-ex.rel2.some(onto-ex.b)", [str(ax) for ax in ontor1.onto["c"].is_a], "onto axiom not propagated as expected")
        ensure_file_absent(fname)

        # remove restrictions on class
        ontor1 = _init_example()
        ontor1.remove_restrictions_on_class("b")
        self.assertTrue(all([type(p) != Restriction for p in ontor1.onto["b"].is_a]), "class restrictions not removed as expected")
        ensure_file_absent(fname)

        # remove all class restrictions including a certain property
        ontor1 = _init_example()
        ontor1.remove_restrictions_including_prop("rel")
        self.assertNotIn(ontor1.onto["rel"].max(1, ontor1.onto["a"]), ontor1.onto["d"].is_a, "axiom not removed as expected")
        self.assertNotIn(ontor1.onto["rel"].max(1, ontor1.onto["b"]), ontor1.onto["d"].is_a, "axiom not removed as expected")
        self.assertIn(ontor1.onto["rel2"].some(ontor1.onto["d"]), ontor1.onto["b"].is_a, "axiom not kept as expected")


    def test_debugging(self):
        """ check interactive debugging process; uses minimal example with two
        contradicting axioms for a class and its parent class
        """
        iri = "http://example.org/onto-ex.owl"
        fname = "./onto-ex.owl"

        ensure_file_absent(fname)

        classes = [["a", None, None, None, None, None, None],\
                   ["b", "a", None, None, None, None, None],\
                   ["c", None, None, None, None, None, None]]
        ops = [["likes", None, None, None, False, False, False, False, False, False, False, None]]
        axs = [["a", None, "likes", None, "min", 2, "c", None, None, None, None, None, None, None, False],
               ["b", None, "likes", None, "max", 1, "c", None, None, None, None, None, None, None, False]]

        ontor1 = ontor.OntoEditor(iri, fname)
        ontor1.add_axioms(classes)
        ontor1.add_ops(ops)
        ontor1.add_axioms(axs)

        debug_inputs = {
            "Show further information? [y(es), n(o), q(uit)]": "n",
            "Potentially inconsistent axiom: b is_a onto-ex.a\nDelete is_a axiom? [y(es), n(o), q(uit)]": "n",
            "Potentially inconsistent axiom: b is_a onto-ex.likes.max(1, onto-ex.c)\nDelete is_a axiom? [y(es), n(o), q(uit)]": "y",
        }

        with suppress():
            with unittest.mock.patch('builtins.input', side_effect=debug_inputs.values()):
                ontor1.debug_onto(reasoner="hermit", assume_correct_taxo=False)


    def test_visu(self):
        """ test html creation for visu using a minimal example
        """
        iri = "http://example.org/onto-ex.owl"
        fname = "./onto-ex.owl"

        ensure_file_absent(fname)

        classes = [["a", None, None, None, None, None, None],\
                   ["b", "a", None, None, None, None, None],\
                   ["c", None, None, None, None, None, None]]
        ops = [["rel", None, None, None, False, False, False, False, False, False, False, None]]
        axs = [["a", None, "rel", None, "min", 2, "c", None, None, None, None, None, None, None, False],
               ["b", None, "rel", None, "max", 1, "c", None, None, None, None, None, None, None, False]]

        ontor1 = ontor.OntoEditor(iri, fname)
        ontor1.add_axioms(classes)
        ontor1.add_ops(ops)
        ontor1.add_axioms(axs)

        ontor1.visualize(classes=["a", "b"], properties=["rel"], focusnode="b", radius=1)
        html_file = ontor1.path.rsplit(".", 1)[0] + ".html"
        gold_visu = self.test_dir / "data/gold_visu.html"
        self.assertTrue(filecmp.cmp(html_file, gold_visu), "html generated for ontology visu not as expected")

        # bespoke teardown
        ensure_file_absent(html_file)



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
