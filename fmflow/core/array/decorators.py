# coding: utf-8

"""Module for decorators of fmarray functions.

"""

# Python 3.x compatibility
from __future__ import absolute_import as _absolute_import
from __future__ import division as _division
from __future__ import print_function as _print_function

# the Python standard library
from functools import partial, wraps
from inspect import getargspec

# the Python Package Index
import numpy as np
import fmflow as fm

# imported items
__all__ = ['arrayfunc', 'numchunk', 'timechunk']


def arrayfunc(func):
    """Make a function compatible with fmarray.

    This function is used as a decorator like::

        >>> @fm.arrayfunc
        >>> def func(fmarray):
        ...     return fmarray # do nothing
        >>>
        >>> result = func(fmarray)

    Args:
        func (function): A function to be wrapped.
            The first argument of the function must be `fmarray`.

    Returns:
        wrapper (function): A wrapped function.

    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        fmarray_in  = kwargs.pop('fmarray', args[0])
        fmarray_out = fmarray_in.copy()

        if type(fmarray_in) == fm.FMArray:
            array_in = fmarray_in.toarray()
        else:
            array_in = np.asarray(fmarray_in)

        array_out = func(array_in, *args[1:], **kwargs)
        fmarray_out[:] = array_out
        return fmarray_out

    return wrapper


def numrchunk(func):
    """Make a function compatible with multicore numchunk processing.

    This function is used as a decorator like::

        >>> @fm.arrayfunc
        >>> @fm.numchunk
        >>> def func(fmarray):
        ...     return fmarray # do nothing
        >>>
        >>> result = func(fmarray, numchunk=10)

    Args:
        func (function): A function to be wrapped. The first argument
            of the function must be fmarray to be numchunked.

    Returns:
        wrapper (function): A wrapped function.

    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        array_in = args[0]

        p = fm.utils.Pool()
        N = kwargs.pop('numchunk', p.processes)

        argnames = getargspec(func).args
        if len(args) > 1:
            for i in range(1, len(args)):
                kwargs[argnames[i]] = args[i]

        indxs = np.linspace(0, len(array_in), N+1, dtype=int)
        subarrays_in = [array_in[indxs[i]:indxs[i+1]] for i in range(N)]

        pfunc = partial(func, **kwargs)
        subarrays_out = p.map(pfunc, subarrays_in)
        array_out = np.concatenate(subarrays_out)
        return array_out

    return wrapper


def timechunk(func):
    """Make a function compatible with multicore timechunk processing.

    This function is used as a decorator like::

        >>> @fm.arrayfunc
        >>> @fm.timechunk
        >>> def func(fmarray):
        ...     return fmarray # do nothing
        >>>
        >>> result = func(fmarray, timechunk=100)

    Args:
        func (function): A function to be wrapped. The first argument
            of the function must be fmarray to be timechunked.

    Returns:
        wrapper (function): A wrapped function.

    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        array_in = args[0]

        p = fm.utils.Pool()
        T = kwargs.pop('timechunk', len(array_in))
        N = round(len(array_in) / T)

        argnames = getargspec(func).args
        if len(args) > 1:
            for i in range(1, len(args)):
                kwargs[argnames[i]] = args[i]

        indxs = np.linspace(0, len(array_in), N+1, dtype=int)
        subarrays_in = [array_in[indxs[i]:indxs[i+1]] for i in range(N)]

        pfunc = partial(func, **kwargs)
        subarrays_out = p.map(pfunc, subarrays_in)
        array_out = np.concatenate(subarrays_out)
        return array_out

    return wrapper

