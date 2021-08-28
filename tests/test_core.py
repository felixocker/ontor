#!/usr/bin/env python3

import os
import unittest

import ontor


class TestCore(unittest.TestCase):

    def test_onto_creation(self):
        """ basic test for ontology creation functions
        """

        iri = "http://example.org/onto-ex.owl"
        fname = "./onto-ex.owl"

        # clean up
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
        self.assertTrue(ontor1.onto["likes"].some(ontor1.onto["food"]) in ontor1.onto["human"].is_a)

        self.assertTrue(os.path.isfile(fname))

        # clean up
        ensure_file_absent(fname)
        cleanup_logs()


# auxiliary functions for unit tests

def ensure_file_absent(path):
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass

def cleanup_logs():
    dir = "./"
    logfiles = [f for f in os.listdir(dir) if f.endswith(".log")]
    for f in logfiles:
        os.remove(os.path.join(dir, f))


if __name__ == "__main__":
    unittest.main()
