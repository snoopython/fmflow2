# coding: utf-8

# Python 3.x compatibility
from __future__ import absolute_import as _absolute_import
from __future__ import division as _division
from __future__ import print_function as _print_function

# the Python standard library
import json
import os
import re

# the Python Package Index
import yaml
import numpy as np
import fmflow as fm
from astropy import units as u
from astropy import constants as consts
from astropy.io import fits
from astropy.coordinates import Angle

# imported items
__all__ = ['fromnro45m']

# constants
C           = consts.c.value # spped of light in vacuum
D_NRO45m    = (45.0 * u.m).value # diameter of the NRO45m
LAT_NRO45m  = Angle('+35d56m40.9s').deg # latitude of the NRO45m
EFF_8257D   = 0.92 # exposure / interval time of Agilent 8257D
DIR_MODULE  = os.path.dirname(os.path.realpath(__file__)) # module directory
IGNORED_KEY = '^reserve' # reserved[1|4|8]


def fromnro45m(fmlolog, backendlog, antennalog=None, byteorder='<'):
    """Read logging data of NRO45m and merge them into a FITS object.

    Args:
        fmlolog (str): File name of FMLO logging.
        backendlog (str): File name of backend logging.
        antennalog (str): File name of antenna logging (optional).
        byteorder (str): format string that represents byte order
            of the backendlog. Default is '<' (little-endian).
            If the data in the returned FITS seems to be wrong,
            try to spacify '>' (big-endian).

    Returns:
        fitsobj (HDUlist): HDU list containing the merged data.

    See Also:
        https://docs.python.org/2/library/struct.html
    """
    # HDU list
    fitsobj = fits.HDUList()

    # PRIMARY HDU
    hdu = fits.PrimaryHDU()
    fitsobj.append(hdu)

    # FMLOINFO HDU
    hdu = _read_fmlolog(fmlolog)
    fitsobj.append(hdu)

    # BACKEND HDU
    backend = _check_backend(backendlog, byteorder)

    if backend == 'SAM45':
        hdu = _read_backendlog_sam45(backendlog, byteorder)
    else:
        raise fm.utils.FMFlowError('invalid logging type')

    fitsobj.append(hdu)

    # ANTENNA HDU
    if antennalog is not None:
        hdu = _read_antennalog(antennalog)
        fitsobj.append(hdu)

    # OBSINFO HDU
    hdu = _make_obsinfo(fitsobj)
    fitsobj.insert(1, hdu)

    return fitsobj


def _read_fmlolog(fmlolog):
    """Read a FMLO logging of NRO45m.

    Args:
        fmlolog (str): File name of FMLO logging.

    Returns:
        hdu (BinTableHDU): HDU containing the read FMLO logging.

    """
    # datetime converter
    p = fm.utils.DatetimeParser()
    starttime = np.loadtxt(fmlolog, str, usecols=(0,), skiprows=1, converters={0: p})
    scantype  = np.loadtxt(fmlolog, str, usecols=(1,), skiprows=1)
    fmfreq    = np.loadtxt(fmlolog, float, usecols=(2,), skiprows=1)
    lofreq    = np.loadtxt(fmlolog, float, usecols=(3,), skiprows=1)
    vrad      = np.loadtxt(fmlolog, float, usecols=(4,), skiprows=1)

    # fmflag
    fmflag = (scantype == 'ON')

    # bintable HDU
    header = fits.Header()
    header['EXTNAME'] = 'FMLOLOG'
    header['FILENAME'] = fmlolog

    columns = []
    columns.append(fits.Column('STARTTIME', 'A26', 'ISO 8601', array=starttime))
    columns.append(fits.Column('SCANTYPE',  'A4', '', array=scantype))
    columns.append(fits.Column('FMFLAG', 'L', 'bool', array=fmflag))
    columns.append(fits.Column('FMFREQ', 'D', 'Hz', array=fmfreq))
    columns.append(fits.Column('LOFREQ', 'D', 'Hz', array=lofreq))
    columns.append(fits.Column('VRAD', 'D', 'm/s', array=vrad))

    hdu = fits.BinTableHDU.from_columns(columns, header)
    return hdu


def _read_antennalog(antennalog):
    """Read an antenna logging of NRO45m.

    Args:
        antennalog (str): File name of antenna logging.

    Returns:
        hdu (BinTableHDU): HDU containing the read antenna logging.

    """
    # datetime converter
    p = fm.utils.DatetimeParser()
    starttime = np.loadtxt(antennalog, str, usecols=(0,), skiprows=1, converters={0: p})
    ra_prog   = np.loadtxt(antennalog, float, usecols=(1,), skiprows=1)
    dec_prog  = np.loadtxt(antennalog, float, usecols=(2,), skiprows=1)
    az_prog   = np.loadtxt(antennalog, float, usecols=(3,), skiprows=1)
    el_prog   = np.loadtxt(antennalog, float, usecols=(4,), skiprows=1)
    az_real   = np.loadtxt(antennalog, float, usecols=(5,), skiprows=1)
    el_real   = np.loadtxt(antennalog, float, usecols=(6,), skiprows=1)
    az_error  = np.loadtxt(antennalog, float, usecols=(7,), skiprows=1)
    el_error  = np.loadtxt(antennalog, float, usecols=(8,), skiprows=1)

    # RA,Dec real
    degsin = lambda deg: np.sin(np.deg2rad(deg))
    degcos = lambda deg: np.cos(np.deg2rad(deg))
    q = -np.arcsin(degsin(az_prog)*degcos(LAT_NRO45m)/degcos(dec_prog))

    ra_error  = -np.cos(q)*az_error + np.sin(q)*el_error
    dec_error = np.sin(q)*az_error + np.cos(q)*el_error
    ra_real   = ra_prog - ra_error
    dec_real  = dec_prog - ra_error

    # bintable HDU
    header = fits.Header()
    header['EXTNAME'] = 'ANTENNA'
    header['FILENAME'] = antennalog

    columns = []
    columns.append(fits.Column('STARTTIME', 'A26', 'ISO 8601', array=starttime))
    columns.append(fits.Column('RA', 'D', 'deg', array=ra_real))
    columns.append(fits.Column('DEC', 'D', 'deg', array=dec_real))
    columns.append(fits.Column('AZ', 'D', 'deg', array=az_real))
    columns.append(fits.Column('EL', 'D', 'deg', array=el_real))
    columns.append(fits.Column('RA_PROG', 'D', 'deg', array=ra_prog))
    columns.append(fits.Column('DEC_PROG', 'D', 'deg', array=dec_prog))
    columns.append(fits.Column('AZ_PROG', 'D', 'deg', array=az_prog))
    columns.append(fits.Column('EL_PROG', 'D', 'deg', array=el_prog))
    columns.append(fits.Column('RA_ERROR', 'D', 'deg', array=ra_error))
    columns.append(fits.Column('DEC_ERROR', 'D', 'deg', array=dec_error))
    columns.append(fits.Column('AZ_ERROR', 'D', 'deg', array=az_error))
    columns.append(fits.Column('EL_ERROR', 'D', 'deg', array=el_error))

    hdu = fits.BinTableHDU.from_columns(columns, header)
    return hdu


def _check_backend(backendlog, byteorder):
    """Check backend type from a backend logging of NRO45m.

    Args:
        backendlog (str): File name of backend logging.
        byteorder (str): format string that represents byte order
            of the backendlog. Default is '<' (little-endian).
            If the data in the returned FITS seems to be wrong,
            try to spacify '>' (big-endian).

    Returns:
        backend (str): Backend type.

    """
    with open(os.path.join(DIR_MODULE, 'struct_common.yaml')) as f:
        d = yaml.load(f)
        head = fm.utils.CStructReader(d['head'], IGNORED_KEY, byteorder)
        ctl  = fm.utils.CStructReader(d['ctl'], IGNORED_KEY, byteorder)

    with open(backendlog, 'rb') as f:
        head.read(f)
        ctl.read(f)
        backend = ctl.data['cbe_type']

    return backend


def _read_backendlog_sam45(backendlog, byteorder):
    """Read a backend logging of NRO45m/SAM45.

    Args:
        backendlog (str): File name of backend logging.
        byteorder (str): format string that represents byte order
            of the backendlog. Default is '<' (little-endian).
            If the data in the returned FITS seems to be wrong,
            try to spacify '>' (big-endian).

    Returns:
        hdu (BinTableHDU): HDU containing the read backend logging.

    """
    with open(os.path.join(DIR_MODULE, 'struct_common.yaml')) as f:
        d = yaml.load(f)
        head = fm.utils.CStructReader(d['head'], IGNORED_KEY, byteorder)
        ctl  = fm.utils.CStructReader(d['ctl'], IGNORED_KEY, byteorder)

    with open(os.path.join(DIR_MODULE, 'struct_sam45.yaml')) as f:
        d = yaml.load(f)
        obs = fm.utils.CStructReader(d['obs'], IGNORED_KEY, byteorder)
        dat = fm.utils.CStructReader(d['dat'], IGNORED_KEY, byteorder)

    def eof(f):
        head.read(f)
        flag = head._data['crec_type'][-1][0]
        return (flag == 'ED')

    # read data
    fsize = os.path.getsize(backendlog)

    with open(backendlog, 'rb') as f:
        ## control info
        eof(f)
        ctl.read(f)

        ## observation info
        eof(f)
        obs.read(f)

        ## data info
        i = 0
        while not eof(f):
            if not i%100:
                frac = f.tell() / fsize
                fm.utils.progressbar(frac)

            dat.read(f)
            i += 1

    # edit data
    data = dat.data
    data['STARTTIME'] = data.pop('cint_sttm')
    data['ARRAYID']   = data.pop('cary_name')
    data['SCANTYPE']  = data.pop('cscan_type')
    data['ARRAYDATA'] = data.pop('fary_data')

    ## starttime
    p = fm.utils.DatetimeParser()
    data['STARTTIME'] = np.array([p(t) for t in data['STARTTIME']])

    ## scantype (bug?)
    data['SCANTYPE'][data['SCANTYPE']=='R\x00RO'] = 'R'

    ## arraydata
    usefg    = np.array(obs.data['iary_usefg'], dtype=bool)
    ifatt    = np.array(obs.data['iary_ifatt'], dtype=float)[usefg]
    islsb    = np.array(obs.data['csid_type'] == 'LSB')[usefg]
    arrayids = np.unique(data['ARRAYID'])

    for i, arrayid in enumerate(arrayids):
        flag = (data['ARRAYID'] == arrayid)

        ## slices of each scantype
        ons  = fm.utils.slicewhere(flag & (data['SCANTYPE'] == 'ON'))
        rs   = fm.utils.slicewhere(flag & (data['SCANTYPE'] == 'R'))
        skys = fm.utils.slicewhere(flag & (data['SCANTYPE'] == 'SKY'))
        zero = fm.utils.slicewhere(flag & (data['SCANTYPE'] == 'ZERO'))[0]

        ## apply ZERO to ON data
        for on in ons:
            data['ARRAYDATA'][on] -= data['ARRAYDATA'][zero]

        ## apply ZERO and ifatt to R data
        for r in rs:
            data['ARRAYDATA'][r] -= data['ARRAYDATA'][zero]
            data['ARRAYDATA'][r] *= 10.0**(ifatt[i]/10.0)

        ## apply ZERO to SKY data
        for sky in skys:
            data['ARRAYDATA'][sky] -= data['ARRAYDATA'][zero]

        ## reverse array (if LSB)
        if arrayid in arrayids[islsb]:
            data['ARRAYDATA'][flag] = data['ARRAYDATA'][flag,::-1]

    # read and edit formats
    fmts = dat.fitsformats
    fmts['STARTTIME'] = fmts.pop('cint_sttm')
    fmts['ARRAYID']   = fmts.pop('cary_name')
    fmts['SCANTYPE']  = fmts.pop('cscan_type')
    fmts['ARRAYDATA'] = fmts.pop('fary_data')
    fmts['STARTTIME'] = 'A26' # YYYY-mm-ddTHH:MM:SS.ssssss

    # bintable HDU
    header = fits.Header()
    header['EXTNAME'] = 'BACKEND'
    header['FILENAME'] = backendlog
    header['CTLINFO'] = ctl.jsondata
    header['OBSINFO'] = obs.jsondata

    columns = []
    for key in data:
        columns.append(fits.Column(key, fmts[key], array=data[key]))

    hdu = fits.BinTableHDU.from_columns(columns, header)
    return hdu


def _make_obsinfo(fitsobj):
    """Make a OBSINFO HDU from FITS object.

    Args:
        fitsobj (HDUList): FITS object containing FMLOINFO, BACKEND HDUs.

    Returns:
        hdu (BinTableHDU): OBSINFO HDU containing the formatted observational info.

    """
    ctlinfo = json.loads(fitsobj['BACKEND'].header['CTLINFO'])
    obsinfo = json.loads(fitsobj['BACKEND'].header['OBSINFO'])
    datinfo = fitsobj['BACKEND'].data

    # bintable HDU header
    p = fm.utils.DatetimeParser()

    header = fits.Header()
    header['EXTNAME']  = 'OBSINFO'
    header['FITSTYPE'] = 'FMFITS{}'.format(fm.__version__)
    header['TELESCOP'] = 'NRO45m'
    header['DATE-OBS'] = p(obsinfo['clog_id'])[:-3]
    header['OBSERVER'] = obsinfo['cobs_user']
    header['OBJECT']   = obsinfo['cobj_name']
    header['RA']       = obsinfo['dsrc_pos'][0][0]
    header['DEC']      = obsinfo['dsrc_pos'][1][0]
    header['EQUINOX']  = float(re.findall('\d+', obsinfo['cepoch'])[0])

    # bintable HDU data
    N = obsinfo['iary_num']
    flag = np.array(obsinfo['iary_usefg'], dtype=bool)

    arrayid   = np.unique(datinfo['ARRAYID'])
    sideband  = np.array(obsinfo['csid_type'])[flag]
    restfreq  = np.array(obsinfo['dcent_freq'])[flag]
    intmfreq  = np.array(obsinfo['dflif'])[flag]
    beamsize  = np.rad2deg(1.2*C/D_NRO45m) / restfreq
    bandwidth = np.array(obsinfo['dbebw'])[flag]
    chanwidth = np.array(obsinfo['dbechwid'])[flag]
    interval  = np.tile(obsinfo['diptim'], N)
    integtime = np.tile(obsinfo['diptim']*EFF_8257D, N)
    frontend  = np.array(obsinfo['cfe_type'])[flag]
    backend   = np.tile(ctlinfo['cbe_type'], N)

    if backend[0] == 'SAM45':
        numofchan = np.array(obsinfo['ichannel'])[flag]
    else:
        raise fm.utils.FMFlowError('invalid logging type')

    columns = []
    columns.append(fits.Column('ARRAYID', 'A4', '', array=arrayid))
    columns.append(fits.Column('SIDEBAND', 'A4', '', array=sideband))
    columns.append(fits.Column('RESTFREQ', 'D', 'Hz', array=restfreq))
    columns.append(fits.Column('INTMFREQ', 'D', 'Hz', array=intmfreq))
    columns.append(fits.Column('BEAMSIZE', 'D', 'deg', array=beamsize))
    columns.append(fits.Column('BANDWIDTH', 'D', 'Hz', array=bandwidth))
    columns.append(fits.Column('CHANWIDTH', 'D', 'Hz', array=chanwidth))
    columns.append(fits.Column('NUMOFCHAN', 'J', 'ch', array=numofchan))
    columns.append(fits.Column('INTERVAL', 'D', 's', array=interval))
    columns.append(fits.Column('INTEGTIME', 'D', 's', array=integtime))
    columns.append(fits.Column('FRONTEND', 'A10', '', array=frontend))
    columns.append(fits.Column('BACKEND', 'A8', '', array=backend))

    hdu = fits.BinTableHDU.from_columns(columns, header)
    return hdu

