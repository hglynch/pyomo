#  ___________________________________________________________________________
#
#  Pyomo: Python Optimization Modeling Objects
#  Copyright 2017 National Technology and Engineering Solutions of Sandia, LLC
#  Under the terms of Contract DE-NA0003525 with National Technology and 
#  Engineering Solutions of Sandia, LLC, the U.S. Government retains certain 
#  rights in this software.
#  This software is distributed under the 3-clause BSD License.
#  ___________________________________________________________________________

from pyomo.contrib.gdpopt.create_oa_subproblems import (
    _get_master_and_subproblem)
from pyomo.contrib.gdpopt.oa_algorithm_utils import (
    _fix_master_soln_solve_subproblem_and_add_cuts)
from pyomo.contrib.gdpopt.mip_solve import solve_linear_GDP
from pyomo.contrib.gdpopt.nlp_solve import solve_subproblem
from pyomo.contrib.gdpopt.util import time_code, lower_logger_level_to
from pyomo.contrib.gdpopt.algorithm_base_class import _GDPoptAlgorithm
from pyomo.contrib.gdpopt.config_options import (
    _add_OA_configs, _add_mip_solver_configs, _add_nlp_solver_configs, 
    _add_tolerance_configs)
from pyomo.contrib.gdpopt.cut_generation import (
    add_outer_approximation_cuts, add_no_good_cut)

from pyomo.core import Block, Objective, minimize, Var, value
from pyomo.opt.base import SolverFactory
from pyomo.opt import TerminationCondition
from pyomo.gdp import Disjunct
import logging

@SolverFactory.register(
    '_logic_based_oa',
    doc='GDP Logic-Based Outer Approximation (LOA) solver')
class GDP_LOA_Solver(_GDPoptAlgorithm):
    CONFIG = _GDPoptAlgorithm.CONFIG()
    _add_OA_configs(CONFIG)
    _add_mip_solver_configs(CONFIG)
    _add_nlp_solver_configs(CONFIG)
    _add_tolerance_configs(CONFIG)

    def __init__(self, **kwds):
        self.CONFIG = self.CONFIG(kwds)
        super(GDP_LOA_Solver, self).__init__()

    def solve(self, model, **kwds):
        config = self.CONFIG(kwds.pop('options', {}), preserve_implicit=True)
        config.set_value(kwds)
        
        super().solve(model, config)
        min_logging_level = logging.INFO if config.tee else None
        with time_code(self.timing, 'total', is_main_timer=True), \
            lower_logger_level_to(config.logger, min_logging_level):
            return self._solve_gdp_with_loa(model, config)

    def _solve_gdp_with_loa(self, original_model, config):
        logger = config.logger

        (master_util_block,
         subproblem_util_block) = _get_master_and_subproblem(
             original_model, config, self, constraint_list=True)

        master = master_util_block.model()
        subproblem = subproblem_util_block.model()

        original_obj = self._setup_augmented_Lagrangian_objective(
            master_util_block)

        # main loop
        while self.master_iteration < config.iterlim:
            # Set iteration counters for new master iteration.
            self.master_iteration += 1
            self.mip_iteration = 0
            self.nlp_iteration = 0

            # print line for visual display
            logger.info('---GDPopt Master Iteration %s---' % 
                        self.master_iteration)

            # solve linear master problem
            with time_code(self.timing, 'mip'):
                oa_obj = self._update_augmented_Lagrangian_objective(
                    master_util_block, original_obj, config.OA_penalty_factor)
                mip_feasible = solve_linear_GDP(master_util_block, config,
                                                self.timing)
                self._update_bounds_after_master_problem_solve(mip_feasible,
                                                               oa_obj, logger)

                # TODO: No idea what args these callbacks should actually take
                config.call_after_master_solve(master_util_block, self)

            # Check termination conditions
            if self.any_termination_criterion_met(config):
                break

            with time_code(self.timing, 'nlp'):
                _fix_master_soln_solve_subproblem_and_add_cuts(
                    master_util_block, subproblem_util_block, config, self)

            # Add integer cut
            with time_code(self.timing, "integer cut generation"):
                added = add_no_good_cut(master_util_block, config)
                if not added:
                    # We've run out of discrete solutions, so we're done.
                    self._update_dual_bound_to_infeasible(logger)

            # Check termination conditions
            if self.any_termination_criterion_met(config):
                break

        self._get_final_pyomo_results_object()
        if self.pyomo_results.solver.termination_condition not in \
           {TerminationCondition.infeasible, TerminationCondition.unbounded}:
            self._transfer_incumbent_to_original_model()
        return self.pyomo_results

    def _setup_augmented_Lagrangian_objective(self, master_util_block):
        m = master_util_block.model()
        main_objective = next(m.component_data_objects(Objective, active=True))

        # Set up augmented Lagrangean penalty objective
        main_objective.deactivate()
        # placeholder for oa objective
        master_util_block.oa_obj = Objective(sense=minimize)

        return main_objective

    def _update_augmented_Lagrangian_objective(self, master_util_block,
                                               main_objective,
                                               OA_penalty_factor):
        m = master_util_block.model()
        sign_adjust = 1 if main_objective.sense == minimize else -1
        OA_penalty_expr = sign_adjust * OA_penalty_factor * \
                          sum(v for v in m.component_data_objects(
                              ctype=Var, descend_into=(Block, Disjunct))
                          if v.parent_component().local_name == 
                              'GDPopt_OA_slacks')
        master_util_block.oa_obj.expr = main_objective.expr + OA_penalty_expr

        return master_util_block.oa_obj.expr
