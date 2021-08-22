import os
import unittest
import owlready2 as owl2

import ontor


# noinspection PyPep8Naming
class TestCore(unittest.TestCase):
    def setUp(self):
        # prevent that the tests do influence each other -> create a new world each time
        self.world = owl2.World()

    # mark tests which only work for the "old core"
    def test_pizza1(self):

        # basic test (copied from example.py) and slightly adapted

        iri = "http://example.org/onto-ex.owl"
        fname = "./onto-ex.owl"

        # clean up remaining stuff
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


        self.assertEqual(len(list(ontor1.onto.individuals())), 0)

        ontor1.add_axioms(classes)
        ontor1.add_ops(ops)
        ontor1.add_dps(dps)
        ontor1.add_axioms(axs)
        ontor1.add_instances(ins)

        self.assertEqual(len(list(ontor1.onto.individuals())), 2)

        self.assertTrue(os.path.isfile(fname))
        ensure_file_absent(fname)


# #############################################################################
#                    Auxiliary Functions for Unittests
# #############################################################################


def ensure_file_absent(path):
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass
