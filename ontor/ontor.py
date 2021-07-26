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
import networkx as nx
import os
import pandas as pd
import sys
import textwrap
import traceback

from contextlib import contextmanager
from io import StringIO
from owlready2 import default_world, destroy_entity, get_ontology, onto_path, types,\
                      sync_reasoner_hermit, sync_reasoner_pellet, Thing, Nothing,\
                      AllDisjoint, AllDifferent, DataProperty, ObjectProperty,\
                      World, Restriction, ConstrainedDatatype,\
                      FunctionalProperty, InverseFunctionalProperty,\
                      TransitiveProperty, SymmetricProperty, AsymmetricProperty,\
                      ReflexiveProperty, IrreflexiveProperty, ThingClass
from pyvis.network import Network

import queries

logger = logging.getLogger(__name__)
timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
logging.basicConfig(filename=timestamp+"_om.log", level=logging.DEBUG)

@contextmanager
def _redirect_to_log():
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
                logger.info(f"reasoner output redirect: \n{_indent_log(result_out.getvalue())}")
            if result_err.getvalue():
                logger.info(f"reasoner errors redirect: \n{_indent_log(result_err.getvalue())}")

def _indent_log(info):
    return textwrap.indent(info, '>   ')

def load_csv(csv_file: str, load_first_line: bool=False) -> list:
    """ load data from CSV file

    :param csv_file: input CSV file
    :param load_first_line: indicates whether content from first row is also returned
    :return: CSV contents as list of lists
    """
    with open(csv_file) as f:
        if load_first_line:
            data = list(csv.reader(f))
        else:
            data = list(csv.reader(f))[1:]
    return data

def load_json(json_file: str) -> dict:
    """ load data from JSON file

    :param json_file: input JSON file
    :return: JSON contents as dictionary
    """
    with open(json_file) as f:
        data = json.load(f)
    return data

class OntoEditor:
    """create, load, and edit ontologies"""

    # NOTE: _prop_types corresponds to owlready2.prop._TYPE_PROPS; defined here to ensure order
    _prop_types = [FunctionalProperty, InverseFunctionalProperty, TransitiveProperty,\
                   SymmetricProperty, AsymmetricProperty, ReflexiveProperty, IrreflexiveProperty]
    _dp_range_types = {"boolean": bool,
                       "float": float,
                       "integer": int,
                       "string": str,
                       "date": datetime.date,
                       "time": datetime.time,
                       "datetime": datetime.datetime}

    def __init__(self, iri: str, path: str, import_paths: list=None):
        """ tries to load onto from file specified, creates new file if none is available

        :param iri: ontology's IRI
        :param path: path to local ontology file or URL; local is checked first
        :param import_paths: list of local directories to be checked for imports
        """
        self.iri = iri
        self.path = path
        self.filename = path.split(sep="/")[-1]
        self.query_prefixes = pkg_resources.read_text(queries, 'prefixes.sparql')
        onto_path.extend(list(set(path.rsplit("/", 1)[0]) - set(onto_path)))
        if import_paths:
            onto_path.extend(list(set(import_paths) - set(onto_path)))
        try:
            self.onto = get_ontology(self.path).load()
            logger.info("successfully loaded ontology specified")
        except:
            self.onto = get_ontology(self.iri)
            self.onto.save(file = self.filename)
            logger.info("ontology file did not exist - created a new one")

    def _reload_from_file(self) -> None:
        try:
            self.onto = get_ontology(self.path).load()
            logger.info("successfully reloaded ontology from file")
        except:
            logger.info("ontology file did not exist")
            sys.exit(1)

    def add_import(self, other_path: str) -> None:
        """load an additional onto"""
        if "file://" in other_path:
            onto_path.extend(list(set(other_path.rsplit("/", 1)[0].\
                             removeprefix("file://")) - set(onto_path)))
        onto_import = get_ontology(other_path).load()
        with self.onto:
            self.onto.imported_ontologies.append(onto_import)
        self.onto.save(file = self.filename)

    def save_as(self, new_name: str) -> None:
        """ safe ontology as new file
        helpful, e.g., if multiple ontos were loaded
        """
        self.onto.save(file = new_name)
        self.filename = new_name
        self.path = "file://./" + new_name

    def export_ntriples(self) -> None:
        """saves with same filename, but as ntriples"""
        ntfilename = self.filename.rsplit(".", 1)[0] + ".nt"
        self.onto.save(file = ntfilename, format = "ntriples")

    def get_elems(self) -> list:
        """ get classes, object properties, datatype properties, and intances

        :return: nodes and edges from onto
        """
        with self.onto:
            cl = self.onto.classes()
            ops = self.onto.object_properties()
            dps = self.onto.data_properties()
            ins = self.onto.individuals()
        return [cl, ops, dps, ins]

    def _build_query(self, body: str) -> str:
        """ use default prefixes to construct entire SPARQL query

        :param body: body of the SPARQL query, without prefixes
        :return: complete SPARQL query consisting of prefixes and body
        """
        gp = self.query_prefixes
        sp = "PREFIX : <" + self.iri + "#>"
        b = body
        return gp + sp + "\n\n" + b

    def query_onto(self, query: str) -> list:
        """ query onto using SPARQL
        NOTE: use of query_owlready messes up ranges of dps

        :param query: SPARQL query
        :return: query results as list
        """
        with self.onto:
            graph = default_world.as_rdflib_graph()
            return list(graph.query(query))

    def get_axioms(self) -> list:
        """
        :return: list of class, op, and dp axioms
        """
        axioms = []
        for body in ['class_axioms.sparql', 'op_axioms.sparql', 'dp_axioms.sparql']:
            query_ax = pkg_resources.read_text(queries, body)
            axioms.append(self.query_onto(self._build_query(query_ax)))
        return axioms

    def add_axioms(self, axiom_tuples: list) -> None:
        """ add entire axioms to onto
        NOTE: only one axiom may be specified at once
        NOTE: no error handling implemented for input tuples
        NOTE: complex axioms, i.e., intersections and unions, are currently not supported

        :param axiom_tuples: list of tuples of the form [class, superclass, property,
            cardinality type, cardinality, op-object, dp-range, dp-min-ex, dp-min-in,
            dp-exact, dp-max-in, dp-max-ex, equivalence(bool)]
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
                if all([axiom[i] for i in [2,3,5]]) or all([axiom[i] for i in [2,3,6]]):
                    if axiom[-1]:
                        current_axioms = my_class.equivalent_to
                    else:
                        current_axioms = my_class.is_a
                    self._add_restr_to_def(current_axioms, [self.onto[axiom[2]],\
                                           axiom[3], axiom[4]], [self.onto[axiom[5]]],\
                                           axiom[6:12], axiom)
                else:
                    logger.warning(f"unexpected input: {axiom}")
        self.onto.save(file = self.filename)

    def _add_restr_to_def(self, current_axioms: list, resinfo: list, opinfo: list, dpinfo: list, axiom: list) -> None:
        """
        :param current_axioms: list of an element's current axioms - equivalent_to or is_a
        :param resinfo: list with general restriction info [prop, p_type, cardin]
        :param opinfo: list with op restriction info [op-object]
        :param dpinfo: list with dp restriction info [dprange, minex, minin,
            exact, maxin, maxex]
        :param axiom: list with complete axiom info
        """
        if any(opinfo) and not any(dpinfo):
            obj = opinfo[0]
        elif not any(opinfo) and any(dpinfo):
            obj = None
            if resinfo[1] in ["some", "only"]:
                obj = self._dp_constraint(dpinfo)
            elif resinfo[1] in ["value"] and dpinfo[3]:
                obj = self._dp_range_types[dpinfo[0]](dpinfo[3])
            if obj is None:
                logger.warning(f"invalid dp constraint: {axiom}")
                return
            if resinfo[1] in ["exactly", "max", "min"]:
                # NOTE: this may be resolved in future versions of Owlready2
                logger.warning(f"qualified cardinality restrictions currently not supported for DPs: {axiom}")
                return
        else:
            logger.warning(f"restriction includes both op and dp: {axiom}")
            return
        if resinfo[1] in ["some", "only", "value"] and not resinfo[2]:
            current_axioms.append(getattr(resinfo[0], resinfo[1])(obj))
        elif resinfo[1] in ["exactly", "max", "min"] and resinfo[2]:
            current_axioms.append(getattr(resinfo[0], resinfo[1])(resinfo[2], obj))
        else:
            logger.warning(f"unexpected cardinality definition: {axiom}")

    def _dp_constraint(self, dpres: list):
        """
        :param dpres: DP restriction is list of the form [dprange, minex, minin,
            exact, maxin, maxex]
        :return: constrained datatype for DP, set to None if invalid
        """
        dp_range = None
        if dpres[0] not in list(self._dp_range_types.keys()):
            logger.warning(f"unexpected dp range: {dpres}")
        if self._check_available_vals(dpres, [0]):
            dp_range = self._dp_range_types[dpres[0]]
        elif self._check_available_vals(dpres, [0,3]):
            dp_range = ConstrainedDatatype(self._dp_range_types[dpres[0]],\
                                           min_inclusive=dpres[3],\
                                           max_inclusive=dpres[3])
        elif self._check_available_vals(dpres, [0,1,4]):
            dp_range = ConstrainedDatatype(self._dp_range_types[dpres[0]],\
                                           min_exclusive=dpres[1],\
                                           max_inclusive=dpres[4])
        elif self._check_available_vals(dpres, [0,1,5]):
            dp_range = ConstrainedDatatype(self._dp_range_types[dpres[0]],\
                                           min_exclusive=dpres[1],\
                                           max_exclusive=dpres[5])
        elif self._check_available_vals(dpres, [0,2,4]):
            dp_range = ConstrainedDatatype(self._dp_range_types[dpres[0]],\
                                           min_inclusive=dpres[2],\
                                           max_inclusive=dpres[4])
        elif self._check_available_vals(dpres, [0,2,5]):
            dp_range = ConstrainedDatatype(self._dp_range_types[dpres[0]],\
                                           min_inclusive=dpres[2],\
                                           max_exclusive=dpres[5])
        elif self._check_available_vals(dpres, [0,1]):
            dp_range = ConstrainedDatatype(self._dp_range_types[dpres[0]],\
                                           min_exclusive=dpres[1])
        elif self._check_available_vals(dpres, [0,2]):
            dp_range = ConstrainedDatatype(self._dp_range_types[dpres[0]],\
                                           min_inclusive=dpres[2])
        elif self._check_available_vals(dpres, [0,4]):
            dp_range = ConstrainedDatatype(self._dp_range_types[dpres[0]],\
                                           max_inclusive=dpres[4])
        elif self._check_available_vals(dpres, [0,5]):
            dp_range = ConstrainedDatatype(self._dp_range_types[dpres[0]],\
                                           max_exclusive=dpres[5])
        else:
            logger.warning(f"unexpected dp range restriction: {dpres}")
        return dp_range

    @staticmethod
    def _check_available_vals(values: list, expected_values: list) -> bool:
        """
        :param values: list with values
        :param expected_values: list with indices of expected values
        :return: True iff expected indices contain values
        """
        indices = [x for x, _ in enumerate(values)]
        assert all([x in indices for x in expected_values]), "invalid expected_values"
        if all([values[i] for i in expected_values]) and\
           not any([values[i] for i in [e for e in indices if not e in expected_values]]):
            return True
        else:
            return False

    def add_ops(self, op_tuples: list) -> None:
        """ add object properties including their axioms to onto
        NOTE: only one inverse_prop can be processed per tuple

        :param op_tuples: list of tuples of the form [op, super-op, domain, range,
            functional, inverse functional, transitive, symmetric,
            asymmetric, reflexive, irreflexive, inverse_prop]
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

    def add_dps(self, dp_tuples: list) -> None:
        """ add datatype properties including their axioms to onto

        :param dp_tuples: list of input tuples of the form [dp, super-dp, functional,
            domain, range, minex, minin, exact, maxin, maxex]
        """
        with self.onto:
            for dp in dp_tuples:
                try:
                    if dp[0] and not dp[1]:
                        my_dp = types.new_class(dp[0], (DataProperty, ))
                    elif dp[0] and dp[1]:
                        my_dp = types.new_class(dp[0], (self.onto[dp[1]], ))
                except:
                    logger.warning(f"unexpected dp info: {dp}")
                    continue
                if dp[2]:
                    my_dp.is_a.append(FunctionalProperty)
                if dp[3]:
                    try:
                        my_dp.domain.append(self.onto[dp[3]])
                    except:
                        logger.warning(f"unexpected dp domain: {dp}")
                if any(dp[4:]):
                    dprange = self._dp_constraint(dp[4:])
                    if dprange:
                        my_dp.range = dprange
                    else:
                        logger.warning(f"unexpected dp range: {dp}")
                        continue
        self.onto.save(file = self.filename)

    def add_instances(self, instance_tuples: list) -> None:
        """
        :param instance_tuples: list of tuples of the form [instance, class,
            property, range, range-type]
        """
        with self.onto:
            for inst in instance_tuples:
                if inst[0] and inst[1]:
                    my_instance = self.onto[inst[1]](inst[0])
                else:
                    logger.warning(f"unexpected instance info: {inst}")
                if not any(inst[2:]):
                    continue
                if inst[2] and inst[3]:
                    if DataProperty in self.onto[inst[2]].is_a:
                        if inst[4] and not inst[4] in self._dp_range_types:
                            logger.warning(f"unexpected DP range: {inst}")
                        elif inst[4]:
                            val = self._dp_range_types[inst[4]](inst[3])
                        else:
                            logger.warning(f"DP range undefined - defaulting to string: {inst}")
                            val = inst[3]
                    elif ObjectProperty in self.onto[inst[2]].is_a and not inst[4]:
                        val = self.onto[inst[3]]
                    self.add_instance_relation(my_instance, inst[2], val)
                else:
                    logger.warning(f"unexpected triple: {inst}")
        self.onto.save(file = self.filename)

    def add_instance_relation(self, subj, pred, obj) -> None:
        if FunctionalProperty in self.onto[pred].is_a:
            setattr(subj, pred, obj)
        else:
            getattr(subj, pred).append(obj)

    def add_distinctions(self, distinct_sets: list) -> None:
        """ make classes disjoint and instances distinct
        NOTE: distinctions may lead to inconsistencies reasoners cannot handle

        :param distinct_sets: list of lists with disjoint/ different elements
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

    def remove_elements(self, elem_list: list) -> None:
        """ remove elements, all their descendents and (in case of classes) instances,
        and all references from axioms

        :param elem_list: list of elements to be removed from onto
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

    def remove_from_taxo(self, elem_list: list, reassign: bool=True) -> None:
        """ remove a class from the taxonomy, but keep all subclasses and instances
        by relating them to parent
        NOTE: elem is not replaced in axioms bc this may be semantically incorrect

        :param elem_list: list of elements to be removed from onto
        :param reassign: add all restrictions to subclasses via is_a
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

    def get_class_restrictions(self, class_name: str, res_type="is_a") -> list:
        """ retrieve restrictions on specific class by restriction type

        :param class_name: name of the class for which restrictions shall be returned
        :param res_type: restriction type, either is_a or equivalent_to
        :return: list of restrictions on class
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

    def remove_restrictions_on_class(self, class_name: str) -> None:
        with self.onto:
            for lst in self.onto[class_name].is_a, self.onto[class_name].equivalent_to:
                self._remove_restr_from_class_def(lst)
        self.onto.save(file = self.filename)

    def remove_restrictions_including_prop(self, prop_name: str) -> None:
        with self.onto:
            for c in self.onto.classes():
                for lst in c.is_a, c.equivalent_to:
                    self._remove_restr_from_class_def(lst, self.onto[prop_name])
        self.onto.save(file = self.filename)

    @staticmethod
    def _remove_restr_from_class_def(cls_restrictions, prop=None) -> None:
        """ remove all restrictions from list

        :param cls_restrictions: restrictions on a class, either is_a or equivalent_to
        :param prop: optional; limits results to restrictions including a certain property
        """
        for r in [r for r in cls_restrictions if isinstance(r, Restriction)]:
            if not prop or prop and r.property == prop:
                cls_restrictions.remove(r)

    def reasoning(self, reasoner: str="hermit", save: bool=False):
        """
        :param reasoner: reasoner can be eiter hermit or pellet
        :param save: bool - save inferences into original file
        :return: returns list of inconsistent classes, if there are any
        """
        inconsistent_classes = None
        # add temporary world for inferences
        inferences = World()
        self._check_reasoner(reasoner)
        inf_onto = inferences.get_ontology(self.path).load()
        with inf_onto:
            try:
                with _redirect_to_log():
                    if reasoner == "hermit":
                        sync_reasoner_hermit([inf_onto])
                    elif reasoner == "pellet":
                        sync_reasoner_pellet([inf_onto], infer_property_values=True,\
                                             infer_data_property_values=True)
                inconsistent_classes = list(inf_onto.inconsistent_classes())
            except Exception as exc:
                print("There was a more complex issue, e.g., with disjoints - check log for traceback")
                logger.error(repr(exc) + "\n" + _indent_log(traceback.format_exc()))
        if inconsistent_classes:
            logger.warning(f"the ontology is inconsistent: {inconsistent_classes}")
            inconsistent_classes.remove(Nothing)
            return inconsistent_classes
        if save and not inconsistent_classes:
            inf_onto.save(file = self.filename)
            self._reload_from_file()
        return None

    @staticmethod
    def _check_reasoner(reasoner: str) -> None:
        reasoners = ["hermit", "pellet"]
        if reasoner not in reasoners:
            logger.warning(f"unexpected reasoner: {reasoner} - available reasoners: {reasoners}")

    def debug_onto(self, reasoner: str="hermit", assume_correct_taxo: bool=True) -> None:
        """ interactively (CLI) fix inconsistencies

        :param assume_correct_taxo: if True, the user interactions will be limited
            to restrictions, i.e., options to delete taxonomical relations are
            not included, e.g., A rdfs:subClassOf B
        :param reasoner: reasoner to be used for inferences
        """
        ax_msg = "Potentially inconsistent axiom: "
        self._check_reasoner(reasoner)
        inconsistent_classes = self.reasoning(reasoner=reasoner, save=False)
        if not inconsistent_classes:
            print("No inconsistencies detected.")
        elif inconsistent_classes:
            print(f"Inconsistent classes are: {inconsistent_classes}")
            if self._bool_user_interaction("Show further information?"):
                debug = World()
                debug_onto = debug.get_ontology(self.path).load()
                with debug_onto:
                    sync_reasoner_pellet([debug_onto], infer_property_values=True,\
                                         infer_data_property_values=True, debug=2)
                    # IDEA: further analyze reasoner results to pin down cause of inconsistency
            rel_types = ["is_a", "equivalent_to"]
            if assume_correct_taxo:
                pot_probl_ax = {"is_a": self._get_incon_class_res("is_a", inconsistent_classes),
                                "equivalent_to": self._get_incon_class_res("equivalent_to", inconsistent_classes)}
            else:
                pot_probl_ax = {"is_a": [self.onto[ic.name].is_a for ic in inconsistent_classes],
                                "equivalent_to": [self.onto[ic.name].equivalent_to for ic in inconsistent_classes]}
            for rel in rel_types:
                for count, ic in enumerate(inconsistent_classes):
                    for ax in pot_probl_ax[rel][count]:
                        if self._bool_user_interaction("Delete " + rel + " axiom?",\
                                                       ax_msg + ic.name + " " + rel + " " + str(ax)):
                            if type(ax) == ThingClass:
                                getattr(self.onto[ic.name], rel).remove(self.onto[ax.name])
                            else:
                                getattr(self.onto[ic.name], rel).remove(ax)
                            # IDEA: instead of simply deleting axioms, also allow user to edit them
            self.onto.save(file = self.filename)
            self.debug_onto(reasoner, assume_correct_taxo)

    def _get_incon_class_res(self, restype: str, inconsistent_classes: list) -> list:
        """
        :param restype: type of class restriction, either is_a or equivalent_to
        :return: list of class restrictions for inconsistent_classes - does not return parent classes
        """
        return [self.get_class_restrictions(ic.name, restype) for ic in inconsistent_classes]

    @staticmethod
    def _bool_user_interaction(question: str, info: str=None) -> str:
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

    @staticmethod
    def _remove_nt_brackets(triple: list) -> list:
        for c, _ in enumerate(triple):
            triple[c] = triple[c].replace('<', '')
            triple[c] = triple[c].replace('>', '')
        return triple

    @staticmethod
    def _df_to_nx_incl_labels(df: pd.DataFrame) -> nx.MultiDiGraph:
        nxgraph = nx.from_pandas_edgelist(df, source="subject", target="object",\
                                          edge_attr="predicate", create_using=nx.MultiDiGraph())
        # manually set predicates as labels
        for e in nxgraph.edges.items():
            e[1]["label"] = e[1].pop("predicate")
        return nxgraph

    def _ntriples_to_nx(self) -> nx.MultiDiGraph:
        self.export_ntriples()
        f = open(self.filename.rsplit(".", 1)[0] + ".nt", "r")
        lines = f.readlines()
        df = pd.DataFrame(columns=["subject", "predicate", "object"])
        for rownum, row in enumerate(lines):
            df.loc[rownum] = self._remove_nt_brackets(row.rsplit(".", 1)[0].split(" ")[:3])
        return self._df_to_nx_incl_labels(df)

    def _query_results_to_nx(self, query_results: list) -> nx.MultiDiGraph:
        clean_data = [[str(elem).split("#")[-1] for elem in row] for row in query_results]
        df = pd.DataFrame(clean_data, columns=['subject', 'predicate', 'object'])
        return self._df_to_nx_incl_labels(df)

    def _plot_nxgraph(self, nxgraph: nx.MultiDiGraph, interactive: bool=False) -> None:
        """
        :param nxgraph: networkx graph including the ontology's triples
        :param interactive: activates mode for changing network appearance
        :return: html file for the network's plot
        """
        net = Network(directed=True, height='100%', width='100%', bgcolor='#222222', font_color='white')
        net.set_options("""
            var options = {
                "nodes": {
                    "font": {
                    "color": "rgba(52,52,52,1)"
                    }
                },
                "edges": {
                    "color": {
                    "inherit": true
                    },
                    "font": {
                    "color": "rgba(158,158,158,1)",
                    "strokeWidth": 0
                    },
                    "smooth": false
                },
                "physics": {
                    "minVelocity": 0.75
                }
            }
        """)
        net.from_nx(nxgraph)
        if interactive:
            net.show_buttons()
        net.show(self.filename.rsplit(".", 1)[0] + ".html")

    def _config_plot_query_body(self, classes: list=[], properties: list=[], focusnode: str=None, radius: int=None) -> str:
        """
        :param classes: classes to be returned including their instances
        :param properties: properties to be returned
        :param focusnode: node whose environment shall be displayed
        :param radius: maximum distance, i.e., relations, between a node and focusnode
        :return: body for query
        """
        def _sparql_set_values(node, values):
            return "VALUES ?" + node + " {rdf:type rdfs:subClassOf " + " ".join([":" + v for v in values]) + "} . "
        def _sparql_set_in(node, values):
            return "FILTER ( ?" + node + " IN (" + ", ".join([":" + v for v in values]) + ") ) . "
        querypt1 = ("SELECT DISTINCT ?s ?p ?o WHERE {\n"
                    "?s ?p ?o . ")
        querypt2 = "}"
        if properties:
            querypt_rels = _sparql_set_values("p", properties)
        else:
            querypt_rels = ""
        query_nodes_dict: dict={}
        if classes:
            for node in ["s", "o"]:
                querypt_classes = "?s ?p ?o . \n" + _sparql_set_in(node, classes)
                querypt_instances = "?" + node + " a/rdfs:subClassOf* ?" + node +\
                                    "class . \n" + _sparql_set_in(node+"class", classes)
                query_nodes_dict[node] = "{\n" + querypt_classes + "\n} UNION {\n" +\
                                        querypt_instances + "\n}"
            querypt_nodes = "\n".join(query_nodes_dict.values())
        else:
            querypt_nodes = ""
        query_rel_lim = ""
        if focusnode and radius:
            assert radius <= 23, "max radius violated"
            if properties:
                rels = properties
            else:
                rels = self.onto.properties()
            query_rel_lim = ":" + focusnode + " " + "?/".join(["(rdf:type|rdfs:subClassOf|:" + "|:".join(rels) + ")"]*radius) + "? ?o . "
        elif focusnode and not radius or not focusnode and radius:
            logger.warning("focus: both a focusnode and a radius must be specified - ignoring the focus")
        return "\n".join([querypt1, querypt_rels, querypt_nodes, query_rel_lim, querypt2])

    def visualize(self, classes: list=[], properties: list=[], focusnode: str=None, radius: int=None) -> None:
        """ visualize onto as a graph; generates html

        :param classes: list of classes to be included in plot
        :param properties: list of properties to be included in plot
        :param radius: maximum number of relations between a node and a node of one of the classes specified
        :return: None
        """
        if not classes and not properties and not focusnode and not radius:
            nxgraph = self._ntriples_to_nx()
        else:
            query_results = self.query_onto(self._build_query(self._config_plot_query_body(classes, properties, focusnode, radius)))
            nxgraph = self._query_results_to_nx(query_results)
        self._plot_nxgraph(nxgraph)
