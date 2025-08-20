from __future__ import annotations

from typing import Union
# ---- import your AST types from the SimPy evaluator module ----
# from simpy_evaluator import Task, Verify, SelectBest, Seq, Par, Node, Scenario
# Minimal re-declarations just for this file's clarity:
class Task:       # name, performer
    def __init__(self, name:str, performer:str): self.name, self.performer = name, performer
class Verify:     # performer
    def __init__(self, performer:str): self.performer = performer
class SelectBest: # performer, left, right
    def __init__(self, performer:str, left, right): self.performer, self.left, self.right = performer, left, right
class Seq:        # items
    def __init__(self, *items): self.items = tuple(items)
class Par:        # left, right
    def __init__(self, left, right): self.left, self.right = left, right
    
    
Node = Union[Task, Verify, SelectBest, Seq, Par]