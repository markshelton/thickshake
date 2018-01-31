# -*- coding: utf-8 -*-
#!/usr/bin/env python
"""
"""
##########################################################
# Standard Library Imports

from collections import defaultdict
import logging
import os

##########################################################
# Third Party Imports

import pymarc
from tqdm import tqdm

##########################################################
# Local Imports

from thickshake.marc.reader import read_file
from thickshake.marc.utils import load_config_file, get_subfield_from_tag
from thickshake.storage.database import Database

##########################################################
# Typing Configuration

from typing import Optional, Union, List, Dict, Any, Tuple

Tag = Dict[str, Optional[str]]
PymarcField = Any
PymarcRecord = Any
FilePath = str
DBSession = Any
DBObject = Any

##########################################################
# Constants


##########################################################
# Logging Configuration

logger = logging.getLogger(__name__)


##########################################################
# Functions


def get_data(
        data: Union[PymarcField, PymarcRecord],
        loader: Dict[str, Any],
        config: Dict[str, Any],
    ) -> Union[List[PymarcField], List[PymarcRecord]]:
    fields = [] # type: List[str]
    if not isinstance(data, pymarc.Field): 
        for k,v in loader.items():
            if not k.startswith(config["GENERATED_FIELD_PREFIX"]) and not k.startswith(config["TABLE_PREFIX"]):
                if config["TAG_DELIMITER"] in str(v):
                    field = str(v).split(config["TAG_DELIMITER"])[0]
                    fields.append(field)
        if len(set(fields)) == 1:
            return data.get_fields(fields[0])
    return [data]


def get_loaders(loader: Dict[str, Any], config: Dict[str, Any]) -> List[Dict[str, Any]]:
    loaders = [v for k,v in loader.items() if k.startswith(config["TABLE_PREFIX"])]
    return loaders


def get_table_name(loader: Dict[str, Any], config: Dict[str, Any]) -> Optional[str]:
    for k,v in loader.items():
        if not k.startswith(config["GENERATED_FIELD_PREFIX"]) and not k.startswith(config["TABLE_PREFIX"]):
            table_name = k.split(config["TABLE_DELIMITER"])[0]
            return table_name
    return None


def parse_record(
        record: Union[PymarcField, PymarcRecord],
        loader: Dict[str, Any],
        config: Dict[str, Any],
        foreign_keys: Dict[str, str]
    ) -> Dict[str, Any]:
    parsed_record = {} # type: Dict[str, Optional[str]]
    for k,v in loader.items():
        if not k.startswith(config["TABLE_PREFIX"]):
            table_name, column = k.split(".")
            if k.startswith(config["GENERATED_FIELD_PREFIX"]):
                parsed_value = None
            elif str(v).startswith(config["TABLE_PREFIX"]):
                table = str(v).replace(config["TABLE_PREFIX"], "").lower()
                if foreign_keys[table]:
                    parsed_value = foreign_keys[table][0]
                else: parsed_value = None
            elif config["TAG_DELIMITER"] in str(v):
                parsed_value = get_subfield_from_tag(record, v, tag_delimiter=config["TAG_DELIMITER"])
            else: parsed_value = v
            parsed_record[column] = parsed_value
    return parsed_record


def store_record(
        parsed_record: Dict[str, Any],
        foreign_keys: Dict[str, str],
        table_name: str,
        database: Database,
        **kwargs: Any
    ) -> Dict[str, str]:
    with database.manage_db_session(**kwargs) as session:
        db_object = database.merge_record(table_name, parsed_record, foreign_keys, **kwargs)
        if hasattr(db_object, "uuid"):
            return db_object.uuid


def load_record(
        data: Union[PymarcField, PymarcRecord],
        loader: Dict[str, Any],
        config: Dict[str, Any],
        database: Database,
        foreign_keys: Dict[str, str] = None,
        **kwargs: Any
    ) -> None:
    if foreign_keys is None: foreign_keys = defaultdict(list)
    records = get_data(data, loader, config)
    sub_loaders = get_loaders(loader, config)
    table_name = get_table_name(loader, config)
    for record in records:
        if table_name:
            parsed_record = parse_record(record, loader, config, foreign_keys)
            new_primary_key = store_record(parsed_record, foreign_keys, table_name, database, **kwargs)
            foreign_keys[table_name].append(new_primary_key)
        for sub_loader in sub_loaders:
            load_record(data=record, loader=sub_loader, config=config, database=database, foreign_keys=foreign_keys)
        if table_name: foreign_keys[table_name].pop()


def load_database(
        records: List[PymarcRecord],
        loader_config_file: FilePath=None,
        **kwargs: Any
    ) -> None:
    database = Database(**kwargs)
    loader_map, loader_config = load_config_file(loader_config_file)
    for record in tqdm(records, desc="Loading Records"):
        load_record(data=record, loader=loader_map, config=loader_config, database=database, **kwargs)


##########################################################
# Scripts


def main():
    records = read_file(input_metadata_file="/home/app/data/input/metadata/marc21.xml", sample=20)
    load_database(records, verbosity="DEBUG")


if __name__ == "__main__":
    main()


##########################################################
