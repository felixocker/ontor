#!/usr/bin/env python3
"""minimal example for applying the ontor module"""

import ontor

def create_first_onto():
    iri = "http://example.org/onto-ex.owl"
    fname = "./onto-ex.owl"
    classes = [["human", None, None, None, None, None, None],\
               ["computer", None, None, None, None, None, None],\
               ["process", None, None, None, None, None, None]]
    ops = [["owns", None, "human", "computer", True, False, False, False, False, False, False, None]]
    dps = [["clock_rate", None, False, "computer", "float", None, None, None, None, None]]
    axs = [["human", None, "owns", "some", None, "computer", False]]
    ins = [["felix", "human", None, None],\
           ["x1", "computer", None, None],\
           ["felix", "human", "owns", "x1"]]
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

def modify_onto():
    classes = [["test", "human", None, None, None, None, None],\
               [None, None, None, None, None, None, None],\
               ["test2", "test", None, None, None, None, False]]
    ins = [["testinstance", "human", "owns", "x1"],\
           ["ti2", None, None, None],\
           ["x1", "computer", "clock_rate", 3.1],\
           ["x1", "computer", "owns", "x1"]]
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

    ontor3.add_distinctions([["classes", ["ops1", "ops2", "ops3"]],\
                             ["classes", ["human", "computer"]],\
                             ["classes", ["human", "process"]],\
                             ["instances", ["felix", "x1"]]])

    print(ontor3.get_axioms())
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

def check_import():
    ontor4 = ontor.OntoEditor("http://example.org/onto-ex.owl", "./onto-ex.owl", ["."])
    print(ontor4.onto.imported_ontologies)

if __name__ == "__main__":
    create_first_onto()
    create_second_onto()
    modify_onto()
    check_import()
