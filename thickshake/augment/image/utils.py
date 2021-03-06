# -*- coding: utf-8 -*-
#!/usr/bin/env python
"""
"""
##########################################################
# Python Compatibility

from __future__ import print_function, division, absolute_import
from future import standard_library
standard_library.install_aliases()

##########################################################
# Standard Library Imports

import logging
import os

##########################################################
# Third Party Imports

import cv2

##########################################################
# Local Imports

from thickshake.utils import maybe_increment_path, maybe_make_directory, generate_output_path

##########################################################
# Typing Configuration

from typing import Text, Any, Optional, List, AnyStr
ImageType = Any
Rectangle = Any
FilePath = Text 
DirPath = Text

##########################################################
# Constants


##########################################################
# Initialization

logger = logging.getLogger(__name__)

##########################################################
# Functions


def rect_to_bb(rect):
    # type: (Rectangle) -> List[float]
	x = rect.left()
	y = rect.top()
	w = rect.right() - x
	h = rect.bottom() - y
	return [x, y, w, h]


def crop(image, box, bleed):
    # type: (ImageType, List[float], float) -> ImageType
    return image.crop((
        box[0] - bleed,
        box[1] - bleed,
        box[0] + box[2] + bleed,
        box[1] + box[3] + bleed
    ))


def show_image(image_rgb):
    # type: (ImageType) -> None
    from matplotlib import pyplot as plt
    plt.imshow(image_rgb)
    plt.show()


def enhance_image(image):
    # type: (ImageType) -> ImageType
    image_YCrCb = cv2.cvtColor(image, cv2.COLOR_BGR2YCR_CB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    channels = [clahe.apply(channel) for channel in cv2.split(image_YCrCb)]
    image = cv2.merge(channels)
    image = cv2.cvtColor(image_YCrCb, cv2.COLOR_YCR_CB2BGR)
    return image


def save_image(image_rgb, sub_folder=None, output_file=None, input_file=None, output_image_dir=None, **kwargs):
    # type: (ImageType, AnyStr, FilePath, FilePath, DirPath, **Any) -> FilePath
    if output_file is None and (input_file is not None and output_image_dir is not None):
        output_file = generate_output_path(input_file, output_dir=output_image_dir, sub_folder=sub_folder)  
    output_file = maybe_increment_path(output_file, **kwargs)
    maybe_make_directory(output_file)
    image_bgr = cv2.cvtColor(image_rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(output_file, image_bgr)
    return output_file


def handle_image(image, input_file, graphics=False, dry_run=False, **kwargs):
    # type: (ImageType, FilePath, bool, bool, **Any) -> None
    if graphics: show_image(image)
    if not dry_run: save_image(image, input_file=input_file, **kwargs)


def get_image(image_file):
    # type: (FilePath) -> ImageType
    image_bgr = cv2.imread(image_file)
    image_bgr = enhance_image(image_bgr)
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    return image_rgb


##########################################################


def main():
    process_images()


if __name__ == "__main__":
    main()


##########################################################
