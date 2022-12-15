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
import random
import re
import string
import sys
import textwrap
import traceback
import typing
from contextlib import contextmanager
from io import StringIO

import networkx as nx
import pandas as pd
from owlready2 import (
    destroy_entity,
    get_ontology,
    onto_path,
    types,
    sync_reasoner_hermit,
    sync_reasoner_pellet,
    Thing,
    Nothing,
    AllDisjoint,
    AllDifferent,
    DataProperty,
    ObjectProperty,
    World,
    Restriction,
    ConstrainedDatatype,
    FunctionalProperty,
    InverseFunctionalProperty,
    TransitiveProperty,
    SymmetricProperty,
    AsymmetricProperty,
    ReflexiveProperty,
    IrreflexiveProperty,
    ThingClass,
    Not,
    Inverse,
    base,
    locstr,
    And,
    Or,
    ClassConstruct,
)
from pyvis.network import Network

from . import config
from . import queries


LOGFILE = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + "_ontor.log"
logging.basicConfig(filename=LOGFILE, level=logging.DEBUG)


def load_csv(csv_file: str, load_first_line: bool = False) -> list:
    """load data from CSV file

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


def load_json(json_file: str) -> typing.Union[dict, list]:
    """load data from JSON file

    :param json_file: input JSON file
    :return: JSON contents as dictionary
    """
    with open(json_file) as f:
        data = json.load(f)
    return data


def cleanup(complete: bool, *extensions: str) -> None:
    """delete all files in the current directory with the extensions specified

    :param extensions: extensions of files to be deleted
    :param complete: do not delete current log file if set to False
    """
    this_dir = "./"
    for e in extensions:
        files = [f for f in os.listdir(this_dir) if f.endswith("." + e)]
        if not complete and LOGFILE in files:
            files.remove(LOGFILE)
        for f in files:
            os.remove(os.path.join(this_dir, f))


class InfoException(Exception):
    """exception for invalid ontor inputs"""

    def __init__(self, **kwargs: str):
        Exception.__init__(self)
        self.info = kwargs


class OntoEditor:
    """create, load, and edit ontologies"""

    # NOTE: _prop_types corresponds to owlready2.prop._TYPE_PROPS; defined here to ensure order
    _prop_types = [
        FunctionalProperty,
        InverseFunctionalProperty,
        TransitiveProperty,
        SymmetricProperty,
        AsymmetricProperty,
        ReflexiveProperty,
        IrreflexiveProperty,
    ]
    _dp_range_types = {
        "boolean": bool,
        "float": float,
        "integer": int,
        "string": str,
        "date": datetime.date,
        "time": datetime.time,
        "datetime": datetime.datetime,
    }

    def __init__(self, iri: str, path: str, import_paths: list = None) -> None:
        """tries to load onto from file specified, creates new file if none is available

        :param iri: ontology's IRI
        :param path: path to local ontology file or URL; local is checked first
        :param import_paths: list of local directories to be checked for imports
        """
        self.iri = iri
        self.path = path
        self.filename = path.split(sep="/")[-1]
        self.logger = logging.getLogger(self.filename.split(".")[0])
        self.query_prefixes = pkg_resources.read_text(queries, "prefixes.sparql")
        onto_path.extend(list({path.rsplit("/", 1)[0]} - set(onto_path)))
        if import_paths:
            onto_path.extend(list(set(import_paths) - set(onto_path)))
        self.onto_world = World()
        try:
            self.onto = self.onto_world.get_ontology(self.path).load()
            self.logger.info("successfully loaded ontology specified")
        except FileNotFoundError:
            self.onto = self.onto_world.get_ontology(self.iri)
            self.onto.save(file=self.path)
            self.logger.info("ontology file did not exist - created a new one")

    @contextmanager
    def _redirect_to_log(self) -> typing.Iterator[None]:
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
                    self.logger.info(
                        f"reasoner output redirect: \n{self._indent_log(result_out.getvalue())}"
                    )
                if result_err.getvalue():
                    self.logger.info(
                        f"reasoner errors redirect: \n{self._indent_log(result_err.getvalue())}"
                    )

    @staticmethod
    def _indent_log(info: str) -> str:
        return textwrap.indent(info, ">   ")

    def _reload_from_file(self) -> None:
        try:
            self.onto_world = World()
            self.onto = self.onto_world.get_ontology(self.path).load()
            self.logger.info("successfully reloaded ontology from file")
        except FileNotFoundError:
            self.logger.error("ontology file did not exist")
            sys.exit(1)

    def _transform_to_dp_type(self, data_type: str, val):
        if data_type != "boolean":
            return self._dp_range_types[data_type](val)
        elif str(val).lower() == "false":
            return False
        elif str(val).lower() == "true":
            return True

    def add_import(self, other_path: str) -> None:
        """load an additional onto

        :param other_path: path to file of onto to be imported
        """
        if "file://" in other_path:
            onto_path.extend(
                list(
                    set(other_path.rsplit("/", 1)[0].removeprefix("file://"))
                    - set(onto_path)
                )
            )
        onto_import = get_ontology(other_path).load()
        with self.onto:
            self.onto.imported_ontologies.append(onto_import)
        self.onto.save(file=self.path)

    def save_as(self, new_path: str) -> None:
        """safe ontology as new file
        helpful, e.g., if multiple ontos were loaded

        :param new_path: path including filename for saving the onto
        """
        self.onto.save(file=new_path)
        self.path = new_path
        self.filename = new_path.rsplit("/", 1)[1]

    def export_ntriples(self) -> None:
        """saves with same filename, but as ntriples"""
        ntpath = self.path.rsplit(".", 1)[0] + ".nt"
        self.onto.save(file=ntpath, format="ntriples")

    def get_elems(self) -> list:
        """get classes, object properties, datatype properties, and instances

        :return: nodes and edges from onto
        """
        with self.onto:
            cl = self.onto.classes()
            ops = self.onto.object_properties()
            dps = self.onto.data_properties()
            ins = self.onto.individuals()
        return [cl, ops, dps, ins]

    def _build_query(self, body: str) -> str:
        """use default prefixes to construct entire SPARQL query

        :param body: body of the SPARQL query, without prefixes
        :return: complete SPARQL query consisting of prefixes and body
        """
        gp = self.query_prefixes
        sp = "PREFIX : <" + self.iri + "#>"
        b = body
        return gp + sp + "\n\n" + b

    def query_onto(self, query: str) -> list:
        """query onto using SPARQL
        NOTE: use of query_owlready messes up ranges of dps

        :param query: SPARQL query
        :return: query results as list
        """
        with self.onto:
            graph = self.onto_world.as_rdflib_graph()
        return list(graph.query(query))

    def get_axioms(self) -> list:
        """identify all axioms included in the onto

        :return: list of class, op, and dp axioms
        """
        axioms = []
        for body in ["class_axioms.sparql", "op_axioms.sparql", "dp_axioms.sparql"]:
            query_ax = pkg_resources.read_text(queries, body)
            axioms.append(self.query_onto(self._build_query(query_ax)))
        return axioms

    def _create_notion(self, name, parent, elem_type) -> type:
        """load a notion from the ontology or create a new one if not yet available
        works for classes, object properties, and data properties

        :param name: name of the notion
        :param parent: name of the parent notion
        :param elem_type: indicates class, op, or dp
        :return: notion
        """
        type_dict = {
            "c": Thing,
            "o": ObjectProperty,
            "d": DataProperty,
        }
        with self.onto:
            if name and not parent:
                notion = types.new_class(name, (type_dict[elem_type],))
            elif name and parent and elem_type != "c":
                notion = types.new_class(name, (self.onto[parent], type_dict[elem_type],))
            elif name and parent and elem_type == "c":
                notion = types.new_class(name, (self.onto[parent],))
            else:
                self.logger.warning(f"unexpected info: {name, parent, elem_type}")
                raise InfoException
        return notion

    def add_taxo(self, class_tuples: list) -> None:
        """add taxonomy to onto

        :param class_tuples: list of 2-tuples of the form [class, superclass]
        """
        with self.onto:
            for clst in class_tuples:
                try:
                    my_class = self._create_notion(clst[0], clst[1], "c")
                except (TypeError, InfoException):
                    self.logger.warning(f"unexpected class info: {clst}")
                    continue
        self.onto.save(file=self.path)

    @staticmethod
    def class_dict_to_tuple_list(cls_dict: dict) -> list:
        """helper function to convert dict with class definitions to list of
        tuples as required by add_taxo function

        :param cls_dict: dictionary for taxonomy definition of the form
            {superclass: [subclasses]}
        :return: list of class definition 2-tuples of the form [[subclass, superclass], ...]
        """
        return [
            [subcls, supercls]
            for supercls in cls_dict.keys()
            for subcls in cls_dict[supercls]
        ]

    def _combine_axioms(self, axs: dict) -> tuple:
        """define complex axioms, i.e., elementary axioms that are logically combined

        :param axs: input for axioms, either simple list or of the form {"or": [ax1, "and": [ax2, ax3]]}
        :return: combined restriction, restriction type (equivalence or subclass), and class
        """
        res, comb, cls = [], None, None
        res_type_set, res_type = False, None
        res_type_vals = {
            None: False,
            False: False,
            True: True,
        }
        assert len(axs.keys()) == 1, f"more than one operator defined for axiom: {axs}"
        operator = list(axs.keys())[0]
        assert operator in [
            "and",
            "or",
        ], f"invalid key for axiom combination: {operator}"
        for axiom in axs[operator]:
            if isinstance(axiom, list):
                if not res_type_set:
                    res_type_set, res_type = True, res_type_vals[axiom[-1]]
                else:
                    assert (
                        res_type_vals[axiom[-1]] == res_type
                    ), f"restriction types (subsumption vs equivalence) do not match: {axs}"
                if not cls:
                    cls = axiom[0]
                else:
                    assert (
                        axiom[0] == cls
                    ), f"aggregated restriction does not always refer to same class: {axs}"
                res.append(
                    self._tuple_to_res(
                        axiom[1],
                        [self.onto[axiom[2]], axiom[3], axiom[4], axiom[5], axiom[13]],
                        [self.onto[axiom[6]]],
                        axiom[7:13],
                        axiom,
                    )
                )
            elif isinstance(axiom, dict):
                res.append(self._combine_axioms(axiom)[0])
        if operator == "and":
            comb = And(res)
        elif operator == "or":
            comb = Or(res)
        return comb, res_type, cls

    def add_axioms(self, axioms: list) -> None:
        """add entire axioms to onto
        NOTE: only one axiom may be specified at once
        NOTE: no error handling implemented for input tuples

        :param axioms: list of tuples of the form [class, superclass, property,
            inverted(bool), cardinality type, cardinality, op-object, dp-range,
            dp-min-ex, dp-min-in, dp-exact, dp-max-in, dp-max-ex, negated(bool),
            equivalence(bool)]
            may also include dicts containing aggregate axioms of the form {"or": [ax1, "and": [ax2, ax3]]}
        """
        with self.onto:
            for axiom in axioms:
                if isinstance(axiom, list):
                    my_class = self.onto[axiom[0]]
                    if not any(axiom[i] for i in [1, 2, 4, 5, 6]) and not axiom[5] == 0:
                        continue
                    if (
                        all(axiom[i] is not None for i in [0, 1, -1])
                        or all(axiom[i] for i in [2, 4, 6])
                        or all(axiom[i] for i in [2, 4, 7])
                    ):
                        if axiom[-1]:
                            current_axioms = my_class.equivalent_to
                        else:
                            current_axioms = my_class.is_a
                        res = self._tuple_to_res(
                            axiom[1],
                            [
                                self.onto[axiom[2]],
                                axiom[3],
                                axiom[4],
                                axiom[5],
                                axiom[13],
                            ],
                            [self.onto[axiom[6]]],
                            axiom[7:13],
                            axiom,
                        )
                        if res:
                            current_axioms.append(res)
                    else:
                        self.logger.warning(f"unexpected input: {axiom}")
                elif isinstance(axiom, dict):
                    comb, res_type, cls = self._combine_axioms(axiom)
                    my_class = self.onto[cls]
                    if res_type:
                        current_axioms = my_class.equivalent_to
                    else:
                        current_axioms = my_class.is_a
                    if comb:
                        current_axioms.append(comb)
                    else:
                        self.logger.warning(f"unexpected input: {axiom}")
        self.onto.save(file=self.path)

    def _tuple_to_res(
        self, supercls: str, resinfo: list, opinfo: list, dpinfo: list, axiom: list
    ) -> typing.Union[ClassConstruct, None]:
        """
        :param supercls: parent class or equivalent class, depending on equiv parameter
        :param resinfo: list with general restriction info [prop, inverted, p_type,
            cardin, negated]
        :param opinfo: list with op restriction info [op-object]
        :param dpinfo: list with dp restriction info [dprange, minex, minin,
            exact, maxin, maxex]
        :param axiom: list with complete axiom info
        """
        if supercls and not any(opinfo) and not any(dpinfo):
            return self.onto[supercls]
        elif any(opinfo) and not any(dpinfo):
            obj = opinfo[0]
        elif not any(opinfo) and any(dpinfo):
            obj = None
            if resinfo[1]:
                self.logger.warning(
                    f"invalid dp constraint - dp may not be inverted: {axiom}"
                )
                return None
            if resinfo[2] in ["some", "only"]:
                obj = self._dp_constraint(dpinfo)
            elif resinfo[2] in ["value"] and dpinfo[3]:
                obj = self._transform_to_dp_type(dpinfo[0], dpinfo[3])
            if obj is None:
                self.logger.warning(f"invalid dp constraint: {axiom}")
                return None
            if resinfo[2] in ["exactly", "max", "min"]:
                # NOTE: this may be resolved in future versions of Owlready2
                self.logger.warning(
                    "qualified cardinality restrictions currently not "
                    f"supported for DPs: {axiom}"
                )
                return None
        else:
            self.logger.warning(f"restriction includes both op and dp: {axiom}")
            return None
        if resinfo[1]:
            resinfo[0] = Inverse(resinfo[0])
        if (
            resinfo[2] in ["some", "only", "value"]
            and not resinfo[3]
            and not resinfo[3] == 0
        ):
            res = getattr(resinfo[0], resinfo[2])(obj)
        elif resinfo[2] in ["exactly", "max", "min"] and (
            resinfo[3] or resinfo[3] == 0
        ):
            res = getattr(resinfo[0], resinfo[2])(resinfo[3], obj)
        else:
            self.logger.warning(f"unexpected cardinality definition: {axiom}")
            return None
        if resinfo[4]:
            res = Not(res)
        return res

    def _dp_constraint(self, dpres: list) -> typing.Optional[ConstrainedDatatype]:
        """
        :param dpres: DP restriction is list of the form [dprange, minex, minin,
            exact, maxin, maxex]
        :return: constrained datatype for DP, set to None if invalid
        """
        dp_range = None
        if dpres[0] not in list(self._dp_range_types.keys()):
            self.logger.warning(f"unexpected dp range: {dpres}")
        if self._check_available_vals(dpres, [0]):
            dp_range = self._dp_range_types[dpres[0]]
        elif self._check_available_vals(dpres, [0, 3]):
            dp_range = ConstrainedDatatype(
                self._dp_range_types[dpres[0]],
                min_inclusive=dpres[3],
                max_inclusive=dpres[3],
            )
        elif self._check_available_vals(dpres, [0, 1, 4]):
            dp_range = ConstrainedDatatype(
                self._dp_range_types[dpres[0]],
                min_exclusive=dpres[1],
                max_inclusive=dpres[4],
            )
        elif self._check_available_vals(dpres, [0, 1, 5]):
            dp_range = ConstrainedDatatype(
                self._dp_range_types[dpres[0]],
                min_exclusive=dpres[1],
                max_exclusive=dpres[5],
            )
        elif self._check_available_vals(dpres, [0, 2, 4]):
            dp_range = ConstrainedDatatype(
                self._dp_range_types[dpres[0]],
                min_inclusive=dpres[2],
                max_inclusive=dpres[4],
            )
        elif self._check_available_vals(dpres, [0, 2, 5]):
            dp_range = ConstrainedDatatype(
                self._dp_range_types[dpres[0]],
                min_inclusive=dpres[2],
                max_exclusive=dpres[5],
            )
        elif self._check_available_vals(dpres, [0, 1]):
            dp_range = ConstrainedDatatype(
                self._dp_range_types[dpres[0]], min_exclusive=dpres[1]
            )
        elif self._check_available_vals(dpres, [0, 2]):
            dp_range = ConstrainedDatatype(
                self._dp_range_types[dpres[0]], min_inclusive=dpres[2]
            )
        elif self._check_available_vals(dpres, [0, 4]):
            dp_range = ConstrainedDatatype(
                self._dp_range_types[dpres[0]], max_inclusive=dpres[4]
            )
        elif self._check_available_vals(dpres, [0, 5]):
            dp_range = ConstrainedDatatype(
                self._dp_range_types[dpres[0]], max_exclusive=dpres[5]
            )
        else:
            self.logger.warning(f"unexpected dp range restriction: {dpres}")
        return dp_range

    def _check_available_vals(self, values: list, expected_values: list) -> bool:
        """
        :param values: list with values
        :param expected_values: list with indices of expected values
        :return: True iff expected indices contain values
        """
        indices = [x for x, _ in enumerate(values)]
        assert all(x in indices for x in expected_values), "invalid expected_values"
        test = all(
            self._check_value_validity(values[i]) for i in expected_values
        ) and not any(
            self._check_value_validity(values[i])
            for i in [e for e in indices if e not in expected_values]
        )
        return test

    @staticmethod
    def _check_value_validity(value) -> bool:
        return value is not None and value != ""

    def add_gcas(self, gcas: list) -> None:
        """workaround for representing General Class Axioms
        adds two helper classes, each defined via an axiom, that are defined to be equivalent
        helper classes are denoted with an underscore

        :param gcas: list of two-tuples with axioms as defined by add_axioms()
        """
        with self.onto:

            class GcaHelper(Thing):
                comment = [
                    "Helper class for workaround to represent General Class Axioms"
                ]

            for gca in gcas:
                for a in gca:
                    gh_name = "_" + "".join(
                        random.choices(string.ascii_letters + string.digits, k=16)
                    )
                    a.insert(0, gh_name)
                    a.insert(1, "GcaHelper")
                    assert (
                        a[-1] is True
                    ), "GCAs must be equivalented with auxiliary classes for inferences to work"
                self.add_taxo([a[:2] for a in gca])
                for a in gca:
                    a[1] = None
                gca.append([gca[0][0], gca[1][0]] + [None] * 12 + [True])
                self.add_axioms(gca)
        self.onto.save(file=self.path)

    def add_ops(self, op_tuples: list) -> None:
        """add object properties including their axioms to onto
        NOTE: only one inverse_prop can be processed per tuple

        :param op_tuples: list of tuples of the form [op, super-op, domain, range,
            functional, inverse functional, transitive, symmetric,
            asymmetric, reflexive, irreflexive, inverse_prop]
        """
        with self.onto:
            for op in op_tuples:
                try:
                    my_op = self._create_notion(op[0], op[1], "o")
                except (TypeError, InfoException):
                    self.logger.warning(f"unexpected op info: {op}")
                    continue
                if op[2]:
                    my_op.domain.append(self.onto[op[2]])
                if op[3]:
                    my_op.range.append(self.onto[op[3]])
                for count, charac in enumerate(op[4:11]):
                    if charac:
                        my_op.is_a.append(self._prop_types[count])
                if op[-1]:
                    my_op.inverse_property = self.onto[op[11]]
        self.onto.save(file=self.path)

    def add_dps(self, dp_tuples: list) -> None:
        """add datatype properties including their axioms to onto

        :param dp_tuples: list of input tuples of the form [dp, super-dp, functional,
            domain, range, minex, minin, exact, maxin, maxex]
        """
        with self.onto:
            for dp in dp_tuples:
                try:
                    my_dp = self._create_notion(dp[0], dp[1], "d")
                except (TypeError, InfoException):
                    self.logger.warning(f"unexpected dp info: {dp}")
                    continue
                if dp[2]:
                    my_dp.is_a.append(FunctionalProperty)
                if dp[3]:
                    try:
                        my_dp.domain.append(self.onto[dp[3]])
                    except Exception:
                        self.logger.warning(f"unexpected dp domain: {dp}")
                if any(self._check_value_validity(d) for d in dp[4:]):
                    dprange = self._dp_constraint(dp[4:])
                    if dprange:
                        my_dp.range = dprange
                    else:
                        self.logger.warning(f"unexpected dp range: {dp}")
                        continue
        self.onto.save(file=self.path)

    def add_instances(self, instance_tuples: list) -> None:
        """add instances and their relations to onto

        :param instance_tuples: list of tuples of the form [instance, class,
            property, range, range-type]
        """
        with self.onto:
            for inst in instance_tuples:
                if inst[0] and inst[1]:
                    my_instance = self.onto[inst[1]](inst[0])
                else:
                    self.logger.warning(f"unexpected instance info: {inst}")
                if not any(inst[2:]):
                    continue
                if inst[2] and self._check_value_validity(inst[3]):
                    pred = self.onto[inst[2]]
                    if DataProperty in pred.is_a:
                        if inst[4] and not inst[4] in self._dp_range_types:
                            self.logger.warning(f"unexpected DP range: {inst}")
                        elif inst[4]:
                            val = self._transform_to_dp_type(inst[4], inst[3])
                        else:
                            self.logger.warning(
                                f"DP range undefined - defaulting to string: {inst}"
                            )
                            val = inst[3]
                    elif ObjectProperty in pred.is_a and not inst[4]:
                        val = self.onto[inst[3]]
                    self._add_instance_relation(my_instance, pred, val)
                else:
                    self.logger.warning(f"unexpected triple: {inst}")
        self.onto.save(file=self.path)

    @staticmethod
    def _add_instance_relation(subj, pred, obj) -> None:
        if FunctionalProperty in pred.is_a:
            setattr(subj, pred.name, obj)
        else:
            getattr(subj, pred.name).append(obj)

    def add_distinctions(self, distinct_sets: list) -> None:
        """make classes disjoint and instances distinct
        NOTE: distinctions may lead to inconsistencies reasoners cannot handle

        :param distinct_sets: list of lists with disjoint/ different elements
        """
        funcs = {"classes": AllDisjoint, "instances": AllDifferent}
        with self.onto:
            for ds in distinct_sets:
                try:
                    func = funcs[ds[0]]
                    func([self.onto[elem] for elem in ds[1]])
                except KeyError:
                    self.logger.warning(f"unknown distinction type {ds[0]}")
        self.onto.save(file=self.path)

    def remove_elements(self, elem_list: list) -> None:
        """remove elements, all their descendents and (in case of classes) instances,
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
        self.onto.save(file=self.path)

    def add_label(self, name: str, label: str, lang: str = None) -> None:
        """add label in language specified as localized string, defaults to
        regular string if no language is specified

        :param name: entity name
        :param label: label to be appended
        :param lang: label's language (optional)
        """
        entity = self._get_entity_by_name(name)
        if not entity:
            return
        desc = entity.label
        self._add_description_generic(desc, label, lang)

    def add_annotation(self, name: str, comment: str, lang: str = None) -> None:
        """add annotation in language specified as localized string, defaults to
        regular string if no language is specified

        :param name: entity name
        :param comment: annotation to append
        :param lang: annotation's language (optional)
        """
        entity = self._get_entity_by_name(name)
        if not entity:
            return
        desc = entity.comment
        self._add_description_generic(desc, comment, lang)

    def _get_entity_by_name(self, name: str) -> typing.Optional[Thing]:
        entity = None
        try:
            entity = self.onto[name]
        except AttributeError:
            self.logger.info(
                f"unexpected entity: {name}, return None and continue anyways"
            )
        return entity

    def _add_description_generic(
        self, desc_list: list, description: str, lang: typing.Optional[str]
    ) -> None:
        """add description in language specified as localized string, defaults to
        regular string if no language is specified

        :param desc_list: list to which to append the description
        :param description: description to append
        :param lang: description's language (optional)
        """
        if lang:
            desc_list.append(locstr(description, lang=lang))
        else:
            desc_list.append(description)
        self.onto.save(file=self.path)

    def remove_from_taxo(self, elem_list: list, reassign: bool = True) -> None:
        """remove a class from the taxonomy, but keep all subclasses and instances
        by relating them to parent
        NOTE: elem is not replaced in axioms bc this may be semantically incorrect

        :param elem_list: list of elements to be removed from onto
        :param reassign: add all restrictions to subclasses via is_a
        """
        with self.onto:
            for elem in elem_list:
                parents = list(
                    set(self.onto[elem].ancestors()).intersection(self.onto[elem].is_a)
                )
                parent = [p for p in parents if not p in self._prop_types]
                if len(parent) > 1:
                    self.logger.warning(f"unexpected parent classes: {parents}")
                descendants = list(self.onto[elem].descendants())
                descendants.remove(self.onto[elem])
                individuals = list(self.onto[elem].instances())
                if reassign:
                    sc_res = self.get_class_restrictions(
                        self.onto[elem].name, res_type="is_a"
                    )
                    eq_res = self.get_class_restrictions(
                        self.onto[elem].name, res_type="equivalent_to"
                    )
                for desc in descendants:
                    desc.is_a.append(parent[0])
                    if reassign:
                        desc.is_a = desc.is_a + sc_res + eq_res
                for ind in individuals:
                    ind.is_a.append(parent[0])
                destroy_entity(self.onto[elem])
        self.onto.save(file=self.path)

    def get_class_restrictions(
        self, class_name: str, res_type: str = "is_a", res_only: bool = True
    ) -> list:
        """retrieve restrictions on specific class by restriction type

        :param class_name: name of the class for which restrictions shall be returned
        :param res_only: only returns Restrictions if set to True, if set to False
            parent class(es) are also included
        :param res_type: restriction type, either is_a or equivalent_to
        :return: list of restrictions on class
        """
        with self.onto:
            if res_type == "is_a":
                elems = self.onto[class_name].is_a
            elif res_type == "equivalent_to":
                elems = self.onto[class_name].equivalent_to
            else:
                self.logger.warning(f"unexpected res_type: {res_type}")
                sys.exit(1)
            if res_only:
                elems = [x for x in elems if isinstance(x, Restriction)]
        return elems

    def remove_restrictions_on_class(self, class_name: str) -> None:
        """remove all restrictions on a given class

        :param class_name: name of the class for which restrictions shall be removed
        """
        with self.onto:
            for lst in self.onto[class_name].is_a, self.onto[class_name].equivalent_to:
                self._remove_restr_from_class_def(lst)
        self.onto.save(file=self.path)

    def remove_restrictions_including_prop(self, prop_name: str) -> None:
        """remove class restrictions that include a certain property

        :param prop_name: name of the property for which all class restrictions
            shall be removed
        """
        with self.onto:
            for c in self.onto.classes():
                for lst in c.is_a, c.equivalent_to:
                    self._remove_restr_from_class_def(lst, self.onto[prop_name])
        self.onto.save(file=self.path)

    @staticmethod
    def _remove_restr_from_class_def(cls_restrictions, prop=None) -> None:
        """remove all restrictions from list

        :param cls_restrictions: restrictions on a class, either is_a or equivalent_to
        :param prop: optional; limits results to restrictions including a certain property
        """
        for r in [r for r in cls_restrictions if isinstance(r, Restriction)]:
            if not prop or prop and r.property == prop:
                cls_restrictions.remove(r)

    def reasoning(
        self, reasoner: str = "hermit", save: bool = False, debug: bool = False
    ) -> list:
        """run reasoner to check consistency and infer new facts

        :param reasoner: reasoner can be eiter hermit or pellet
        :param save: bool - save inferences into original file
        :param debug: bool - log pellet explanations for inconsistencies; only
            works with Pellet
        :return: returns list of inconsistent classes if there are any
        """
        inconsistent_classes = []
        # add temporary world for inferences
        inferences = World()
        self._check_reasoner(reasoner)
        inf_onto = inferences.get_ontology(self.path).load()
        with inf_onto:
            try:
                with self._redirect_to_log():
                    if reasoner == "hermit":
                        sync_reasoner_hermit([inf_onto])
                    elif reasoner == "pellet":
                        # pellet explanations are generated if debug is set to >=2
                        sync_reasoner_pellet(
                            [inf_onto],
                            infer_property_values=True,
                            infer_data_property_values=True,
                            debug=debug + 1,
                        )
                inconsistent_classes = list(inf_onto.inconsistent_classes())
            except Exception as exc:
                if reasoner == "pellet" and debug:
                    inconsistent_classes = self._analyze_pellet_results(str(exc))
                else:
                    inconsistent_classes = self.reasoning("pellet", False, True)
        if inconsistent_classes:
            self.logger.warning(f"the ontology is inconsistent: {inconsistent_classes}")
            if Nothing in inconsistent_classes:
                inconsistent_classes.remove(Nothing)
        elif save and not inconsistent_classes:
            inf_onto.save(file=self.path)
            self._reload_from_file()
        return inconsistent_classes

    def _check_reasoner(self, reasoner: str) -> None:
        reasoners = ["hermit", "pellet"]
        if reasoner not in reasoners:
            self.logger.warning(
                f"unexpected reasoner: {reasoner} - available reasoners: {reasoners}"
            )

    def _analyze_pellet_results(self, exc: str) -> list:
        """analyze the explanation returned by Pellet, print it and return
        inconsistent classes
        IDEA: also consider restrictions on properties and facts about instances

        :param exc: string of exception thrown during reasoning process
        :return: list of classes identified as problematic
        """
        inconsistent_classes = []
        self.logger.error(repr(exc))
        expl = self._extract_pellet_explanation(traceback.format_exc())
        if expl[0]:
            print("Pellet provides the following explanation(s):")
            print(*expl[0], sep="\n")
            inconsistent_classes = [
                self.onto[ax[0]]
                for ex in expl[1]
                for ax in ex
                if self.onto[ax[0]] in self.onto.classes()
            ]
        else:
            print("There was a more complex issue, check log for traceback")
            self.logger.error(self._indent_log(traceback.format_exc()))
        return list(set(inconsistent_classes))

    @staticmethod
    def _extract_pellet_explanation(pellet_traceback: str) -> tuple:
        """extract reasoner explanation

        :param pellet_traceback: traceback created when running reasoner
        :return: tuple of entire explanation and list of axioms included in explanation
        """
        rex = re.compile(r"Explanation\(s\): \n(.*?)\n\n", re.DOTALL | re.MULTILINE)
        res = set(re.findall(rex, pellet_traceback))
        axioms: list = []
        if res:
            expls = [[l[5:] for l in expl.split("\n")] for expl in res]
            axioms = [[axiom.split() for axiom in block] for block in expls]
        return (res, axioms)

    def debug_onto(
        self, reasoner: str = "hermit", assume_correct_taxo: bool = True
    ) -> None:
        """interactively (CLI) fix inconsistencies

        :param assume_correct_taxo: if True, the user interactions will be limited
            to restrictions, i.e., options to delete taxonomical relations are
            not included, e.g., A rdfs:subClassOf B
        :param reasoner: reasoner to be used for inferences
        """
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
                    try:
                        sync_reasoner_pellet(
                            [debug_onto],
                            infer_property_values=True,
                            infer_data_property_values=True,
                            debug=2,
                        )
                    except base.OwlReadyInconsistentOntologyError as err:
                        self.logger.error(repr(err))
                        self.logger.error(self._indent_log(traceback.format_exc()))
                        print(
                            "There was an issue with the input ontology; check the log for details."
                        )
                        self._analyze_pellet_results(traceback.format_exc())
                    # IDEA: further analyze reasoner results to pin down cause of inconsistency
            if assume_correct_taxo:
                pot_probl_ax = {
                    "is_a": self._get_incon_class_res("is_a", inconsistent_classes),
                    "equivalent_to": self._get_incon_class_res(
                        "equivalent_to", inconsistent_classes
                    ),
                }
            else:
                pot_probl_ax = {
                    "is_a": [self.onto[ic.name].is_a for ic in inconsistent_classes],
                    "equivalent_to": [
                        self.onto[ic.name].equivalent_to for ic in inconsistent_classes
                    ],
                }
            ax_msg = "Potentially inconsistent axiom: "
            for rel in "is_a", "equivalent_to":
                self._interactively_delete_axs_by_rel(
                    rel, inconsistent_classes, pot_probl_ax, ax_msg
                )
            self.onto.save(file=self.path)
            self.debug_onto(reasoner, assume_correct_taxo)

    def _get_incon_class_res(self, restype: str, inconsistent_classes: list) -> list:
        """
        :param restype: type of class restriction, either is_a or equivalent_to
        :return: list of class restrictions for inconsistent_classes - does not return parent classes
        """
        return [
            self.get_class_restrictions(ic.name, res_type=restype, res_only=True)
            for ic in inconsistent_classes
        ]

    def _interactively_delete_axs_by_rel(
        self, rel: str, classes: list, axioms: dict, msg: str
    ) -> None:
        """
        :param rel: relation between class and axioms - is_a or equivalent_to
        :param classes: classes for which axioms are to be removed
        :param axioms: axioms which should be checked for removal
        :param msg: message to be displayed when prompting user
        """
        for count, ic in enumerate(classes):
            for ax in axioms[rel][count]:
                if self._bool_user_interaction(
                    "Delete " + rel + " axiom?",
                    msg + ic.name + " " + rel + " " + str(ax),
                ):
                    if isinstance(ax, ThingClass):
                        getattr(self.onto[ic.name], rel).remove(self.onto[ax.name])
                    else:
                        getattr(self.onto[ic.name], rel).remove(ax)
                    # IDEA: instead of simply deleting axioms, also allow user to edit them

    @staticmethod
    def _bool_user_interaction(question: str, info: str = None) -> bool:
        """simple CLI for yes/ no/ quit interaction"""
        answer = {"y": True, "n": False}
        if info:
            print(info)
        print(question + " [y(es), n(o), q(uit)]")
        user_input = input()
        while user_input not in ["y", "n", "q"]:
            print("invalid choice, please try again")
            user_input = input()
        if user_input == "q":
            print("quitting - process needs to be restarted")
            sys.exit(0)
        else:
            return answer[user_input]

    @staticmethod
    def _remove_nt_brackets(triple: list) -> list:
        for c, _ in enumerate(triple):
            triple[c] = triple[c].replace("<", "")
            triple[c] = triple[c].replace(">", "")
        return triple

    @staticmethod
    def _df_to_nx_incl_labels(df: pd.DataFrame, coloring: dict) -> nx.MultiDiGraph:
        """turns a pandas dataframe into a networkx graph

        :param df: pandas df with spo-triples
        :param coloring: dict with colors as keys and lists of nodes as values
        :return: nxgraph for the ontology including labels and coloring
        """
        nxgraph = nx.from_pandas_edgelist(
            df,
            source="subject",
            target="object",
            edge_attr="predicate",
            create_using=nx.MultiDiGraph(),
        )
        # manually set predicates as labels
        for e in nxgraph.edges.items():
            e[1]["label"] = e[1].pop("predicate")
        # assert that a node may not have more than one color
        assert not set(list(coloring.values())[0]).intersection(
            *list(coloring.values())
        ), "Several colors specified for one node"
        for n in nxgraph.nodes.items():
            for color in coloring.keys():
                if n[0] in coloring[color]:
                    n[1]["color"] = color
        return nxgraph

    def _ntriples_to_df(self) -> pd.DataFrame:
        self.export_ntriples()
        with open(self.path.rsplit(".", 1)[0] + ".nt", "r") as f:
            lines = f.readlines()
        df = pd.DataFrame(columns=["subject", "predicate", "object"])
        for rownum, row in enumerate(lines):
            df.loc[rownum] = self._remove_nt_brackets(
                row.rsplit(".", 1)[0].split(" ")[:3]
            )
        return df

    @staticmethod
    def _query_results_to_df(query_results: list) -> pd.DataFrame:
        clean_data = [
            [str(elem).rsplit("#", maxsplit=1)[-1] for elem in row]
            for row in query_results
        ]
        df = pd.DataFrame(clean_data, columns=["subject", "predicate", "object"])
        return df

    def _plot_nxgraph(
        self,
        nxgraph: nx.MultiDiGraph,
        open_html: bool = False,
        interactive: bool = False,
    ) -> None:
        """create html file for the network's plot

        :param nxgraph: networkx graph including the ontology's triples
        :param open_html: directly open the html file created using the default program
        :param interactive: activates mode for changing network appearance
        """
        net = Network(
            directed=True,
            height="100%",
            width="100%",
            bgcolor="#222222",
            font_color="white",
        )
        net.set_options(pkg_resources.read_text(config, "network_visualization.config"))
        net.from_nx(nxgraph)
        if interactive:
            net.show_buttons()
        html_name = self.path.rsplit(".", 1)[0] + ".html"
        if open_html:
            net.show(html_name)
        else:
            net.write_html(html_name)

    def _config_plot_query_body(
        self,
        classes: list = None,
        properties: list = None,
        focusnode: str = None,
        radius: int = None,
        tbox_only: bool = False,
        include_class_res: bool = True,
        show_class_descendants: bool = True,
    ) -> str:
        """configure body for SPARQL query that identifies triples for plot

        :param classes: classes to be returned including their instances
        :param properties: properties to be returned
        :param focusnode: node whose environment shall be displayed
        :param radius: maximum distance, i.e., relations, between a node and focusnode
        :param tbox_only: limit query to TBox if set to True
        :param include_class_res: also return simplified spo-triples for class
            restrictions if True
        :param show_class_descendants: also explicitly include subclasses of the classes specified
        :return: body for SPARQL query
        """
        max_radius = 5
        nodes_to_be_ignored = [
            "owl:Class",
            "owl:Thing",
            "owl:NamedIndividual",
            "owl:Restriction",
        ]

        if classes and show_class_descendants:
            descendent_lists = [
                [desc.name for desc in self.onto[c].descendants()] for c in classes
            ]
            subclasses = list({c for sublist in descendent_lists for c in sublist})
        elif classes and not show_class_descendants:
            subclasses = classes

        def _sparql_set_values(node, values):
            return (
                "VALUES ?"
                + node
                + " {rdf:type rdfs:subClassOf "
                + " ".join([":" + v for v in values])
                + "} . "
            )

        def _sparql_set_in(node, values, sep=None):
            if not sep:
                sep = ""
            return (
                "FILTER ( ?"
                + node
                + " IN ("
                + ", ".join([sep + v for v in values])
                + ") ) . "
            )

        querypt_class_rels = (
            "?s rdfs:subClassOf | owl:equivalentClass ?res . \n"
            "?res a owl:Restriction . \n"
            "?res owl:onProperty ?p . \n"
            "?res owl:onClass | owl:someValuesFrom | owl:allValuesFrom | owl:hasValue ?o . "
        )
        querypt1 = "SELECT DISTINCT ?s ?p ?o WHERE {\n"

        if include_class_res:
            # NOTE: only atomic axioms are currently supported
            querypt1 += "{\n?s ?p ?o . \n} UNION {\n" + querypt_class_rels + "\n}"
        else:
            querypt1 += "?s ?p ?o . \n"
        querypt2 = "}"
        if properties:
            querypt_rels = _sparql_set_values("p", properties)
        else:
            querypt_rels = ""
        if classes:
            query_nodes_dict: dict = {}
            for node in ["s", "o"]:
                querypt_classes = "?s ?p ?o . \n" + _sparql_set_in(
                    node, subclasses, ":"
                )
                querypt_class_res = (
                    querypt_class_rels + "\n" + _sparql_set_in(node, subclasses, ":")
                )
                querypt_instances = (
                    "{\n?"
                    + node
                    + " a/rdfs:subClassOf* ?"
                    + node
                    + "class . \n"
                    + _sparql_set_in(node + "class", classes, ":")
                    + "\n} UNION {\n?s ?p ?o . \nFILTER NOT EXISTS {?"
                    + node
                    + " a ?"
                    + node
                    + "p . }\nFILTER NOT EXISTS {?"
                    + node
                    + " rdfs:subClassOf ?"
                    + node
                    + "p . } \n}"
                )
                query_nodes_dict[node] = (
                    "{\n"
                    + querypt_classes
                    + "\n} UNION {\n"
                    + querypt_class_res
                    + "\n}"
                )
                if not tbox_only:
                    query_nodes_dict[node] += " UNION {\n"
                    query_nodes_dict[node] += querypt_instances
                    query_nodes_dict[node] += "\n}"
            querypt_nodes = "\n".join(query_nodes_dict.values())
        else:
            querypt_nodes = ""
        query_rel_lim = ""
        if focusnode and radius:
            assert radius <= max_radius, "max radius violated"
            if properties:
                rels = properties
            else:
                rels = [p.name for p in self.onto.properties()]
            query_rel_lim = (
                ":"
                + focusnode
                + " "
                + "?/".join(
                    ["(rdf:type|rdfs:subClassOf|:" + "|:".join(rels) + ")"] * radius
                )
                + "? ?o . "
            )
        elif focusnode and not radius or not focusnode and radius:
            self.logger.warning(
                "focus: both a focusnode and a radius must be specified - ignoring the focus"
            )
        querypt_ignore = ""
        for node in ["s", "o"]:
            querypt_ignore += (
                "\nMINUS {\n?s ?p ?o . \n"
                + _sparql_set_in(node, nodes_to_be_ignored)
                + "\n}"
            )
        querypt_ignore += "\nMINUS {\n?s ?p ?o . \n ?o a owl:Restriction . \n}"
        query_body = "\n".join(
            [
                querypt1,
                querypt_rels,
                querypt_nodes,
                query_rel_lim,
                querypt_ignore,
                querypt2,
            ]
        )
        return query_body

    def _render_by_label(
        self, graph: nx.MultiDiGraph, lang: str = None
    ) -> nx.MultiDiGraph:
        """relabel the networkx graph's nodes and edges using the labels specified
        in the ontology (if there are labels available); defaults to first label

        :param graph: input graph w/ names
        :param lang: desired label language
        :return: graph w/ labels instead of names
        """
        mapping: dict = {}
        for n in graph.nodes():
            label = self._name_to_label(n, lang)
            if label != n:
                mapping[n] = label
        graph = nx.relabel_nodes(graph, mapping)
        for e in graph.edges.items():
            label = self._name_to_label(e[1]["label"], lang)
            if label != e[1]["label"]:
                e[1]["label"] = label
        return graph

    def _name_to_label(self, name: str, lang: str = None) -> str:
        """return (first) label for an entity in the language specified

        :param elem: name of the ontology's element
        :param lang: indicates desired label language, can be none to simply use
            first label available
        :return: elem's (first) label, defaults to name if there is no label
            available in the language specified available
        """
        try:
            elem = self.onto[name]
            if not lang and elem.label.first():
                label = elem.label.first()
            elif [l for l in elem.label if l.lang == lang]:
                label = [l for l in elem.label if l.lang == lang][0]
            else:
                label = name
        # catch literals
        except AttributeError:
            label = name
        return label

    def visualize(
        self,
        classes: list = None,
        properties: list = None,
        focusnode: str = None,
        radius: int = None,
        bylabel: bool = False,
        lang: str = None,
        open_html: bool = False,
        tbox_only: bool = False,
    ) -> None:
        """visualize onto as a graph; generates html

        :param classes: list of classes to be included in plot
        :param properties: list of properties to be included in plot
        :param focusnode: node around which a partial graph shall be displayed
        :param radius: maximum number of relations between a node and a node of
            one of the classes specified
        :param bylabel: render visualization by labels (if available)
        :param lang: language of the labels to be displayed
        :param open_html: open html file generated
        :param tbox_only: only visualizes TBox if set to True
        :return: None
        """
        # graph coloring settings; note that literals default to grey
        classcolor = "#0065bd"
        instancecolor = "#98c6ea"
        coloring = {
            classcolor: [c.name for c in self.onto.classes()],
            instancecolor: [i.name for i in self.onto.individuals()],
        }

        if not classes and not properties and not focusnode and not radius:
            graphdata = self._ntriples_to_df()
        else:
            query_body = self._config_plot_query_body(
                classes, properties, focusnode, radius, tbox_only
            )
            query_results = self.query_onto(self._build_query(query_body))
            graphdata = self._query_results_to_df(query_results)
        nxgraph = self._df_to_nx_incl_labels(graphdata, coloring)
        if bylabel:
            nxgraph = self._render_by_label(nxgraph, lang)
        self._plot_nxgraph(nxgraph, open_html)
