#!/usr/bin/env python3
"""example onto for onto mngr class"""

from owlready2 import get_ontology, Thing, DatatypeProperty, ObjectProperty,\
     locstr, FunctionalProperty, ConstrainedDatatype, SymmetricProperty

def main(iri, fname):
    """create onto and save to file"""
    onto = get_ontology(iri)
    with onto:
        class human(Thing):
            pass
        class computer(Thing):
            pass
        class owns(ObjectProperty, FunctionalProperty):
            domain = [human]
            range = [computer]
        class clock_rate(DatatypeProperty, FunctionalProperty):
            domain = [computer]
            range = [float]
        human.is_a.append(owns.some(computer))
        felix = human("felix")
        x1 = computer("x1")
        felix.owns = x1
    onto.save(file=fname)

if __name__ == "__main__":
    iri = "http://example.org/onto-ex.owl"
    fname = "./onto-ex.owl"
    main(iri, fname)
