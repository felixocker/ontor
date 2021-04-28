#!/usr/bin/env python3
"""minimal example for applying the onto_mngr module"""

# TODO: rename project "ontomaton"?
# TODO: add example folder under root: https://stackoverflow.com/questions/42770924/how-to-include-examples-or-test-programs-in-a-package
# https://packaging.python.org/tutorials/packaging-projects/#working-in-development-mode

import onto_mngr as om

def create_first_onto():
# TODO: move onto_ex here
    raise NotImplementedError

def create_second_onto():
# TODO: move onto_ex_add here
    raise NotImplementedError

def modify_onto():
    classes = [["test", "human", None, None, None, None, None],\
               [None, None, None, None, None, None, None],\
               ["test2", "test", None, None, None, None, False]]
    ins = [["testinstance", "human", "owns", "x1"],\
           ["ti2", None, None, None],\
           ["x1", "computer", "clock_rate", 3],\
           ["x1", "computer", "owns", "x1"]]
    my_om = om.Onto_Manager("http://example.org/onto-ex.owl", "file://./onto-ex.owl")
    my_om.add_axioms(classes)
    print([elem for elem in my_om.get_elems()[0]])
    my_om.add_ops(om.load_json("./../data/props.json")["op"])
    print([elem for elem in my_om.get_elems()[0]])
    my_om.add_dps(om.load_json("./../data/props.json")["dp"])
    print([elem for elem in my_om.get_elems()[0]])
    my_om.add_instances(ins)
    print([elem for elem in my_om.get_elems()[0]])
    my_om.add_axioms(om.load_csv("./../data/class_axioms.csv"))
    # print(*my_om.get_axioms()[0], sep="\n")
    # print("inconsistent classes")
    # print(my_om.reasoning("hermit", False))
    my_om.debug_onto()

# removing restrictions
    # print(my_om.get_class_restrictions("test2"))
    # my_om.remove_restrictions_including_prop("owns")
    # my_om.remove_restrictions_on_class("test")
    # my_om.remove_from_taxo(["test"])
    # print(my_om.get_class_restrictions("test2"))

# BUG: if disjoints are added before removal there is an attribute error - seemingly independent of whether prop is mentioned in disjoints
#    my_om.add_distinctions([["classes", ["ops1", "ops2", "ops3"]],\
#                         ["classes", ["human", "computer"]],\
#                         ["instances", ["felix", "x1"]]])

# removing entities
#    print([elem for elem in my_om.get_elems()[1]])
#    my_om.remove_elements(["owns"])
#    print([elem for elem in my_om.get_elems()[1]])

#    print(my_om.get_axioms("http://example.org/onto-ex.owl", "file://./onto-ex.owl"))
#    my_om.add_import("file://./onto-ex-add.owl")
#    my_om.save_as("test.owl")

if __name__ == "__main__":
    # create_first_onto()
    # create_second_onto()
    modify_onto()
