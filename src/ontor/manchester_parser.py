#!/usr/bin/env python3
"""
parser for axioms expressed in Manchester Syntax
W3C working group note specifying the Manchester Syntax: https://www.w3.org/TR/owl2-manchester-syntax/

NOTE: at the time of writing, this is not meant to be a fully functional parser for ontologies but rather a lean parser
for single axioms expressed in Manchester Syntax
"""

from lark import Lark, Token, Tree, Transformer
import typing


def parse(grammar_file: str, axiom: str) -> typing.Union[Tree, Tree]:
    with open(grammar_file, "r") as g:
        grammar = g.read()
    lark_parser = Lark(grammar)
    return lark_parser.parse(axiom)


# [class, superclass, property,
#  inverted(bool), cardinality type, cardinality, op-object, dp-range,
#  dp-min-ex, dp-min-in, dp-exact, dp-max-in, dp-max-ex, negated(bool),
#  equivalence(bool)]

class ManchesterToOntorInput(Transformer):
    """ transform string in Manchester syntax to input for ontor
    """
    def equivalence(self, items) -> list:
        left, right = items
        if isinstance(left, str) and isinstance(right, str):
            return [left, right] + [None] * 12 + [True]
        if isinstance(left, str) and isinstance(right, list):
            return [left, None] + right + [True]
        # TODO: different cases see below

    def subsumption(self, items) -> list:
        left, right = items
        if isinstance(left, str) and isinstance(right, str):
            return [left, right] + [None] * 12 + [False]
        # TODO: different cases see below

    def op_res(self, items) -> list:
        if len(items) == 3:
            return [items[0], None, items[1], None, items[2]] + [None] * 7
        if len(items) == 4:
            return [items[0], None, items[1], items[2], items[3]] + [None] * 7

    def dp_res(self, items) -> list:
        if len(items) == 3:
            return [items[0], None, items[1], None, None] + items[2]
        if len(items) == 4:
            # TODO: cardinality restriction
            raise NotImplementedError
        # TODO: this

    def val_res(self, items) -> list:
        if isinstance(items[0], str):
            return [items[0]] + [None] * 5
        if isinstance(items[0], list):
            return items[0]

    def union(self, items) -> dict:
        return {"or": [items[0], items[1]]}

    def intersection(self, items) -> dict:
        return {"and": [items[0], items[1]]}

    def object(self, n):
        (n,) = n
        return str(n)

    def prop(self, n):
        (n,) = n
        return str(n)

    def val(self, n):
        (n,) = n
        return n

    def range(self, items):
        return [items[0]]
        # TODO: handle mins and macs correctly

    some = lambda self, _: "some"
    exactly = lambda self, _: "exactly"
    only = lambda self, _: "only"
    integer = lambda self, _: "int"
    INT = lambda self, i: int(i)
    FLOAT = lambda self, i: float(i)
    BOOL = lambda self, i: bool(i)
    STRING = lambda self, i: str(i)
    NUMBER = lambda self, i: float(i)

    # different cases
    # * both bases include only one word -> equivalence/ subsumption of classes -> one simple axiom
    # * one base includes only one word -> class axiom
    #   * other base includes a restriction -> simple class axiom
    #   * other base includes an intersection or a union -> complex class axiom
    # * both bases include a restriction, an intersection, or a union (other cases too?) -> GCA


# IDEA: function for comparing expressions in Manchester Syntax - might be helpful for checking axioms in lecture
# should be doable via AST comparison


if __name__ == "__main__":
    lark_grammar_file = "./config/manchester_syntax.config"
    example_axiom_0 = "pizza EquivalentTo tomato_bread"
    example_axiom_1 = "pizza EquivalentTo has some topping"
    example_axiom_2 = "pizza EquivalentTo has exactly 1 base"
    example_axiom_3 = "pizza EquivalentTo diam some xsd:integer"
    example_axiom_4 = "pizza EquivalentTo diam only xsd:integer [ > 0 , < 5]"
    # example_axiom_1 = "pizza EquivalentTo not ( has min 1 topping and not ( has exactly 1 base ) )"
    # example_axiom_2 = "pizza SubClassOf Inverse ( has ) min 1 topping and has only base"
    # example_axiom_3 = "Inverse ( has ) min 2 topping and has only base SubClassOf Inverse ( has ) min 1 topping and has only base"
    # example_axiom_4 = "pizza SubClassOf diam only xsd:integer [ > 0 , < 5]"
    for ax in [example_axiom_0, example_axiom_1, example_axiom_2, example_axiom_3, example_axiom_4]:
        tree = parse(lark_grammar_file, ax)
        print(ax)
        print(tree)
        print(tree.pretty())
        print(ManchesterToOntorInput().transform(tree))
