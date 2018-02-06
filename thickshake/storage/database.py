# -*- coding: utf-8 -*-
#!/usr/bin/env python
"""
"""
##########################################################
# Standard Library Imports

from collections import defaultdict
from contextlib import contextmanager
import logging

##########################################################
# Third Party Imports

from envparse import env
import pandas as pd
from sqlalchemy import create_engine, text, func, inspect
from sqlalchemy.engine import url
from sqlalchemy.exc import IntegrityError, DataError
from sqlalchemy.orm import scoped_session, sessionmaker, load_only
from tqdm import tqdm

##########################################################
# Local Imports

from thickshake._config.schema import Base
from thickshake.utils import maybe_make_directory, Borg

##########################################################
# Typing Configuration

from mypy_extensions import TypedDict
from typing import (
    Optional, Union, List, Dict,
    Any, Tuple, Iterator, Iterable,
)

DBConfig = TypedDict("DBConfig", {
    'database': str, 'drivername': str, 'host': Optional[str],
    'username': Optional[str], 'password': Optional[str],
    }, total=False
)
DBEngine = Any
DBSession = Any
DBObject = Any
Series = Any
DataFrame = Any

##########################################################
# Constants

DB_CONFIG = {} # type: DBConfig
DB_CONFIG["drivername"] = env.str("DB_DRIVER", default="postgres")
DB_CONFIG["host"] = env.str("DB_HOST", default="thickshake_db")
DB_CONFIG["database"] = env.str("POSTGRES_DB", default="thickshake")
DB_CONFIG["username"] = env.str("POSTGRES_USER", default="postgres")
DB_CONFIG["password"] = env.str("POSTGRES_PASSWORD", default="thickshake")

##########################################################
# Initializations

logger = logging.getLogger(__name__)

##########################################################
# Functions


class Database(Borg):
    engine = None
    session = None
    base = None

    def __init__(self, db_config=DB_CONFIG, force=False, **kwargs):
        # type: (DBConfig, bool, **Any) -> None
        Borg.__init__(self)
        if self.engine is None:
            self.engine = self.make_engine(db_config, **kwargs)
            self.base = Base
            if force: self.remove_db_tables()
            self.make_db_tables()
            

    def make_engine(self, db_config, verbosity="INFO", **kwargs):
        # type: (DBConfig, str, **Any) -> DBEngine
        db_url = url.URL(**db_config)
        if db_config["database"] is None: return None
        maybe_make_directory(db_config["database"])
        echo = True if logging.getLogger().getEffectiveLevel() == logging.DEBUG else False
        db_engine = create_engine(db_url, encoding='utf8', convert_unicode=True, echo=echo)
        return db_engine


    def make_db_tables(self):
        # type: () -> None
        self.base.metadata.create_all(self.engine)


    def remove_db_tables(self):
        # type: () -> None
        self.base.metadata.reflect(self.engine)
        self.base.metadata.drop_all(self.engine)


    @contextmanager
    def manage_db_session(self, dry_run=False, **kwargs):
        # type: (bool, **Any) -> Iterator[DBSession]
        Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.session = scoped_session(Session)
        try:
            yield self.session
            if not dry_run: self.session.commit()
        except IntegrityError as e:
            self.session.rollback()
            raise e
        except BaseException:
            self.session.rollback()
            raise
        finally:
            self.session.close()


    def merge_record(self, table_name, parsed_record, foreign_keys, **kwargs):
        # type: (str, Dict[str, Any], Dict[str, str], **Any) -> DBObject
        model = self.get_class_by_table_name(table_name)
        db_object = model(**parsed_record)
        try: 
            if foreign_keys[table_name] and foreign_keys[table_name][-1] is not None:
                db_object.uuid = foreign_keys[table_name][-1]
                self.session.merge(db_object)
            else:
                if not parsed_record or all(v is None for v in parsed_record.values()): return None
                self.session.add(db_object)
            self.session.flush()
        except IntegrityError as e:
            self.session.rollback()
            if not parsed_record or all(v is None for v in parsed_record.values()): return None
            try: 
                self.session.merge(db_object)
                self.session.flush()
            except IntegrityError as e:
                self.session.rollback()
                unique_columns = self.get_unique_columns(table_name)
                q = self.session.query(model)
                for col in unique_columns:
                    try: q = q.filter(getattr(model, col).like(getattr(db_object, col)))
                    except: q = q.filter(getattr(model, col) == getattr(db_object, col))
                matched_obj = q.first()
                db_object = matched_obj
        return db_object


    def get_records(self, table_name="record", **kwargs):
        # type: (str, **Any) -> List[DBObject]
        model = self.get_class_by_table_name(table_name)
        q = self.session.query(model)
        db_objects = q.all()
        return db_objects


    def get_class_by_table_name(self, table_name):
        # type: (str) -> Any
        for c in self.base._decl_class_registry.values():
            if hasattr(c, '__tablename__') and c.__tablename__ == table_name:
                return c


    def get_primary_keys(self, table_name=None, model=None):
        # type: (str, Any) -> List[str]
        assert model is not None or table_name is not None
        if model is None and table_name is not None: 
            model = self.get_class_by_table_name(table_name)
        pk_columns = inspect(model).primary_key
        return [pk.name for pk in pk_columns]


    def get_unique_columns(self, table_name):
        # type: (str) -> List[str]
        insp = inspect(self.engine)
        unique_constraints = insp.get_unique_constraints(table_name)
        return [unique_constraint["column_names"][0] for unique_constraint in unique_constraints]

    def get_relationships(self, table_name):
        # type: (str) -> List[Any]
        model = self.get_class_by_table_name(table_name)
        insp = inspect(model)
        return insp.relationships

    def execute_text_query(self, sql_text):
        # type: (str) -> List[Dict[str, Any]]
        with self.manage_db_session() as session:
            result = session.execute(text(sql_text)).fetchall()
            result = [dict(record) for record in result]
            return result


    #Convert to sqlalchemy ORM
    def dump(self, sample=0, **kwargs):
        # type: (int, **Any) -> List[Dict[str, Any]]
        sql_text =  "SELECT *\n"
        sql_text += "FROM image\n"
        sql_text += "NATURAL LEFT JOIN location\n"
        sql_text += "NATURAL LEFT JOIN record\n"
        sql_text += "NATURAL LEFT JOIN image_subject\n"
        sql_text += "NATURAL LEFT JOIN record_subject\n"
        sql_text += "NATURAL LEFT JOIN subject\n"
        sql_text += "NATURAL LEFT JOIN record_topic\n"
        sql_text += "NATURAL LEFT JOIN topic\n"
        if sample != 0: sql_text += "LIMIT %i\n" % sample
        sql_text += ";"
        result = self.execute_text_query(sql_text)
        return result


    def load_columns(self, table, columns, **kwargs):
        # type: (str, List[str], **Any) -> DataFrame
        with self.manage_db_session() as session:
            model = self.get_class_by_table_name(table)
            result = session.query(model).all()
            pk = self.get_primary_keys(model=model)
            records = [record.__dict__ for record in result]
            df = pd.DataFrame(data=records)
            df.set_index(keys=pk, inplace=True, drop=False)
            df = df[columns]
            return df


    def get_remote_fk_name(self, input_table, output_table):
        # type: (str, str) -> str
        rs = self.get_relationships(output_table)
        input_model = self.get_class_by_table_name(input_table)
        for r in rs:
            if r.mapper.class_ == input_model:
                return list(r.remote_side)[0].description
        return None


    def save_record(self, input_table, output_table, output_map, data, **kwargs):
        # type: (str, str, Dict[str, str], DataFrame, **Any) -> None
        data.reset_index(drop=False, inplace=True)
        data.rename(columns=output_map, inplace=True)
        new_columns = list(output_map.values())
        data = data.where((pd.notnull(data)), None)
        data = data.astype('object')
        record = data.squeeze().to_dict()
        foreign_keys = defaultdict(list) # type: Dict[str, Any]
        remote_fk_value = None
        with self.manage_db_session() as session:
            db_object = self.merge_record(output_table, record, foreign_keys, **kwargs)
            if hasattr(db_object, "uuid"): remote_fk_value = db_object.uuid
        if input_table != output_table and remote_fk_value is not None:
            with self.manage_db_session() as session:
                local_fk_value = record["%s_uuid" % input_table]
                remote_fk_name = self.get_remote_fk_name(input_table, output_table)
                record = {"uuid": local_fk_value, remote_fk_name: remote_fk_value}
                self.merge_record(input_table, record, foreign_keys, **kwargs)


    def inspect_database(self):
        # type: () -> None
        with self.manage_db_session() as session:
            for table_name in self.base.metadata.tables.keys():
                model = self.get_class_by_table_name(table_name)
                num_records = session.query(func.count('*')).select_from(model).scalar()
                logger.info("Table: %s, Records: %s", table_name, num_records)


    def check_history(self, function_name, **kwargs):
        # type: (str, **Any) -> bool
        with self.manage_db_session() as session:
            model = self.get_class_by_table_name("augment_history")
            return session.query(model).filter(model.function_name == function_name).scalar()
    

    def add_to_history(self, function_name, **kwargs):
        # type: (str, **Any) -> None
        with self.manage_db_session() as session:
            model = self.get_class_by_table_name("augment_history")
            db_object = model(function_name=function_name)
            session.add(db_object)


##########################################################
# Main


def main():
    pass


if __name__ == "__main__":
    main()


##########################################################
