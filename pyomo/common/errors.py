#  ___________________________________________________________________________
#
#  Pyomo: Python Optimization Modeling Objects
#  Copyright 2017 National Technology and Engineering Solutions of Sandia, LLC
#  Under the terms of Contract DE-NA0003525 with National Technology and 
#  Engineering Solutions of Sandia, LLC, the U.S. Government retains certain 
#  rights in this software.
#  This software is distributed under the 3-clause BSD License.
#  ___________________________________________________________________________


class PyomoException(Exception):
    pass


class DeveloperError(PyomoException, NotImplementedError):
    """
    Exception class used to throw errors that result from Pyomo
    programming errors, rather than user modeling errors (e.g., a
    component not declaring a 'ctype').
    """

    def __init__(self, val):
        self.parameter = val

    def __str__(self):
        return ( "Internal Pyomo implementation error:\n\t%s\n"
                 "\tPlease report this to the Pyomo Developers."
                 % ( repr(self.parameter), ) )


class InfeasibleConstraintException(PyomoException):
    """
    Exception class used by Pyomo transformations to indicate
    that an infeasible constraint has been identified (e.g. in
    the course of range reduction).
    """
    pass
