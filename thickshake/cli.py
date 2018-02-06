# -*- coding: utf-8 -*-
#!/usr/bin/env python
"""
"""
##########################################################
# Standard Library Imports

import configparser
import functools
import logging
import os

##########################################################
# Third Party Imports

import click
from click_help_colors import HelpColorsGroup, HelpColorsCommand
import click_log
from envparse import env

##########################################################
# Local Imports

from thickshake.utils import convert_file_type

##########################################################
# Typing Configuration

from typing import Any, Callable, Dict
FilePath = str 
DirPath = str

##########################################################
# Constants

CURRENT_FILE_DIR, _ = os.path.split(__file__)
CONFIG_DIR_PATH = "%s/_config" % CURRENT_FILE_DIR
CONFIG_SETTINGS_FILE = env.str("CONFIG_SETTINGS_FILE", default="%s/settings.ini" % (CONFIG_DIR_PATH))

##########################################################
# Classes


class MyParser(configparser.ConfigParser):
    def as_dict(self):
        # type: () -> Dict[str, Any]
        d = dict(self._sections)
        x = {} # type: Dict[str, Any]
        for k in d:
            d[k] = dict(self._defaults, **d[k])
            d[k].pop('__name__', None)
            x.update(d[k])
        return x


##########################################################
# Initializations

parser = MyParser()
parser.read(CONFIG_SETTINGS_FILE)
default_map = parser.as_dict()
context_settings = dict(default_map=default_map, ignore_unknown_options=True, allow_extra_args=True)
logger = logging.getLogger()

##########################################################
# Helpers

def common_params(func):
    # type: (Callable) -> Any
    @click.option("-f", "--force", is_flag=True, help="overwrite existing files")
    @click.option("-d", "--dry-run", is_flag=True, help="run without writing files")
    @click.option("-nm", "--no-import-metadata", is_flag=True, help="run without importing metadata")
    @click.option("-ni", "--no-import-images", is_flag=True, help="run without importing images")
    @click.option("-ne", "--no-export", is_flag=True, help="run without exporting")
    @click.option("-g", "--graphics", is_flag=True, help="display images in GUI")
    @click.option("-s", "--sample", type=int, default=0, help="perform on random sample (default: 0 / None)")
    @click_log.simple_verbosity_option(logger)
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # type: (*Any, **Any) -> Any
        return func(*args, **kwargs)
    return wrapper


@click.group(
    cls=HelpColorsGroup,
    help_headers_color='yellow',
    help_options_color='green',
    context_settings=context_settings,
)
def cli(**kwargs):
    # type: (**Any) -> None
    """Functions for improving library catalogues."""
    pass


##########################################################
# Functions


##########################################################
# Commands


@cli.command(context_settings=context_settings)
@common_params
def inspect(**kwargs):
    # type: (**Any) -> None
    """Inspects state of database."""
    from thickshake.storage import Database
    database = Database()
    database.inspect_database()


@cli.command(context_settings=context_settings)
@click.option("-i","--input-metadata-file", required=True, type=click.Path(exists=True, dir_okay=False))
@click.option("-o","--output-metadata-file", required=False, type=click.Path(dir_okay=False))
@click.option("-t","--output-metadata-type", required=False, type=click.Choice([".json", ".xml", ".marc"]), default=".marc", prompt='Output Types | Options: [.json, .xml, .marc] | Default:')
@common_params
def convert(input_metadata_file, output_metadata_file=None, output_metadata_type=None, **kwargs):
    # type: (FilePath, FilePath, str, **Any) -> None
    """Converts metadata between file formats."""
    from thickshake.marc import marc
    if output_metadata_type is not None:
        marc.convert_metadata(input_metadata_file, output_metadata_type=output_metadata_type, **kwargs)
    else: marc.convert_metadata(input_metadata_file, output_metadata_file=output_metadata_file, **kwargs)


@cli.command(context_settings=context_settings)
@click.option("-i", "--input-metadata-file", required=True, type=click.Path(exists=True, dir_okay=False))
@common_params
def load(input_metadata_file, **kwargs):
    # type: (FilePath, **Any) -> None
    """Imports metadata into database."""
    from thickshake.marc import marc
    marc.import_metadata(input_metadata_file, **kwargs)


##########################################################
# Export


@cli.group(context_settings=context_settings)
def export(**kwargs):
    # type: (**Any) -> None
    """Exports metadata from database."""


@export.command(name="marc", context_settings=context_settings)
@click.option("-o", "--output-metadata-file", required=False, type=click.Path(exists=False, dir_okay=False))
@click.option("-t","--output-metadata-type", required=False, type=click.Choice([".json", ".xml", ".marc"]), default=".marc", prompt='Output Types | Options: [.json, .xml, .marc] | Default:')
@click.option("-i", "--input-metadata-file", required=False, type=click.Path(exists=True, dir_okay=False))
@click.option("-p", "--partial", required=False, is_flag=True, help="output minimal fields to merge into catalogue")
@common_params
def export_marc(output_metadata_file, output_metadata_type, input_metadata_file, partial, **kwargs):
    # type: (FilePath, str, FilePath, bool, **Any) -> None
    """[WIP] Exports a marc file (for catalogues)."""
    assert output_metadata_file is not None or output_metadata_type is not None
    from thickshake.marc import marc
    if output_metadata_type is not None:
        output_metadata_file = convert_file_type(output_metadata_file, output_metadata_type)
    marc.export_metadata(output_metadata_file, input_metadata_file, partial=partial, **kwargs)


@export.command(name="dump", context_settings=context_settings)
@click.option("-o", "--output-dump-file", required=True, type=click.Path(exists=False, dir_okay=False))
@click.option("-t","--output-dump-type", required=False, type=click.Choice([".csv", ".json", ".hdf5"]), default=".csv", prompt='Output Types | Options: [.csv, .json, .hdf5] | Default:')
@common_params
def export_dump(output_dump_file, output_dump_type, **kwargs):
    # type: (FilePath, str, **Any) -> None
    """Exports a flat file (for other systems)."""
    assert output_dump_type is not None or output_dump_file is not None
    from thickshake.storage import writer
    if output_dump_type is not None:
        output_dump_file = convert_file_type(output_dump_file, output_dump_type)
    writer.export_flat_file(output_dump_file, **kwargs)


##########################################################
# Augment


@cli.group(context_settings=context_settings)
def augment(**kwargs):
    # type: (**Any) -> None
    """Applies functions to augment metadata."""


@augment.command(name="run_parsers", context_settings=context_settings)
@common_params
def augment_parsers(**kwargs):
    # type: (**Any) -> None
    """Runs all metadata parsing functions."""
    from thickshake.augment import augment
    augment.parse_locations(**kwargs)
    augment.parse_dates(**kwargs)
    augment.parse_links(**kwargs)
    augment.parse_sizes(**kwargs)


@augment.command(name="run_processors", context_settings=context_settings)
@click.option("-ii", "--input-image-dir", required=False, type=click.Path(exists=True, file_okay=False))
@click.option("-oi", "--output-image-dir", required=False, type=click.Path(exists=False, file_okay=False))
@common_params
def augment_processors(input_image_dir, output_image_dir, **kwargs):
    # type: (DirPath, DirPath, **Any) -> None
    """Runs all image processing functions."""
    from thickshake.augment import augment
    augment.detect_faces(input_image_dir, output_image_dir=output_image_dir, **kwargs)
    augment.identify_faces(input_image_dir, output_image_dir=output_image_dir, **kwargs)
    augment.read_text(input_image_dir, output_image_dir=output_image_dir, **kwargs)
    augment.caption_images(input_image_dir, output_image_dir=output_image_dir, **kwargs)


@augment.command(name="run_all", context_settings=context_settings)
@click.option("-ii", "--input-image-dir", required=False, type=click.Path(exists=True, file_okay=False))
@click.option("-oi", "--output-image-dir", required=False, type=click.Path(exists=False, file_okay=False))
@common_params
def augment_all(input_image_dir, output_image_dir, **kwargs):
    # type: (DirPath, DirPath, **Any) -> None
    """Runs all augment functions."""
    from thickshake.augment import augment
    augment.parse_locations(**kwargs)
    augment.parse_dates(**kwargs)
    augment.parse_links(**kwargs)
    augment.parse_sizes(**kwargs)
    augment.detect_faces(input_image_dir, output_image_dir=output_image_dir, **kwargs)
    augment.identify_faces(input_image_dir, output_image_dir=output_image_dir, **kwargs)
    augment.read_text(input_image_dir, output_image_dir=output_image_dir, **kwargs)
    augment.caption_images(input_image_dir, output_image_dir=output_image_dir, **kwargs)


@augment.command(context_settings=context_settings)
@click.option("-ii", "--input-image-dir", required=False, type=click.Path(exists=True, file_okay=False))
@click.option("-oi", "--output-image-dir", required=False, type=click.Path(exists=False, file_okay=False))
@common_params
def detect_faces(input_image_dir, output_image_dir, **kwargs):
    # type: (DirPath, DirPath, **Any) -> None
    """[WIP] Detects faces in images."""
    from thickshake.augment import augment
    augment.detect_faces(input_image_dir, output_image_dir=output_image_dir, **kwargs)


@augment.command(context_settings=context_settings)
@click.option("-ii", "--input-image-dir", required=False, type=click.Path(exists=True, file_okay=False))
@click.option("-oi", "--output-image-dir", required=False, type=click.Path(exists=False, file_okay=False))
@common_params
def identify_faces(input_image_dir, output_image_dir, **kwargs):
    # type: (DirPath, DirPath, **Any) -> None
    """[WIP] Identifies faces in images."""
    from thickshake.augment import augment
    augment.identify_faces(input_image_dir, output_image_dir=output_image_dir, **kwargs)


@augment.command(context_settings=context_settings)
@click.option("-ii", "--input-image-dir", required=False, type=click.Path(exists=True, file_okay=False))
@click.option("-oi", "--output-image-dir", required=False, type=click.Path(exists=False, file_okay=False))
@common_params
def read_text(input_image_dir, output_image_dir, **kwargs):
    # type: (DirPath, DirPath, **Any) -> None
    """[TODO] Reads text embedded in images."""
    from thickshake.augment import augment
    augment.read_text(input_image_dir, output_image_dir=output_image_dir, **kwargs)


@augment.command(context_settings=context_settings)
@click.option("-ii", "--input-image-dir", required=False, type=click.Path(exists=True, file_okay=False))
@click.option("-oi", "--output-image-dir", required=False, type=click.Path(exists=False, file_okay=False))
@common_params
def caption_images(input_image_dir, output_image_dir, **kwargs):
    # type: (DirPath, DirPath, **Any) -> None
    """[TODO] Automatically captions images."""
    from thickshake.augment import augment
    augment.caption_images(input_image_dir, output_image_dir=output_image_dir, **kwargs)


@augment.command(context_settings=context_settings)
@common_params
def parse_locations(**kwargs):
    # type: (**Any) -> None
    """Parses locations from text fields."""
    from thickshake.augment import augment
    augment.parse_locations(**kwargs)


@augment.command(context_settings=context_settings)
@common_params
def parse_dates(**kwargs):
    # type: (**Any) -> None
    """Parses dates from text fields."""
    from thickshake.augment import augment
    augment.parse_dates(**kwargs)


@augment.command(context_settings=context_settings)
@common_params
def parse_links(**kwargs):
    # type: (**Any) -> None
    """Parses links from text fields."""
    from thickshake.augment import augment
    augment.parse_links(**kwargs)


@augment.command(context_settings=context_settings)
@common_params
def parse_sizes(**kwargs):
    # type: (**Any) -> None
    """Parses image sizes from urls."""
    from thickshake.augment import augment
    augment.parse_sizes(**kwargs)


##########################################################
