#!/usr/bin/env python3
"""
app/dependency_analyzer.py — GAP‑16 Constraint Dependency Analysis
Maps variable‑level dependencies between constraints, detects impact chains,
circular dependencies, and tight coupling. Warns operators before deployment.
"""
import json, re
from collections import defaultdict
from typing import List, Dict, Set, Optional, Tuple

_KEYWORDS = {"AND", "OR", "NOT", "IF", "THEN", "ELSE", "IN", "TRUE", "FALSE"}

def extract_variables(constraint: dict) -> Set[str]:
    cf = constraint.get("canonical_form", "")
    if not isinstance(cf, str):
        return set()
    tokens = re.findall(r'[A-Za-z_]\w*', cf)
    return {t for t in tokens if t.upper() not in _KEYWORDS}


class DependencyResult:
    def __init__(self, constraint_name: str):
        self.constraint_name = constraint_name
        self.variables: List[str] = []
        self.directly_depends_on: List[str] = []
        self.transitively_depends_on: List[str] = []
        self.dependents_count: int = 0
        self.impact_radius: int = 0
        self.safe_to_change: bool = True
        self.impact_chains: List[List[str]] = []
        self.circular_dependency: bool = False

    def to_dict(self) -> dict:
        return {
            "constraint_name": self.constraint_name,
            "variables": self.variables,
            "directly_depends_on": self.directly_depends_on,
            "transitively_depends_on": self.transitively_depends_on,
            "dependents_count": self.dependents_count,
            "impact_radius": self.impact_radius,
            "safe_to_change": self.safe_to_change,
            "impact_chains": self.impact_chains,
            "circular_dependency": self.circular_dependency,
        }


class CriticalityResult:
    def __init__(self, variable: str, count: int, constraints: List[str], risk: str):
        self.variable = variable
        self.count = count
        self.constraints = constraints
        self.risk = risk

    def to_dict(self) -> dict:
        return {
            "variable": self.variable,
            "count": self.count,
            "constraints": self.constraints,
            "risk": self.risk,
        }


class ConstraintDependencyAnalyzer:
    def __init__(self, constraints: List[dict], tight_coupling_threshold: int = 10):
        self._constraints = {c["identity_string"]: c for c in constraints if isinstance(c, dict)}
        self._threshold = tight_coupling_threshold
        self._variable_map: Dict[str, List[str]] = self._build_variable_map()
        self._dependency_graph: Dict[str, Set[str]] = self._build_dependency_graph()
        self._reverse_graph: Dict[str, Set[str]] = self._build_reverse_graph()

    def _build_variable_map(self) -> Dict[str, List[str]]:
        var_map: Dict[str, List[str]] = defaultdict(list)
        for name, c in self._constraints.items():
            for v in extract_variables(c):
                var_map[v].append(name)
        return dict(var_map)

    def _build_dependency_graph(self) -> Dict[str, Set[str]]:
        graph: Dict[str, Set[str]] = {name: set() for name in self._constraints}
        for name, c in self._constraints.items():
            for v in extract_variables(c):
                for other in self._variable_map.get(v, []):
                    if other != name:
                        graph[name].add(other)
        return graph

    def _build_reverse_graph(self) -> Dict[str, Set[str]]:
        rev: Dict[str, Set[str]] = {name: set() for name in self._constraints}
        for name, deps in self._dependency_graph.items():
            for dep in deps:
                rev[dep].add(name)
        return rev

    def analyze_impact(self, constraint_name: str, safe_threshold: int = 10) -> DependencyResult:
        result = DependencyResult(constraint_name)
        if constraint_name not in self._constraints:
            return result
        c = self._constraints[constraint_name]
        result.variables = sorted(extract_variables(c))
        result.directly_depends_on = sorted(self._dependency_graph.get(constraint_name, []))
        result.dependents_count = len(self._reverse_graph.get(constraint_name, []))
        visited: Set[str] = set()
        queue = list(result.directly_depends_on)
        visited.update(queue)
        transitives: Set[str] = set()
        while queue:
            current = queue.pop(0)
            for neighbor in self._dependency_graph.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    transitives.add(neighbor)
                    queue.append(neighbor)
        result.transitively_depends_on = sorted(transitives)
        result.impact_radius = len(result.directly_depends_on) + len(transitives)
        result.safe_to_change = result.impact_radius <= safe_threshold
        for target in result.transitively_depends_on:
            chain = self._find_shortest_path(constraint_name, target)
            if chain:
                result.impact_chains.append(chain)
        return result

    def _find_shortest_path(self, start: str, end: str) -> Optional[List[str]]:
        if start == end:
            return [start]
        visited = {start}
        queue = [[start]]
        while queue:
            path = queue.pop(0)
            node = path[-1]
            for neighbor in self._dependency_graph.get(node, []):
                if neighbor == end:
                    return path + [end]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return None

    def find_circular_dependencies(self) -> List[Set[str]]:
        cycles: List[Set[str]] = []
        visited_all: Set[str] = set()
        def dfs(node: str, path: List[str], path_set: Set[str]):
            if node in path_set:
                cycle_start = path.index(node)
                cycle = set(path[cycle_start:])
                if len(cycle) >= 2 and cycle not in cycles:
                    cycles.append(cycle)
                return
            if node in visited_all:
                return
            path.append(node)
            path_set.add(node)
            for neighbor in self._dependency_graph.get(node, []):
                dfs(neighbor, path, path_set)
            path.pop()
            path_set.discard(node)
            visited_all.add(node)
        for name in self._constraints:
            dfs(name, [], set())
        return cycles

    def find_tight_coupling(self, threshold: int = None) -> List[CriticalityResult]:
        if threshold is None:
            threshold = self._threshold
        results: List[CriticalityResult] = []
        for var, names in self._variable_map.items():
            count = len(names)
            if count >= threshold:
                risk = "high" if count >= threshold * 2 else "medium"
                results.append(CriticalityResult(var, count, sorted(names), risk))
        results.sort(key=lambda x: x.count, reverse=True)
        return results

    def find_independent_constraints(self) -> List[str]:
        independent = []
        for name in self._constraints:
            if not self._dependency_graph.get(name) and not self._reverse_graph.get(name):
                independent.append(name)
        return sorted(independent)

    def analyze_variable_criticality(self) -> List[CriticalityResult]:
        results = []
        for var, names in self._variable_map.items():
            count = len(names)
            risk = "low"
            if count >= self._threshold * 2:
                risk = "high"
            elif count >= self._threshold:
                risk = "medium"
            results.append(CriticalityResult(var, count, sorted(names), risk))
        results.sort(key=lambda x: x.count, reverse=True)
        return results

    def full_report(self, constraint_name: str = None) -> dict:
        report = {
            "constraint_count": len(self._constraints),
            "variable_count": len(self._variable_map),
            "independent_constraints": self.find_independent_constraints(),
            "circular_dependencies": [sorted(c) for c in self.find_circular_dependencies()],
            "tight_couplings": [t.to_dict() for t in self.find_tight_coupling()],
            "variable_criticality": [c.to_dict() for c in self.analyze_variable_criticality()[:20]],
        }
        if constraint_name:
            report["impact_analysis"] = self.analyze_impact(constraint_name).to_dict()
        return report
