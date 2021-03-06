# -*- coding: utf-8 -*-
#!/usr/bin/env python
"""
"""
##########################################################
# Python Compatibility

from __future__ import print_function, division, absolute_import
from builtins import int
from future import standard_library
standard_library.install_aliases()

##########################################################
# Standard Library Imports

import datetime
import logging
import re

##########################################################
# Third Party Imports

import datefinder

##########################################################
# Local Imports

##########################################################
# Typing Configuration

from typing import Text, List, Optional, Any, Dict, AnyStr
Date = Any
Dates = Dict[AnyStr, Date]

##########################################################
# Constants


##########################################################
# Initializations

logger = logging.getLogger(__name__)

##########################################################
# Functions

def get_possible_dates(date_string):
    # type: (AnyStr) -> List[Date]
    try:
        dates = [dt.date() for dt in datefinder.find_dates(date_string)]
        dates[0]
    except:
        years = re.findall(".*([1-2][0-9]{3})", date_string)
        dates = [datetime.date(year=int(year), month=1, day=1) for year in years]
    max_date = datetime.datetime.now().date()
    min_date = datetime.date(year=1800,month=1,day=1)
    dates = [date for date in dates if date < max_date and date > min_date]
    return dates


def select_date(possible_dates, method="first"):
    # type: (List[Date], AnyStr) -> Optional[Date]
    if len(possible_dates) == 0: return None
    if method == "first": return possible_dates[0]
    elif method == "last": return possible_dates[-1]
    else: return None
    

def extract_date(date_text, method="first", **kwargs):
    # type: (AnyStr, AnyStr, **Any) -> Optional[Date]
    possible_dates = get_possible_dates(date_text)
    selected_date = select_date(possible_dates, method=method)
    return {"date": selected_date}


def extract_date_from_title(date_text, **kwargs):
    # type: (AnyStr, **Any) -> Optional[Date]
    try: date_text = " ".join(date_text.split(" ")[1:])
    except: pass
    extracted_date = extract_date(date_text, **kwargs).get("date", None)
    return {"date": extracted_date}

def combine_dates(fields, **kwargs):
    # type: (List[AnyStr], **Any) -> Optional[Date]
    date_created_raw = fields[0]
    date_created_approx_raw = fields[1]
    if date_created_raw: date_created = extract_date(date_created_raw).get("date", None)
    elif date_created_approx_raw: date_created = extract_date(date_created_approx_raw).get("date", None)
    else: date_created = None
    return {"date": date_created}


def split_dates(text, **kwargs):
    # type: (AnyStr, **Any) -> Dates
    if text is None: return {"start_date": None, "end_date": None}
    dates_num = len(text.split("-"))
    if dates_num >= 2:
        date_start_raw = text.split("-")[0]
        date_end_raw = text.split("-")[1]
        date_start = extract_date(date_start_raw).get("date", None)
        date_end = extract_date(date_end_raw).get("date", None)
    elif dates_num == 1:
        date_start_raw = text.split("-")[0]
        date_start = extract_date(date_start_raw).get("date", None)
        date_end = None
    return {"start_date": date_start, "end_date": date_end}


##########################################################
# Main


def main():
    pass


if __name__ == "__main__":
    main()


##########################################################
