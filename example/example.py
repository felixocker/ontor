#!/usr/bin/env python3
"""minimal example for applying the ontor module"""

#
# This file is part of ontor (https://github.com/felixocker/ontor).
# Copyright (c) 2021 Felix Ocker.
#
# ontor is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# ontor is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with ontor.  If not, see <https://www.gnu.org/licenses/>.
#

from owlready2 import locstr
import ontor


def create_first_onto():
    iri = "http://example.org/onto-ex.owl"
    fname = "./onto-ex.owl"
    classes = [["human", None],\
               ["vegetarian", "human"],\
               ["food", None],\
               ["pizza", "food"],\
               ["pizza_base", "food"],\
               ["pizza_topping", "food"],\
               ["vegetarian_pizza", "pizza"],\
               ["margherita", "vegetarian_pizza"]]
    ops = [["likes", None, "human", None, False, False, False, False, False, False, False, None]]
    dps = [["diameter_in_cm", None, True, "pizza", "integer", None, None, None, None, None],
           ["weight_in_grams", None, True, "pizza", "float", None, None, None, None, None],
           ["description", None, False, "food", "string", None, None, None, None, None],
           ["has_price", None, True, None, "float", None, None, None, None, None]]
    axs = [["human", None, "likes", None, "some", None, "food", None, None, None, None, None, None, None, False]]
    ins = [["John", "vegetarian", None, None, None],\
           ["His_pizza", "margherita", None, None, None],\
           ["John", "vegetarian", "likes", "His_pizza", None]]
    ontor1 = ontor.OntoEditor(iri, fname)
    ontor1.add_taxo(classes)
    ontor1.add_ops(ops)
    ontor1.add_dps(dps)
    ontor1.add_axioms(axs)
    ontor1.add_instances(ins)


def create_second_onto():
    iri = "http://example.org/onto-ex-add.owl"
    fname = "./onto-ex-add.owl"
    classes = [["beverage", None],
               ["water", "beverage"]]
    ontor2 = ontor.OntoEditor(iri, fname)
    ontor2.add_taxo(classes)


def modify_onto():
    classes = [["company", None],\
               ["pizza_company", "company"],\
               ["margherita_company", "pizza_company"],\
               [None, None],\
               ["quattro_stagioni", "pizza"]]
    ins = [["Her_pizza", "quattro_stagioni", None, None, None],\
           ["Jane", "human", "likes", "Her_pizza", None],\
           ["Faulty_pizza", None, None, None, None],\
           ["Her_pizza", "quattro_stagioni", "weight_in_grams", "430.0", "float"],\
           ["Her_pizza", "quattro_stagioni", "diameter_in_cm", "32", "integer"],\
           ["Her_pizza", "quattro_stagioni", "description", "jane's pizza", "string"],\
           ["Another_pizza", "seafood_pizza", None, None, None]]
    axs = [["pizza_company", "company", "produces", None, "some", None, "pizza", None, None, None, None, None, None, None, False],
           ["pizza_company", "company", "likes", None, "some", None, "food", None, None, None, None, None, None, None, False]]
    ontor3 = ontor.OntoEditor("http://example.org/onto-ex.owl", "./onto-ex.owl")
    ontor3.add_taxo(classes)
    ontor3.add_taxo(ontor.load_csv("./data/taxo.csv"))
    # print(list(elem for elem in ontor3.get_elems()[0]))
    ontor3.add_ops(ontor.load_json("./data/props.json")["op"])
    # print(list(elem for elem in ontor3.get_elems()[0]))
    ontor3.add_dps(ontor.load_json("./data/props.json")["dp"])
    # print(list(elem for elem in ontor3.get_elems()[0]))
    ontor3.add_instances(ins)
    # print(list(elem for elem in ontor3.get_elems()[0]))
    ontor3.add_axioms(ontor.load_csv("./data/class_axioms.csv"))
    # print(*ontor3.get_axioms()[0], sep="\n")
    ontor3.add_axioms(axs)

    ontor3.add_distinctions([["classes", ["human", "pizza"]],
                             ["classes", ["has_base", "has_topping"]]])

    # print(*ontor3.get_axioms(), sep="\n")
    ontor3.add_import("file://./onto-ex-add.owl")
    # ontor3.save_as("test.owl")

    print("inconsistent classes")
    print(ontor3.reasoning("hermit", False))
    print("debugging")
    ontor3.debug_onto(assume_correct_taxo=False)

    # removing objects from the onto
    # removing restrictions by op - produces
    ontor3.remove_restrictions_including_prop("produces")
    _test_rm(ontor3.get_class_restrictions("pizza_company"),\
             ["onto-ex.likes.some(onto-ex.food)"], "produces restrictions")
    # removing restrictions by class - pizza_company
    ontor3.remove_restrictions_on_class("pizza_company")
    _test_rm(ontor3.get_class_restrictions("pizza_company"),\
             [], "restrictions on pizza_company")
    # removing entities - pizza_company
    ontor3.remove_from_taxo(["pizza_company"])
    _test_rm(ontor3.get_class_restrictions("margherita_company", res_only= False),\
             ["onto-ex.company"], "pizza_company")
    # removing relations - produces
    ontor3.remove_elements(["produces"])
    _test_rm(ontor3.get_elems()[1],\
             ["onto-ex.likes", "onto-ex.part", "onto-ex.has_base", "onto-ex.has_topping"],\
             "produces")

    # labels for rendering by labels demo - set "bylabel" to True and "lang" to "en" in "visualize"
    ontor3.add_label("John", "John's English label", "en")
    ontor3.add_label("likes", "likes' label")

    ontor3.visualize(classes=["human", "pizza"], properties=["likes", "diameter_in_cm"],\
                     focusnode="John", radius=2, bylabel=False, lang=None, open_html=True)


def _test_rm(as_is: list, as_expected: list, elem: str) -> None:
    """ check whether remove function worked as expected

    :param as_is: current elements
    :param as_expected: elements expected after modification
    """
    as_is = [str(e) for e in as_is]
    if set(as_is) == set(as_expected):
        print(f"successfully removed {elem} (reparented subclasses and instances if applicable)")
    else:
        print(f"removing {elem} failed")


def add_gcas_to_onto():
    gcas = ontor.load_json("./data/gcas.json")
    ontor4 = ontor.OntoEditor("http://example.org/onto-ex.owl", "./onto-ex.owl")
    ontor4.add_gcas(gcas)


def check_import():
    ontor4 = ontor.OntoEditor("http://example.org/onto-ex.owl", "./onto-ex.owl", ["."])
    print("Imports are:")
    print(ontor4.onto.imported_ontologies)


if __name__ == "__main__":
    ontor.cleanup(False, "log", "owl")
    create_first_onto()
    create_second_onto()
    modify_onto()
    check_import()
    add_gcas_to_onto()
