# coding: utf-8

# Python 3.x compatibility
from __future__ import absolute_import as __absolute_import
from __future__ import division as __division
from __future__ import print_function as __print_function

# the Python Standard Library
from collections import defaultdict
from copy import deepcopy

# the Python Package Index
import numpy as np
from sklearn import decomposition
from fmflow import utils as ut

# FMFlow submodules
from .._array import *

# imported items
__all__ = ['reducedim']

# constants
PARAMS = defaultdict(dict)
PARAMS['KernelPCA'] = {'fit_inverse_transform': True}


@fmfunc
@timechunk
def reducedim(fmarray, algorithm='TruncatedSVD', **kwargs):
    """Compute a dimension-reduced fmarray via a decomposition algorithm.

    Args:
        fmarray (FMArray): An input fmarray.
        algorithm (str): A name of decomposition algorithm
            which sklearn.decomposition provides.
        kwargs (dict): Parameters for the spacified algorithm such as `n_components`.

    Returns:
        result (FMArray): An output dimension-reduced fmarray.

    Example:
        To compute a fmarray reconstructed from top two principal components:

        >>> result = fm.reduce(fmarray, 'PCA', n_components=2)

    """
    AlgorithmClass = getattr(decomposition, algorithm)
    params = deepcopy(PARAMS[algorithm])
    params.update(kwargs)

    model = AlgorithmClass(**params)
    fit = model.fit_transform(fmarray)
    
    if hasattr(model, 'inverse_transform'):
        result = model.inverse_transform(fit)
    elif hasattr(model, 'components_'):
        result = np.dot(fit, model.components_)
    else:
        raise ut.FMFlowError('cannot decompose with the spacified algorithm')

    return result

