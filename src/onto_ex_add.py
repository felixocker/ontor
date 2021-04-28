#!/usr/bin/env python3
"""additional example onto for onto mngr class"""

from owlready2 import get_ontology, Thing, DatatypeProperty, ObjectProperty,\
                      locstr, FunctionalProperty, ConstrainedDatatype, SymmetricProperty

def main(iri, fname):
    """create onto and save to file"""
    onto = get_ontology(iri)
    with onto:
        class tablet(Thing):
            pass
    onto.save(file=fname)

if __name__ == "__main__":
    iri = "http://example.org/onto-ex-add.owl"
    fname = "./onto-ex-add.owl"
    main(iri, fname)
