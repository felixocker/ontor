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

import ontor

def create_first_onto():
    iri = "http://example.org/onto-ex.owl"
    fname = "./onto-ex.owl"
    classes = [["human", None, None, None, None, None, None],\
               ["computer", None, None, None, None, None, None],\
               ["process", None, None, None, None, None, None]]
    ops = [["owns", None, "human", "computer", True, False, False, False, False, False, False, None]]
    dps = [["clock_rate", None, False, "computer", "float", None, None, None, None, None],
           ["pixel_width", None, False, "computer", "integer", None, None, None, None, None],
           ["description", None, False, "computer", "string", None, None, None, None, None]]
    axs = [["human", None, "owns", "some", None, "computer", None, None, None, None, None, None, False]]
    ins = [["felix", "human", None, None, None],\
           ["x1", "computer", None, None, None],\
           ["felix", "human", "owns", "x1", None]]
    ontor1 = ontor.OntoEditor(iri, fname)
    ontor1.add_axioms(classes)
    ontor1.add_ops(ops)
    ontor1.add_dps(dps)
    ontor1.add_axioms(axs)
    ontor1.add_instances(ins)

def create_second_onto():
    iri = "http://example.org/onto-ex-add.owl"
    fname = "./onto-ex-add.owl"
    classes = [["tablet", None, None, None, None, None, None]]
    ontor2 = ontor.OntoEditor(iri, fname)
    ontor2.add_axioms(classes)

def modify_onto(break_by_disjoint=False):
    """
    :param break_by_disjoint: if True disjoints are added that the reasoner cannot handle
    """
    classes = [["test", "human", None, None, None, None, None],\
               [None, None, None, None, None, None, None],\
               ["test2", "test", None, None, None, None, False]]
    ins = [["testinstance", "human", "owns", "x1", None],\
           ["ti2", None, None, None, None],\
           ["x1", "computer", "clock_rate", "3.1", "float"],\
           ["x1", "computer", "pixel_width", "1920", "integer"],\
           ["x1", "computer", "description", "my personal x1", "string"],\
           ["x1", "computer", "owns", "x1", None]]
    ontor3 = ontor.OntoEditor("http://example.org/onto-ex.owl", "./onto-ex.owl")
    ontor3.add_axioms(classes)
    print(list(elem for elem in ontor3.get_elems()[0]))
    ontor3.add_ops(ontor.load_json("./data/props.json")["op"])
    print(list(elem for elem in ontor3.get_elems()[0]))
    ontor3.add_dps(ontor.load_json("./data/props.json")["dp"])
    print(list(elem for elem in ontor3.get_elems()[0]))
    ontor3.add_instances(ins)
    print(list(elem for elem in ontor3.get_elems()[0]))
    ontor3.add_axioms(ontor.load_csv("./data/class_axioms.csv"))
    print(*ontor3.get_axioms()[0], sep="\n")

    ontor3.add_distinctions([["classes", ["human", "process"]]])

    if break_by_disjoint:
        ontor3.add_distinctions([["classes", ["ops1", "ops2", "ops3"]],\
                                 ["classes", ["human", "computer"]],\
                                 ["instances", ["felix", "x1"]]])

    print(*ontor3.get_axioms(), sep="\n")
    ontor3.add_import("file://./onto-ex-add.owl")
    ontor3.save_as("test.owl")

#    ontor3.remove_restrictions_on_class("test2")

    print("inconsistent classes")
    print(ontor3.reasoning("hermit", False))
    print("debugging")
    ontor3.debug_onto()

    # # removing restrictions
    # print(ontor3.get_class_restrictions("test2"))
    # ontor3.remove_restrictions_including_prop("owns")
    # ontor3.remove_restrictions_on_class("test")
    # ontor3.remove_from_taxo(["test"])
    # print(ontor3.get_class_restrictions("test2"))

    # # removing entities
    # print([elem for elem in ontor3.get_elems()[1]])
    # ontor3.remove_elements(["ops1"])
    # print([elem for elem in ontor3.get_elems()[1]])

    # ontor3.export_ntriples()
    # ontor3.visualize()
    ontor3.visualize(["human", "computer"], ["owns", "ops2"], "felix", 2)

def check_import():
    ontor4 = ontor.OntoEditor("http://example.org/onto-ex.owl", "./onto-ex.owl", ["."])
    print("Imports are:")
    print(ontor4.onto.imported_ontologies)

if __name__ == "__main__":
    create_first_onto()
    create_second_onto()
    modify_onto()
    check_import()
