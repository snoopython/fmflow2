# coding: utf-8

# Python 3.x compatibility
from __future__ import absolute_import as _absolute_import
from __future__ import division as _division
from __future__ import print_function as _print_function

# the Python Package Index
import numpy as np
from scipy import ndimage

# imported items
__all__ = ['slicewhere']


def slicewhere(condition):
    """Return slices of regions that fulfill condition.

    Args:
        condition (list of bool): An array of booleans.

    Returns:
        slices (list of slice): List of slice objects.

    Example:
        >>> cond = [False, True, True, False, False, True, False]
        >>> fm.utils.slicewhere(cond)
        [slice(1L, 3L, None), slice(5L, 6L, None)]

    """
    regions = ndimage.find_objects(ndimage.label(condition)[0])
    slices = [region[0] for region in regions]
    return slices

