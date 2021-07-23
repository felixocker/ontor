# ONTology editOR (ontor)
ontology editor built on Owlready2

## functionality
each instance of the ontor class represents an individual ontology and provides support for:
* creating new, loading existing, and saving ontologies
* modifying ontologies:
  * import other ontologies
  * simply extract information such as axioms and class restrictions
  * insert classes, properties, instances, relations, and restrictions
  * delete classes, properties, instances, relations, and restrictions but preserve the ontology's structure by reassigning subclasses and instances appropriately
* reasoning over ontologies and debugging by interactively deleting problematic axioms
* visualizing the entire ontology or selected parts thereof

ontor provides a tuple based syntax with JSON and CSV support for ontology editing to facilitate focusing on the ontology's content

## installation
install ontor to run the example, possibly in editable mode:\
```pip install -e .```

## demo
interactively debug your ontology\
in the example: ```ontor3.debug_onto()```

<img src="docs/debug.gif" width="500"/>

visualize selected classes and properties within a radius of two relations around the node "felix"\
in the example: ```ontor3.visualize(["human", "computer"], ["owns", "ops2"], "felix", 2)```

<img src="docs/visualize.png" alt="visualize selected ontology parts" width="500"/>

## license
GPL v3.0

## contact
Felix Ocker - [felix.ocker@googlemail.com](mailto:felix.ocker@googlemail.com)
