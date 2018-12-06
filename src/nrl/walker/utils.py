# -*- coding: utf-8 -*-

"""Utilities for random walker algorithms."""

import random
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Iterable, Optional

from igraph import Graph, Vertex

__all__ = [
    'RandomWalkParameters',
    'AbstractRandomWalker',
]


@dataclass
class RandomWalkParameters:
    """Parameters for random walks."""

    #: The number of paths to get
    number_paths: int = 10

    #: The maximum length the walk can be
    max_path_length: int = 40

    # TODO use this in get_random_walks
    #: Probability of restarting the path. If None, doesn't consider.
    restart_probability: Optional[float] = 0.0

    """Node2vec parameters"""

    #: p
    p: Optional[float] = 1.0

    #: q
    q: Optional[float] = 1.0

    # the strategy for sampling the walks
    # TODO: type
    # TODO: implement different strategies
    sampling_strategy: Optional[Dict] = field(default_factory=dict)

    #: Whether the graph is directed or not
    is_directed: Optional[bool] = False

    # Whether the graph is weighted or not
    is_weighted: Optional[bool] = True


class AbstractRandomWalker(ABC):
    """An abstract class for random walkers."""

    def __init__(self, parameters: RandomWalkParameters):
        """Initialize the walker with the given random walk parameters dataclass."""
        self.parameters = parameters

    def get_walks(self, graph: Graph) -> Iterable[Iterable[Vertex]]:
        """Get walks over this graph."""
        for _ in range(self.parameters.number_paths):
            vertices = list(graph.vs)
            random.shuffle(vertices)
            for vertex in graph.vs:
                yield self.get_walk(graph, vertex)

    @abstractmethod
    def get_walk(self, graph: Graph, vertex: Vertex) -> Iterable[Vertex]:
        """Generate one walk."""