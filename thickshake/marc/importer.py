# -*- coding: utf-8 -*-
#!/usr/bin/env python
"""
"""
##########################################################
# Standard Library Imports

import logging
import os

##########################################################
# Third Party Imports

from sqlalchemy.exc import IntegrityError
import pymarc
from tqdm import tqdm
import yaml

##########################################################
# Local Imports

from thickshake.marc.reader import read_file
from thickshake.marc.utils import load_config_file
from thickshake.storage.database import Database
from thickshake.helpers import open_file

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
# Helper Functions


def get_subfield_from_field(field: PymarcField, subfield_key: str) -> Optional[str]:
    if subfield_key not in field: return None
    subfield = field[subfield_key]
    return subfield


def get_subfield_from_record(record: PymarcRecord, field_key: str, subfield_key: str) -> Optional[str]:
    if field_key not in record: return None
    field = record[field_key]
    subfield = get_subfield_from_field(field, subfield_key)
    return subfield


def get_subfield_from_tag(record_or_field: Union[PymarcRecord, PymarcField], tag_key: str, tag_delimiter: str = "$") -> Optional[str]:
    tag = split_tag_key(tag_key, tag_delimiter)
    if tag is None: return None
    field_key = tag["field"]
    subfield_key = tag["subfield"]
    if isinstance(record_or_field, pymarc.Record):
        if field_key is None or subfield_key is None: return None
        return get_subfield_from_record(record_or_field, field_key, subfield_key)
    elif isinstance(record_or_field, pymarc.Field):
        if subfield_key is None: return None
        return get_subfield_from_field(record_or_field, subfield_key)
    else: return None


def split_tag_key(tag_key: str, tag_delimiter: str = "$") -> Optional[Tag]:
    """Split tag into a tuple of the field and subfield."""
    tag_list = tag_key.split(tag_delimiter)
    if len(tag_list) == 2:
        return dict(field=tag_list[0], subfield=tag_list[1])
    elif len(tag_list) == 1:
        return dict(field=tag_list[0], subfield=None)
    else: return None


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
        if not k.startswith(config["GENERATED_FIELD_PREFIX"]) and not k.startswith(config["TABLE_PREFIX"]):
            table_name, column = k.split(".")
            if str(v).startswith(config["TABLE_PREFIX"]):
                table = str(v).replace(config["TABLE_PREFIX"], "").lower()
                parsed_value = next(v for k,v in foreign_keys.items() if k.startswith(table))
            elif config["TAG_DELIMITER"] in str(v):
                parsed_value = get_subfield_from_tag(record, v, tag_delimiter=config["TAG_DELIMITER"])
            else: parsed_value = v
            parsed_record[column] = parsed_value
    return parsed_record


def make_relationship(db_object: DBObject, table_name: str, foreign_keys: Dict[str, str]):
    if db_object is not None:
        if hasattr(db_object, "uuid"):
            foreign_keys[table_name + ".uuid"] = db_object.uuid
    return foreign_keys


def store_record(
        parsed_record: Dict[str, Any],
        foreign_keys: Dict[str, str],
        table_name: str,
        database: Database,
        **kwargs: Any
    ) -> Dict[str, str]:
    with database.manage_db_session(**kwargs) as session:
        db_object = database.merge_record(table_name, parsed_record, **kwargs)
        foreign_keys = make_relationship(db_object, table_name, foreign_keys)
    return foreign_keys


def load_record(
        data: Union[PymarcField, PymarcRecord],
        loader: Dict[str, Any],
        config: Dict[str, Any],
        database: Database,
        foreign_keys: Dict[str, str] = None,
        **kwargs: Any
    ) -> None:
    if foreign_keys is None: foreign_keys = {}
    records = get_data(data, loader, config)
    sub_loaders = get_loaders(loader, config)
    table_name = get_table_name(loader, config)
    for record in records:
        if table_name:
            parsed_record = parse_record(record, loader, config, foreign_keys)
            foreign_keys = store_record(parsed_record, foreign_keys, table_name, database, **kwargs)
        for sub_loader in sub_loaders:
            load_record(data=record, loader=sub_loader, config=config, database=database, foreign_keys=foreign_keys)


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