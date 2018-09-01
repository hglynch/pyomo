#  ___________________________________________________________________________
#
#  Pyomo: Python Optimization Modeling Objects
#  Copyright 2017 National Technology and Engineering Solutions of Sandia, LLC
#  Under the terms of Contract DE-NA0003525 with National Technology and
#  Engineering Solutions of Sandia, LLC, the U.S. Government retains certain
#  rights in this software.
#  This software is distributed under the 3-clause BSD License.
#  ___________________________________________________________________________

import os
import six

_default_env_vars = ['LD_LIBRARY_PATH','PATH']

def find_file(fname, cwd=True, mode=os.R_OK, ext=None, pathlist=[]):
    """Locate a file, given a set of search parameters

    Arguments
    ---------
    fname (str): the file name to locate

    cwd (bool): start by looking in the current working directory
        (default: True)

    mode (mask): if not None, only return files that can be accessed for
        reading/writing/executing.  Valid values are the inclusive OR of
        {os.R_OK, os.W_OK, os.X_OK} (default: os.R_OK)

    ext (str): if not None, also look for fname+ext (default: None)

    pathlist (list): a list of strings containing paths to search.  Each
        string contains one or more paths separated by
        os.pathsep. (default: [])

    """ % ( _default_env_vars, )

    locations = []
    if cwd:
        locations.append(os.getcwd())
    for pathspec in pathlist:
        locations.extend(pathspec.split(os.pathsep))

    extlist = ['']
    if ext:
        if isinstence(ext, six.string_types):
            extlist.append(ext)
        else:
            extlist.extend(ext)

    for path in locations:
        if not path:
            continue
        for ext in extlist:
            test = os.path.join(path, fname+ext)
            if not os.path.isfile(test):
                continue
            if mode is not None and not os.access(test, mode):
                continue
            return test
    return None

_exeExt = {
    'linux':   None,
    'windows': '.exe',
    'cygwin':  '.exe',
    'darwin':  None,
}

_libExt = {
    'linux':   '.so',
    'windows': '.dll',
    'cygwin':  ['.dll','.so'],
    'darwin':  '.dynlib',
}

def _system():
    system = platform.system().lower()
    for c in '.-_':
        system = system.split(c)[0]
    return system

def find_library(libname, cwd=True, include_PATH=True, pathlist=None):
    if pathlist is None:
        pathlist = [ os.environ.get('LD_LIBRARY_PATH','') ]
    elif isinstance(pathlist, six.string_types):
        pathlist = [pathlist]
    else:
        pathlist = list(pathlist)
    if include_PATH:
        pathlist.append( os.environ.get('PATH','') or os.defpath )
    ext = _libExt.get(_system(), None)
    return find_file(libname, cwd=cwd, ext=ext, pathlist=pathlist)

def find_executable(exename, cwd=True, include_PATH=True, pathlist=None):
    if pathlist is None:
        pathlist = []
    elif isinstance(pathlist, six.string_types):
        pathlist = [pathlist]
    else:
        pathlist = list(pathlist)
    if include_PATH:
        pathlist.append( os.environ.get('PATH','') or os.defpath )
    ext = _exeExt.get(_system(), None)
    return find_file(exename, cwd=cwd, ext=ext, mode=os.R_OK|os.X_OK,
                     pathlist=pathlist)
