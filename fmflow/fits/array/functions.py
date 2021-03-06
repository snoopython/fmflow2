# coding: utf-8

# Python 3.x compatibility
from __future__ import absolute_import as _absolute_import
from __future__ import division as _division
from __future__ import print_function as _print_function

# the Python standard library
import os

# the Python Package Index¬
import numpy as np
import fmflow as fm
from astropy.io import fits

# imported items
__all__ = ['getarray']


def getarray(fitsname, arrayid, scantype):
    """Create a modulated fmarray from a FMFITS.

    Args:
        fitsname (str): File name of a FMFITS.
        arrayid (str): An array ID with which the output fmarray is created.
        scantype (str): A scan type with which the output fmarray is created.

    Returns:
        fmarray (FMArray): An output fmarray of the spacified array ID and scan type.

    """
    with fits.open(os.path.expanduser(fitsname)) as f:
        obsinfo = f['OBSINFO']
        fmlolog = f['FMLOLOG']
        backend = f['BACKEND']
        if 'ANTENNA' in f:
            antenna = f['ANTENNA']

        # flags
        flag_info = (obsinfo.data.ARRAYID == arrayid)
        flag_fmlo = (fmlolog.data.SCANTYPE == scantype)
        flag_be   = (backend.data.ARRAYID == arrayid) &\
                    (backend.data.SCANTYPE == scantype)

        t_fmlo = fmlolog.data.STARTTIME[flag_fmlo]
        t_be   = backend.data.STARTTIME[flag_be]

        # flags of time
        if 'ANTENNA' in f:
            t_ant = antenna.data.STARTTIME
            t_com = sorted(set(t_fmlo) & set(t_be) & set(t_ant))

            tflag_fmlo = np.in1d(t_fmlo, t_com)
            tflag_be   = np.in1d(t_be, t_com)
            tflag_ant  = np.in1d(t_ant, t_com)
        else:
            t_com = sorted(set(t_fmlo) & set(t_be))
            tflag_fmlo = np.in1d(t_fmlo, t_com)
            tflag_be   = np.in1d(t_be, t_com)

        # info
        keys = [name.lower() for name in obsinfo.data[flag_info].names]
        values = obsinfo.data[flag_info][0]

        info = dict(zip(keys, values))
        info['fitstype'] = obsinfo.header['FITSTYPE']
        info['telescop'] = obsinfo.header['TELESCOP']
        info['date-obs'] = obsinfo.header['DATE-OBS']
        info['observer'] = obsinfo.header['OBSERVER']
        info['object']   = obsinfo.header['OBJECT']
        info['ra']       = obsinfo.header['RA']
        info['dec']      = obsinfo.header['DEC']
        info['equinox']  = obsinfo.header['EQUINOX']

        # array
        if scantype != 'ON':
            array = np.squeeze(backend.data.ARRAYDATA[flag_be])
            return array
        else:
            array = np.squeeze(backend.data.ARRAYDATA[flag_be][tflag_be])

        # fmch, vrad
        fmfreq = fmlolog.data.FMFREQ[flag_fmlo][tflag_fmlo]
        fmch = (fmfreq / info['chanwidth']).astype(int)
        vrad = fmlolog.data.VRAD[flag_fmlo][tflag_fmlo]

        # coord (optional)
        if 'ANTENNA' in f:
            ra  = antenna.data.RA[tflag_ant]
            dec = antenna.data.DEC[tflag_ant]
            coord = np.vstack([ra, dec]).T
        else:
            coord = None

        # fmarray
        fmarray = fm.array(array, fmch, vrad, coord, info)
        return fmarray

