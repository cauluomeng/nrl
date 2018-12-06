# -*- coding: utf-8 -*-

"""Algorithms for generating random walks for Node2vec."""

from typing import Iterable, Optional

import numpy as np
from gensim.models import Word2Vec
from igraph import Graph, Vertex

from .word2vec import Word2VecParameters, get_word2vec_from_walks
from ..walker import BiasedRandomWalker, RandomWalkParameters

__all__ = [
    'Node2VecModel',
]

WEIGHT = 'weight'


class Node2VecModel:
    """An implementation of Node2Vec using igraph."""

    FIRST_TRAVEL_KEY = 'first_travel_key'
    PROBS_KEY = 'probabilities'
    WEIGHT_KEY = 'weight'
    NUM_WALKS_KEY = 'num_walks'
    WALK_LENGTH_KEY = 'walk_length'
    P_KEY = 'p'
    Q_KEY = 'q'

    def __init__(self,
                 graph: Graph,
                 random_walk_parameters: Optional[RandomWalkParameters] = None,
                 word2vec_parameters: Optional[Word2VecParameters] = None
                 ) -> None:
        """Precompute the walking probabilities and generate random walks.

        :param graph: Input graph
        :param dimensions: Embedding dimensions (default: 128)
        :param walk_length: Number of nodes in each walk (default: 80)
        :param num_walks: Number of walks per node (default: 10)
        :param p: Return hyper parameter (default: 1)
        :param q: Inout parameter (default: 1)
        :param weight_key: On weighted graphs, this is the key for the weight attribute (default: 'weight')
        :param workers: Number of workers for parallel execution (default: 1)
        :param sampling_strategy: Node specific sampling strategies, supports setting node specific 'q', 'p',
         'num_walks' and 'walk_length'.

        Use these keys exactly. If not set, will use the global ones which were passed on the object initialization
        """
        self.graph = graph
        self.dimensions = word2vec_parameters.size
        self.walk_length = random_walk_parameters.max_path_length
        self.num_walks = random_walk_parameters.number_paths
        self.p = random_walk_parameters.p
        self.q = random_walk_parameters.q
        self.weight_key = 'weight'
        self.workers = word2vec_parameters.workers
        self.random_walk_parameters = random_walk_parameters
        self.walker = BiasedRandomWalker(self.random_walk_parameters)

        sampling_strategy = random_walk_parameters.sampling_strategy
        if sampling_strategy is not None:
            self.sampling_strategy = sampling_strategy

        if not random_walk_parameters.is_weighted:
            for edge in self.graph.es:
                edge['weight'] = 1

        self._precompute_probs()

    def _precompute_probs(self):
        """Pre-compute transition probabilities for each node."""
        first_travel_done = set()

        for node in self.graph.vs:
            node[self.PROBS_KEY] = dict()

        for source in self.graph.vs:
            for current_node in source.neighbors():
                unnormalized_weights, first_travel_weights = self._compute_unnormalized_weights(
                    source,
                    current_node,
                    first_travel_done
                )

                # Normalize
                unnormalized_weights = np.array(unnormalized_weights)
                sum_of_weights = unnormalized_weights.sum()
                current_node[self.PROBS_KEY][source['name']] = unnormalized_weights / sum_of_weights

                if current_node['name'] not in first_travel_done:
                    unnormalized_weights = np.array(first_travel_weights)
                    sum_of_weights = unnormalized_weights.sum()
                    current_node[self.FIRST_TRAVEL_KEY] = unnormalized_weights / sum_of_weights
                    first_travel_done.add(current_node['name'])

    def _compute_unnormalized_weights(self, source, current_node, first_travel_done):
        """Compute the unnormalized weights for Node2Vec algorithm.

        :param source: The source node of the previous step on the walk.
        :param current_node: The target node of the previous step on the walk.
        :param first_travel_done: A set
        :return:
        """
        unnormalized_weights = list()  # TODO: why not a dict?
        first_travel_weights = list()

        # Calculate unnormalized weights
        for target in current_node.neighbors():
            p = self._get_p(current_node['name'])
            q = self._get_q(current_node['name'])

            edge = self.graph.es.select(_between=([current_node.index], [target.index]))
            edge_weight = edge[self.weight_key][0]

            # Assign the unnormalized sampling strategy weight, normalize during random walk
            unnormalized_weights.append(
                self._compute_prob(source.index, target.index, p, q, edge_weight)
            )

            if current_node['name'] not in first_travel_done:
                first_travel_weights.append(edge_weight)

        return unnormalized_weights, first_travel_weights

    def _get_p(self, current_node):
        p = self.sampling_strategy[current_node].get(
            self.P_KEY,
            self.p
        ) if current_node in self.sampling_strategy else self.p
        return p

    def _get_q(self, current_node):
        q = self.sampling_strategy[current_node].get(
            self.Q_KEY,
            self.q
        ) if current_node in self.sampling_strategy else self.q
        return q

    def _compute_prob(self, source, target, p, q, weight):
        if target == source:
            return weight / p
        elif len(self.graph.es.select(_source=source, _target=target)) > 0:
            return weight
        return weight / q

    def fit(self) -> Word2Vec:
        """Create the embeddings using gensim's Word2Vec."""
        walks = self.walker.get_walks(self.graph)

        # stringify output from igraph for Word2Vec
        walks = self._transform_walks(walks)

        return get_word2vec_from_walks(walks)

    def _transform_walks(self, walks: Iterable[Iterable[Vertex]]) -> Iterable[Iterable[str]]:
        for walk in walks:
            yield map(str, walk)
