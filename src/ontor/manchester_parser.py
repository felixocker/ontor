#!/usr/bin/env python3
"""
parser for axioms expressed in Manchester Syntax
W3C working group note specifying the Manchester Syntax: https://www.w3.org/TR/owl2-manchester-syntax/

NOTE: at the time of writing, this is not meant to be a fully functional parser for ontologies but rather a lean parser
for single axioms expressed in Manchester Syntax
"""

from lark import Lark


def parse(grammar_file: str, axiom: str):
    with open(grammar_file, "r") as g:
        grammar = g.read()
    lark_parser = Lark(grammar)
    return lark_parser.parse(axiom)


if __name__ == "__main__":
    lark_grammar_file = "./config/manchester_syntax.config"
    example_axiom_1 = "pizza EquivalentTo not ( has min 1 topping and not ( has exactly 1 base ) )"
    example_axiom_2 = "pizza SubClassOf Inverse ( has min 1 topping and has only base )"
    example_axiom_3 = "pizza SubClassOf diam only xsd:integer [ > 0 , < 5]"
    for ax in example_axiom_1, example_axiom_2:
        print(parse(lark_grammar_file, ax))
