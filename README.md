[![Build Status](https://cloud.drone.io/api/badges/felixocker/ontor/status.svg)](https://cloud.drone.io/felixocker/ontor)
[![Documentation Status](https://readthedocs.org/projects/felixocker-ontor/badge/?version=latest)](https://felixocker-ontor.readthedocs.io/en/latest/?badge=latest)
[![PyPI](https://img.shields.io/pypi/v/ontor)](https://pypi.org/project/ontor/)
[![License](https://img.shields.io/badge/license-GPLv3-blue)](https://www.gnu.org/licenses/gpl-3.0.html)

# ONTology editOR (ontor)
ontology editor built on [Owlready2](https://pypi.org/project/Owlready2/)

## functionality
each instance of the ontor class represents an individual ontology and provides support for:
* creating new, loading existing, and saving ontologies
* modifying ontologies:
  * import other ontologies
  * simply extract information such as axioms and class restrictions
  * insert classes, properties, instances, relations, and restrictions
  * insert general class axioms using a workaround for Owlready2
  * delete classes, properties, instances, relations, and restrictions but preserve the ontology's structure by reassigning subclasses and instances appropriately
* reasoning over ontologies and debugging by interactively deleting problematic axioms
* visualizing the entire ontology or selected parts thereof

ontor provides a tuple based syntax with JSON and CSV support for ontology editing to facilitate focusing on the ontology's content

## requirements and installation
* Python 3.9+
* install ontor using pip
  * from PyPI: ```pip install ontor```
  * from GitHub, in editable mode: ```pip install -e .```
* generate documentation via sphinx using the makefile in *docs/*: ```make html```

## demo

the directory *example/* includes a demo application inspired by [Protégé's pizza example](https://protegewiki.stanford.edu/wiki/Protege4Pizzas10Minutes)

### general class axioms
in addition to class axioms, General Class Axioms (GCAs) can express more complex statements - the generic axioms are equivalented using helper classes\
in the example, a uniform price of 5 is set for all pizzas with seafood toppings without making use of an explicitly defined class for these pizzas:\
```
[
  ["has_topping",null,"min",1,"seafood_topping",null,null,null,null,null,null,null,true],
  ["has_price",null,"value",null,null,"float",null,null,5,null,null,null,true]
]
```
this allows a reasoner to infer that the price for all instances of *seafood_pizza* as well as for the  instance *Another_pizza* is 5

### interactive debugging
interactively debug an ontology\
in the example: ```ontor3.debug_onto()```

<img src="https://github.com/felixocker/ontor/raw/main/docs/debug.gif" alt="interactive ontology debugging" width="500"/>

### visualization
visualize selected instances, classes, and properties in a given radius around a focus node; e.g., all nodes in a radius of two relations around the node "John"\
in the example: ```ontor3.visualize(classes=["human", "pizza"], properties=["likes", "diameter_in_cm"], focusnode="John", radius=2)```

<img src="https://github.com/felixocker/ontor/raw/main/docs/visualize.png" alt="visualize selected ontology parts" width="500"/>

### workflow

When creating ontologies from scratch, note that some functions have to be called in a specific order:
1. *add_taxo* - the taxonomy has to be created first to ensure that all classes are defined, which are required by the properties, axioms, and individuals
2. *add_ops*, *add_dps* - properties must be defined before axioms can be specified
3. *add_axioms*, *add_gcas*, *add_instances* - axioms and instances can only be added when all the necessary classes and properties have been defined

## license
GPL v3.0

## contact
Felix Ocker - [felix.ocker@googlemail.com](mailto:felix.ocker@googlemail.com)
