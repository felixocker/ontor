#!/usr/bin/env python3
"""minimal example for applying the ontor module"""

import ontor

def create_first_onto():
    iri = "http://example.org/onto-ex.owl"
    fname = "./onto-ex.owl"
    classes = [["human", None, None, None, None, None, None],\
               ["computer", None, None, None, None, None, None]]
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
           ["x1", "computer", "clock_rate", 3],\
           ["x1", "computer", "owns", "x1"]]
    my_ontor = ontor.OntoEditor("http://example.org/onto-ex.owl", "file://./onto-ex.owl")
    my_ontor.add_axioms(classes)
    print(list(elem for elem in my_ontor.get_elems()[0]))
    my_ontor.add_ops(ontor.load_json("./data/props.json")["op"])
    print(list(elem for elem in my_ontor.get_elems()[0]))
    my_ontor.add_dps(ontor.load_json("./data/props.json")["dp"])
    print(list(elem for elem in my_ontor.get_elems()[0]))
    my_ontor.add_instances(ins)
    print(list(elem for elem in my_ontor.get_elems()[0]))
    my_ontor.add_axioms(ontor.load_csv("./data/class_axioms.csv"))
    print(*my_ontor.get_axioms()[0], sep="\n")
    print("inconsistent classes")
    print(my_ontor.reasoning("hermit", False))
    my_ontor.debug_onto()

# removing restrictions
    # print(my_ontor.get_class_restrictions("test2"))
    # my_ontor.remove_restrictions_including_prop("owns")
    # my_ontor.remove_restrictions_on_class("test")
    # my_ontor.remove_from_taxo(["test"])
    # print(my_ontor.get_class_restrictions("test2"))

# BUG: if disjoints are added before removal there is an attribute error
# BUG: seemingly independent of whether prop is mentioned in disjoints
#    my_ontor.add_distinctions([["classes", ["ops1", "ops2", "ops3"]],\
#                         ["classes", ["human", "computer"]],\
#                         ["instances", ["felix", "x1"]]])

# removing entities
#    print([elem for elem in my_ontor.get_elems()[1]])
#    my_ontor.remove_elements(["owns"])
#    print([elem for elem in my_ontor.get_elems()[1]])

    print(my_ontor.get_axioms())
    my_ontor.add_import("file://./onto-ex-add.owl")
    my_ontor.save_as("test.owl")

if __name__ == "__main__":
    create_first_onto()
    create_second_onto()
    modify_onto()
