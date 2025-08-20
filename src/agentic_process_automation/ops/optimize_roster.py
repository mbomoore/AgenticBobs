"""Roster optimization using OR-Tools.

Optimizes resource assignments and schedules for process execution.
"""
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass

try:
    from ortools.linear_solver import pywraplp
    from ortools.sat.python import cp_model
    ORTOOLS_AVAILABLE = True
except ImportError:
    ORTOOLS_AVAILABLE = False


@dataclass
class Resource:
    """Represents a resource with skills and availability."""
    id: str
    name: str
    skills: List[str]
    hourly_cost: float = 0.0
    max_hours_per_day: float = 8.0


@dataclass
class Task:
    """Represents a task requiring specific skills."""
    id: str
    name: str
    required_skills: List[str]
    duration_hours: float
    priority: int = 1
    earliest_start: Optional[int] = None  # time slot
    latest_finish: Optional[int] = None   # time slot


@dataclass
class Assignment:
    """Represents a resource assignment to a task."""
    resource_id: str
    task_id: str
    start_time: int
    duration: int


class RosterOptimizer:
    """Optimizes resource assignments using OR-Tools."""
    
    def __init__(self):
        if not ORTOOLS_AVAILABLE:
            raise ImportError("OR-Tools library required for roster optimization")
    
    def optimize_assignments(self, resources: List[Resource], tasks: List[Task], 
                           time_horizon: int = 168) -> List[Assignment]:
        """Optimize resource assignments to tasks.
        
        Args:
            resources: Available resources
            tasks: Tasks to be assigned
            time_horizon: Time horizon in hours (default: 1 week)
            
        Returns:
            List of optimal assignments
        """
        model = cp_model.CpModel()
        
        # Decision variables: assignment[r][t][s] = 1 if resource r works on task t starting at time s
        assignments = {}
        for r in range(len(resources)):
            for t in range(len(tasks)):
                for s in range(time_horizon - int(tasks[t].duration_hours) + 1):
                    assignments[(r, t, s)] = model.NewBoolVar(f'assign_{r}_{t}_{s}')
        
        # Constraints
        
        # 1. Each task must be assigned exactly once
        for t in range(len(tasks)):
            model.Add(
                sum(assignments[(r, t, s)] 
                    for r in range(len(resources))
                    for s in range(time_horizon - int(tasks[t].duration_hours) + 1)
                    if self._has_required_skills(resources[r], tasks[t])) == 1
            )
        
        # 2. Resource capacity constraints
        for r in range(len(resources)):
            for h in range(time_horizon):
                # Resource can work at most max_hours_per_day per day
                day = h // 24
                day_start = day * 24
                day_end = min((day + 1) * 24, time_horizon)
                
                model.Add(
                    sum(assignments[(r, t, s)]
                        for t in range(len(tasks))
                        for s in range(max(0, h - int(tasks[t].duration_hours) + 1), h + 1)
                        if s + int(tasks[t].duration_hours) > h and s < time_horizon) 
                    <= 1  # No overlapping assignments
                )
        
        # 3. Task timing constraints
        for t in range(len(tasks)):
            task = tasks[t]
            if task.earliest_start is not None:
                for r in range(len(resources)):
                    for s in range(min(task.earliest_start, time_horizon)):
                        if (r, t, s) in assignments:
                            model.Add(assignments[(r, t, s)] == 0)
            
            if task.latest_finish is not None:
                for r in range(len(resources)):
                    for s in range(max(0, task.latest_finish - int(task.duration_hours) + 1), time_horizon):
                        if (r, t, s) in assignments:
                            model.Add(assignments[(r, t, s)] == 0)
        
        # Objective: minimize cost and maximize priority
        objective_terms = []
        for r in range(len(resources)):
            for t in range(len(tasks)):
                for s in range(time_horizon - int(tasks[t].duration_hours) + 1):
                    if (r, t, s) in assignments:
                        cost = resources[r].hourly_cost * tasks[t].duration_hours
                        priority_bonus = tasks[t].priority * 100  # Higher priority = lower cost
                        objective_terms.append(assignments[(r, t, s)] * (cost - priority_bonus))
        
        model.Minimize(sum(objective_terms))
        
        # Solve
        solver = cp_model.CpSolver()
        status = solver.Solve(model)
        
        result_assignments = []
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            for r in range(len(resources)):
                for t in range(len(tasks)):
                    for s in range(time_horizon - int(tasks[t].duration_hours) + 1):
                        if (r, t, s) in assignments and solver.Value(assignments[(r, t, s)]):
                            result_assignments.append(Assignment(
                                resource_id=resources[r].id,
                                task_id=tasks[t].id,
                                start_time=s,
                                duration=int(tasks[t].duration_hours)
                            ))
        
        return result_assignments
    
    def _has_required_skills(self, resource: Resource, task: Task) -> bool:
        """Check if resource has all required skills for task."""
        return all(skill in resource.skills for skill in task.required_skills)


class MockRosterOptimizer:
    """Mock roster optimizer for testing when OR-Tools is not available."""
    
    def optimize_assignments(self, resources: List[Resource], tasks: List[Task], 
                           time_horizon: int = 168) -> List[Assignment]:
        """Return mock assignments."""
        assignments = []
        
        # Simple greedy assignment for testing
        current_time = 0
        for i, task in enumerate(tasks):
            # Find first suitable resource
            suitable_resource = None
            for resource in resources:
                if all(skill in resource.skills for skill in task.required_skills):
                    suitable_resource = resource
                    break
            
            if suitable_resource:
                assignments.append(Assignment(
                    resource_id=suitable_resource.id,
                    task_id=task.id,
                    start_time=current_time,
                    duration=int(task.duration_hours)
                ))
                current_time += int(task.duration_hours)
        
        return assignments


def create_roster_optimizer() -> RosterOptimizer:
    """Create appropriate roster optimizer based on available dependencies."""
    if ORTOOLS_AVAILABLE:
        return RosterOptimizer()
    else:
        return MockRosterOptimizer()