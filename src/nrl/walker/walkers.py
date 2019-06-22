# -*- coding: utf-8 -*-

"""Implementations of random walk algorithms."""

import random

import igraph
import networkx
import numpy as np

from .utils import Walker
from ..typing import Walk

__all__ = [
    'StandardRandomWalker',
    'RestartingRandomWalker',
    'BiasedRandomWalker',
]


class StandardRandomWalker(Walker):
    """Make standard random walks, choosing the neighbors at a given position uniformly."""

    def get_igraph_walk(self, graph: igraph.Graph, vertex: igraph.Vertex) -> Walk:
        """Get a random walk by choosing from the neighbors at a given position uniformly."""
        tail = vertex
        yield tail['label']
        path_length = 1
        # return if the the current path is too long or there if there are no neighbors at the end
        while path_length < self.parameters.max_path_length and graph.neighborhood_size(tail):
            tail = random.choice(tail.neighbors())
            yield tail['label']
            path_length += 1

    def get_networkx_walk(self, graph: networkx.Graph, vertex: str) -> Walk:
        tail = vertex
        yield tail
        path_length = 1
        # return if the the current path is too long or there if there are no neighbors at the end
        while path_length < self.parameters.max_path_length and graph.neighbors(tail):
            tail = random.choice(list(graph.neighbors(tail)))
            yield tail
            path_length += 1


class RestartingRandomWalker(Walker):
    """A random walker that restarts from the original vertex with a given probability."""

    @property
    def restart_probability(self) -> float:
        """Get the probability with which this walker will restart from the original vertex."""
        return self.parameters.restart_probability

    def get_igraph_walk(self, graph: igraph.Graph, vertex: igraph.Vertex) -> Walk:
        """Generate one random walk for one vertex, with the probability, alpha, of restarting."""
        tail = vertex
        yield tail['label']
        path_length = 1

        while path_length < self.parameters.max_path_length and graph.neighborhood_size(tail):
            tail = (
                vertex
                if self.restart_probability <= random.random() else
                random.choice(tail.neighbors())
            )
            yield tail['label']
            path_length += 1

    def get_networkx_walk(self, graph: networkx.Graph, vertex: str) -> Walk:
        """Generate one random walk for one vertex, with the probability, alpha, of restarting."""
        tail = vertex
        yield tail
        path_length = 1

        while path_length < self.parameters.max_path_length and graph.neighbors(tail):
            tail = (
                vertex
                if self.restart_probability <= random.random() else
                random.choice(list(graph.neighbors(tail)))
            )
            yield tail
            path_length += 1


class BiasedRandomWalker(Walker):
    """A random walker that generates second-order random walks biased by edge weights."""

    NUM_WALKS_KEY = 'num_walks'
    WALK_LENGTH_KEY = 'walk_length'
    PROBABILITIES_KEY = 'probabilities'
    FIRST_TRAVEL_KEY = 'first_travel_key'

    @property
    def sampling_strategy(self):
        """Get the sampling strategy for this walker."""
        return self.parameters.sampling_strategy

    def _check(self, vertex):
        return (
                vertex in self.sampling_strategy and
                self.NUM_WALKS_KEY in self.sampling_strategy[vertex] and
                self.sampling_strategy[vertex][self.NUM_WALKS_KEY] <= self.parameters.number_paths
        )

    def get_igraph_walk(self, graph: igraph.Graph, vertex: igraph.Vertex) -> Walk:
        """Generate second-order random walks biased by edge weights."""
        if self.parameters.max_path_length < 2:
            raise ValueError("The path length for random walk is less than 2, which doesn't make sense")

        if self._check(vertex):
            return

        # Start walk
        yield vertex
        double_tail = vertex

        # Calculate walk length
        if vertex in self.sampling_strategy:
            walk_length = self.sampling_strategy[vertex].get(self.WALK_LENGTH_KEY, self.parameters.max_path_length)
        else:
            walk_length = self.parameters.max_path_length

        probabilities = vertex[self.FIRST_TRAVEL_KEY]
        tail = np.random.choice(vertex.neighbors(), p=probabilities)
        if not tail:
            return
        yield tail

        # Perform walk
        path_length = 2
        while path_length < walk_length:
            neighbors = tail.neighbors()

            # Skip dead end nodes
            if not neighbors:
                break

            probabilities = tail[self.PROBABILITIES_KEY][double_tail['name']]
            double_tail, tail = tail, np.random.choice(neighbors, p=probabilities)

            yield tail
            path_length += 1

    def get_networkx_walk(self, graph: networkx.Graph, vertex: str) -> Walk:
        raise NotImplementedError
