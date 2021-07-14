#!/usr/bin/env python3
"""ONTology editOR (ontor) module"""

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

import csv
import datetime
import importlib.resources as pkg_resources
import json
import logging
import os
import sys
import textwrap
import traceback
from contextlib import contextmanager
from io import StringIO
from owlready2 import destroy_entity, get_ontology, types, Thing, Nothing,\
                      AllDisjoint, AllDifferent, DataProperty, ObjectProperty,\
                      FunctionalProperty, InverseFunctionalProperty,\
                      TransitiveProperty, SymmetricProperty, AsymmetricProperty,\
                      ReflexiveProperty, IrreflexiveProperty, World, default_world,\
                      Restriction, ConstrainedDatatype, sync_reasoner_hermit, sync_reasoner_pellet,\
                      onto_path
import queries

logger = logging.getLogger(__name__)
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
logging.basicConfig(filename=timestamp+"_om.log", level=logging.DEBUG)

@contextmanager
def redirect_to_log():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        result_out = StringIO()
        result_err = StringIO()
        sys.stdout = result_out
        sys.stderr = result_err
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            if result_out.getvalue():
                logger.info(f"reasoner output redirect: \n{indent_log(result_out.getvalue())}")
            if result_err.getvalue():
                logger.info(f"reasoner errors redirect: \n{indent_log(result_err.getvalue())}")

def indent_log(info):
    return textwrap.indent(info, '>   ')

def load_csv(csv_file):
    with open(csv_file) as f:
        data = list(csv.reader(f))
    return data

def load_json(json_file):
    with open(json_file) as f:
        data = json.load(f)
    return data

class OntoEditor:
    """create, load, and edit ontologies"""

    _prop_types = [FunctionalProperty, InverseFunctionalProperty, TransitiveProperty,\
                   SymmetricProperty, AsymmetricProperty, ReflexiveProperty, IrreflexiveProperty]
    _dp_range_types = {"boolean": bool,
                       "float": float,
                       "integer": int,
                       "string": str,
                       "date": datetime.date,
                       "time": datetime.time,
                       "datetime": datetime.datetime}

    def __init__(self, iri, path, import_paths=None):
        """
        tries to load onto from file specified, creates new file if none is available
        :param iri: ontology's IRI
        :param path: path to local ontology file or URL; local is checked first
        :param import_paths: list of local directories to be checked for imports
        """
        self.iri = iri
        self.path = path
        self.filename = path.split(sep="/")[-1]
        self.query_prefixes = pkg_resources.read_text(queries, 'prefixes.sparql')
        if import_paths:
            onto_path.extend(import_paths)
        try:
            self.onto = get_ontology(self.path).load()
            logger.info("successfully loaded ontology specified")
        except:
            self.onto = get_ontology(self.iri)
            self.onto.save(file = self.filename)
            logger.info("ontology file did not exist - created a new one")

    def reload_from_file(self):
        try:
            self.onto = get_ontology(self.path).load()
            logger.info("successfully reloaded ontology from file")
        except:
            logger.info("ontology file did not exist")
            sys.exit(1)

    def add_import(self, other_path):
        """load an additional onto"""
        if "file://" in other_path:
            onto_path.append(other_path.rsplit("/", 1)[0].removeprefix("file://"))
        onto_import = get_ontology(other_path).load()
        with self.onto:
            self.onto.imported_ontologies.append(onto_import)
        self.onto.save(file = self.filename)

    def save_as(self, new_name):
        """
        safe ontology as new file
        helpful, e.g., if multiple ontos were loaded
        """
        self.onto.save(file = new_name)
        self.filename = new_name
        self.path = "file://./" + new_name

    def get_elems(self):
        """
        :return: nodes and edges from onto
        """
        with self.onto:
            cl = self.onto.classes()
            ops = self.onto.object_properties()
            dps = self.onto.data_properties()
            ins = self.onto.individuals()
        return [cl, ops, dps, ins]

    def build_query(self, body):
        """
        :param body: body of the SPARQL query, without prefixes
        :return: complete SPARQL query consisting of prefixes and body
        """
        gp = self.query_prefixes
        sp = "PREFIX : <" + self.iri + "#>"
        b = body
        return gp + sp + "\n\n" + b

    def query_onto(self, query):
        """
        :param query: SPARQL query
        :return: query results as list
        # NOTE: use of query_owlready messes up ranges of dps
        """
        with self.onto:
            graph = default_world.as_rdflib_graph()
            return list(graph.query(query))

    def get_axioms(self):
        """
        :return: list of class, op, and dp axioms
        """
        axioms = []
        for body in ['class_axioms.sparql', 'op_axioms.sparql', 'dp_axioms.sparql']:
            query_ax = pkg_resources.read_text(queries, body)
            axioms.append(self.query_onto(self.build_query(query_ax)))
        return axioms

    def add_axioms(self, axiom_tuples):
        """
        :param axiom_tuples: list of tuples of the form [class, superclass, property,
        cardinality type, cardinality, object, equivalence(bool)]
        # NOTE: only one axiom may be specified at once
        # NOTE: no error handling implemented for input tuples
        # NOTE: complex axioms, i.e., intersections and unions, are currently not supported
        """
        with self.onto:
            for axiom in axiom_tuples:
                if axiom[0] and axiom[1] and not axiom[-1]:
                    my_class = types.new_class(axiom[0], (self.onto[axiom[1]], ))
                elif axiom[0] and axiom[1] and axiom[-1]:
                    my_class = types.new_class(axiom[0], (Thing, ))
                    my_class.equivalent_to.append(self.onto[axiom[1]])
                elif axiom[0] and not axiom[1]:
                    my_class = types.new_class(axiom[0], (Thing, ))
                else:
                    logger.warning(f"no class defined: {axiom}")
                if not axiom[2] and not axiom[3] and not axiom[4] and not axiom[5]:
                    continue
                if axiom[2] and axiom[3] and axiom[5]:
                    if axiom[-1]:
                        lst = my_class.equivalent_to
                    else:
                        lst = my_class.is_a
                    self.add_restr_to_class_def(lst, self.onto[axiom[2]], axiom[3],\
                                                axiom[4], self.onto[axiom[5]], axiom)
                else:
                    logger.warning(f"unexpected input: {axiom}")
        self.onto.save(file = self.filename)

    @staticmethod
    def add_restr_to_class_def(lst, prop, p_type, cardin, obj, axiom):
        """
        :param lst: list of an element's axioms - equivalent_to or is_a
        :param prop: object property
        :param p_type: property restriction type
        :param cardin: cardinality
        :param obj: object
        """
        if p_type in ["some", "only", "value"] and not cardin:
            lst.append(getattr(prop, p_type)(obj))
        elif p_type in ["exactly", "max", "min"] and cardin:
            lst.append(getattr(prop, p_type)(cardin, obj))
        else:
            logger.warning(f"unexpected cardinality definition: {axiom}")

    def add_ops(self, op_tuples):
        """
        :param op_tuples: list of tuples of the form [op, super-op, domain, range,
        functional, inverse functional, transitive, symmetric, asymmetric, reflexive,
        irreflexive, inverse_prop]
        NOTE: only one inverse_prop can be processed per tuple
        """
        with self.onto:
            for op in op_tuples:
                if op[0] and not op[1]:
                    my_op = types.new_class(op[0], (ObjectProperty, ))
                elif op[0] and op[1]:
                    my_op = types.new_class(op[0], (self.onto[op[1]], ))
                else:
                    logger.warning(f"unexpected op info: {op}")
                if op[2]:
                    my_op.domain.append(self.onto[op[2]])
                if op[3]:
                    my_op.range.append(self.onto[op[3]])
                for count, charac in enumerate(op[4:11]):
                    if charac:
                        my_op.is_a.append(self._prop_types[count])
                if op[-1]:
                    my_op.inverse_property = self.onto[op[11]]
        self.onto.save(file = self.filename)

    def add_dps(self, dp_tuples):
        """
        :param dp_tuples: list of input tuples of the form
        [dp, super-dp, functional, domain, range, min-ex, min-in, exact, max-ex, max-in]
        """
        with self.onto:
            for dp in dp_tuples:
                if dp[0] and not dp[1]:
                    my_dp = types.new_class(dp[0], (DataProperty, ))
                elif dp[0] and dp[1]:
                    my_dp = types.new_class(dp[0], (self.onto[dp[1]], ))
                else:
                    logger.warning(f"unexpected dp info: {dp}")
                    continue
                if dp[4] not in list(self._dp_range_types.keys()):
                    logger.warning(f"unexpected dp range: {dp}")
                    continue
                if dp[2]:
                    my_dp.is_a.append(FunctionalProperty)
                if dp[3]:
                    my_dp.domain.append(self.onto[dp[3]])
                if dp[4] and not any(dp[5:]):
                    my_dp.range = [self._dp_range_types[dp[4]]]
                elif dp[4] and dp[7] and not any(dp[5:7] + dp[8:]):
                    my_dp.range = [ConstrainedDatatype(self._dp_range_types[dp[4]], min_inclusive=dp[7], max_inclusive=dp[7])]
                elif dp[4] and dp[5] and dp[8] and not any(dp[6:8] + dp[9]):
                    my_dp.range = [ConstrainedDatatype(self._dp_range_types[dp[4]], min_exclusive=dp[5], max_exclusive=dp[8])]
                elif dp[4] and dp[5] and dp[9] and not any(dp[6:9]):
                    my_dp.range = [ConstrainedDatatype(self._dp_range_types[dp[4]], min_exclusive=dp[5], max_inclusive=dp[9])]
                elif dp[4] and dp[6] and dp[8] and not any(dp[5] + dp[7] + dp[9]):
                    my_dp.range = [ConstrainedDatatype(self._dp_range_types[dp[4]], min_inclusive=dp[6], max_exclusive=dp[8])]
                elif dp[4] and dp[6] and dp[9] and not any(dp[5] + dp[7:9]):
                    my_dp.range = [ConstrainedDatatype(self._dp_range_types[dp[4]], min_inclusive=dp[6], max_inclusive=dp[9])]
                elif dp[4] and dp[5] and not any(dp[6:]):
                    my_dp.range = [ConstrainedDatatype(self._dp_range_types[dp[4]], min_exclusive=dp[5])]
                elif dp[4] and dp[6] and not any(dp[5] + dp[7]):
                    my_dp.range = [ConstrainedDatatype(self._dp_range_types[dp[4]], min_inclusive=dp[6])]
                elif dp[4] and dp[8] and not any(dp[5:8] + dp[9]):
                    my_dp.range = [ConstrainedDatatype(self._dp_range_types[dp[4]], max_exclusive=dp[8])]
                elif dp[4] and dp[9] and not any(dp[5:9]):
                    my_dp.range = [ConstrainedDatatype(self._dp_range_types[dp[4]], max_inclusive=dp[9])]
                else:
                    logger.warning(f"unexpected dp range restriction: {dp}")
        self.onto.save(file = self.filename)

    def add_instances(self, instance_tuples):
        """
        :param instance_tuples: list of tuples of the form [instance, class, property, range, range-type]
        """
        with self.onto:
            for inst in instance_tuples:
                if inst[0] and inst[1]:
                    my_instance = self.onto[inst[1]](inst[0])
                else:
                    logger.warning(f"unexpected instance info: {inst}")
                if not inst[2] and not inst[3]:
                    continue
# TODO: handle datatypes correctly for DPs, depending on range of dp? - use self._dp_range_types as above
# simply add another optional element to list so that datatype may be specified
# owlready support for: int, float, bool, string, date, time, datetime, locstring (incl lang) - use dict
                if inst[2] and inst[3]:
                    if DataProperty in self.onto[inst[2]].is_a:
                        val = inst[3]
                    elif ObjectProperty in self.onto[inst[2]].is_a:
                        val = self.onto[inst[3]]
                    self.add_instance_relation(my_instance, inst[2], val)
                else:
                    logger.warning(f"unexpected triple: {inst}")
        self.onto.save(file = self.filename)

    def add_instance_relation(self, subj, pred, obj):
        if FunctionalProperty in self.onto[pred].is_a:
            setattr(subj, pred, obj)
        else:
            getattr(subj, pred).append(obj)

    def add_distinctions(self, distinct_sets):
        """
        add sets of disjoint/ different elements
        NOTE: distinctions may lead to inconsistencies reasoners cannot handle
        """
        funcs = {"classes": AllDisjoint,
                 "instances": AllDifferent}
        with self.onto:
            for ds in distinct_sets:
                try:
                    func = funcs[ds[0]]
                    func([self.onto[elem] for elem in ds[1]])
                except:
                    logger.warning(f"unknown distinction type {ds[0]}")
        self.onto.save(file = self.filename)

    def remove_elements(self, elem_list):
        """
        remove elements, all their descendents and (in case of classes) instances,
        and all references from axioms
        """
        with self.onto:
            for elem in elem_list:
                for desc in self.onto[elem].descendants():
                    if Thing in desc.ancestors():
                        for i in desc.instances():
                            destroy_entity(i)
                    if desc != self.onto[elem]:
                        destroy_entity(desc)
                destroy_entity(self.onto[elem])
        self.onto.save(file = self.filename)

    def remove_from_taxo(self, elem_list, reassign=True):
        """
        remove a class from the taxonomy, but keep all subclasses and instances
        by relating them to parent
        :param reassign: add all restrictions to subclasses via is_a
        NOTE: elem is not replaced in axioms bc this may be semantically incorrect
        """
        with self.onto:
            for elem in elem_list:
                parents = list(set(self.onto[elem].ancestors()).intersection(self.onto[elem].is_a))
                parent = [p for p in parents if not p in self._prop_types]
                if len(parent) > 1:
                    logger.warning(f"unexpected parent classes: {parents}")
                descendants = list(self.onto[elem].descendants())
                descendants.remove(self.onto[elem])
                if reassign:
                    sc_res = self.get_class_restrictions(self.onto[elem].name, "is_a")
                    eq_res = self.get_class_restrictions(self.onto[elem].name, "equivalent_to")
                for desc in descendants:
                    desc.is_a.append(parent[0])
                    if reassign:
                        desc.is_a = desc.is_a + sc_res + eq_res
                destroy_entity(self.onto[elem])
        self.onto.save(file = self.filename)

    def get_class_restrictions(self, class_name, res_type="is_a"):
        """
        :param res_type: restriction type, either is_a or equivalent_to
        """
        with self.onto:
            if res_type == "is_a":
                elems = self.onto[class_name].is_a
            elif res_type == "equivalent_to":
                elems = self.onto[class_name].equivalent_to
            else:
                logger.warning(f"unexpected res_type: {res_type}")
                sys.exit(1)
            return [x for x in elems if isinstance(x, Restriction)]

    def remove_restrictions_on_class(self, class_name):
        with self.onto:
            for lst in self.onto[class_name].is_a, self.onto[class_name].equivalent_to:
                self.remove_restr_from_class_def(lst)
        self.onto.save(file = self.filename)

    def remove_restrictions_including_prop(self, prop_name):
        with self.onto:
            for c in self.onto.classes():
                for lst in c.is_a, c.equivalent_to:
                    self.remove_restr_from_class_def(lst, self.onto[prop_name])
        self.onto.save(file = self.filename)

    @staticmethod
    def remove_restr_from_class_def(lst, prop=None):
        """
        remove all restricitons from list
        :param prop: optional; limits results to restrictions including a certain property
        """
        for r in [r for r in lst if isinstance(r, Restriction)]:
            if not prop or prop and r.property == prop:
                lst.remove(r)

    def reasoning(self, reasoner="hermit", save=False):
        """
        :param reasoner: reasoner can be eiter hermit or pellet
        :param save: bool - save inferences into original file
        :return: returns inconsistent classes, if there are any
        """
        inconsistent_classes = None
        # add temporary world for inferences
        inferences = World()
        self.check_reasoner(reasoner)
        inf_onto = inferences.get_ontology(self.path).load()
        with inf_onto:
            try:
                with redirect_to_log():
                    if reasoner == "hermit":
                        sync_reasoner_hermit([inf_onto])
                    elif reasoner == "pellet":
                        sync_reasoner_pellet([inf_onto], infer_property_values=True,\
                                             infer_data_property_values=True)
                inconsistent_classes = list(inf_onto.inconsistent_classes())
            except Exception as exc:
                print("There was a more complex issue, e.g., with disjoints - check log for traceback")
                logger.error(repr(exc) + "\n" + indent_log(traceback.format_exc()))
        if inconsistent_classes:
            logger.warning(f"the ontology is inconsistent: {inconsistent_classes}")
            inconsistent_classes.remove(Nothing)
            return inconsistent_classes
        elif save and not inconsistent_classes:
            inf_onto.save(file = self.filename)
            self.reload_from_file()
        return None

    @staticmethod
    def check_reasoner(reasoner):
        reasoners = ["hermit", "pellet"]
        if reasoner not in reasoners:
            logger.warning(f"unexpected reasoner: {reasoner} - available reasoners: {reasoners}")

    def debug_onto(self, reasoner="hermit"):
        """
        interactively (CLI) fix inconsistencies
        :param reasoner: reasoner can be eiter hermit or pellet
        """
        ax_msg = "Potentially inconsistent axiom: "
        self.check_reasoner(reasoner)
        inconsistent_classes = self.reasoning(reasoner=reasoner, save=False)
        if not inconsistent_classes:
            print("No inconsistencies detected.")
        elif inconsistent_classes:
            print(f"Inconsistent classes are: {inconsistent_classes}")
            if self.bool_user_interaction("Show further information?"):
                debug = World()
                debug_onto = debug.get_ontology(self.path).load()
                with debug_onto:
                    sync_reasoner_pellet([debug_onto], infer_property_values=True,\
                                         infer_data_property_values=True, debug=2)
                    # IDEA: further analyze reasoner results to pin down cause of inconsistency
            rel_types = ["is_a", "equivalent_to"]
            pot_probl_ax = {"is_a": self.get_incon_class_res("is_a", inconsistent_classes),
                            "equivalent_to": self.get_incon_class_res("equivalent_to", inconsistent_classes)}
            for rel in rel_types:
                for count, ic in enumerate(inconsistent_classes):
                    for ax in pot_probl_ax[rel][count]:
                        if self.bool_user_interaction("Delete " + rel + " axiom?", ax_msg + str(ax)):
                            getattr(self.onto[ic.name], rel).remove(ax)
                            # IDEA: instead of simply deleting axioms, also allow user to edit them
            self.onto.save(file = self.filename)
            self.debug_onto(reasoner)

    def get_incon_class_res(self, rel, inconsistent_classes):
        """
        :return: class restrictions for inconsistent_classes - does not return parent classes
        """
        return [self.get_class_restrictions(ic.name, rel) for ic in inconsistent_classes]

    @staticmethod
    def bool_user_interaction(question, info=None):
        """simple CLI for yes/ no/ quit interaction"""
        answer = {"y": True,
                  "n": False}
        if info:
            print(info)
        print(question + " [y(es), n(o), q(uit)]")
        user_input = input()
        while user_input not in ["y", "n", "q"]:
            print("invalid choice, please try again")
            user_input = input()
        if user_input in ["y", "n"]:
            return answer[user_input]
        if user_input == "q":
            print("quitting - process needs to be restarted")
            sys.exit(0)
