import logging
from abc import ABC, abstractmethod
from collections import deque

from lowcaf.packetprocessing.nodestate import NodeState

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lowcaf.packetprocessing.packetprocessor import PacketProcessor

LOGGER = logging.getLogger(__name__)

class NodeSelector(ABC):
    """
    The node selector defines the strategy on how the next node to be
    processed is selected.
    """

    def gen_nodes(self, pp: 'PacketProcessor'):
        while not self.is_finished():
            ns = self.select_next()
            ns.process()
            self.update(pp, ns)

    @abstractmethod
    def select_next(self) -> 'NodeState':
        """
        Select the next node that should be processed

        Returns:
            ns: NodeState
        """
        raise NotImplementedError

    @abstractmethod
    def update(self, pp: 'PacketProcessor', node_state: 'NodeState'):
        """
        Update the internal state after a Process was called on another node
        Args:
            pp: The PacketProcessor object
            node_state: The NodeState object on which process was called
        """
        raise NotImplementedError

    @abstractmethod
    def is_finished(self) -> bool:
        """
        Should return True, when no more new packets can be processed and
        False until then

        Returns:
            is_finished: bool
        """
        raise NotImplementedError


class PrioritySelector(NodeSelector):
    def __init__(self, pp: 'PacketProcessor'):
        """
        The priority selector is a simple implementation of a selector
        that will just store the nodes in a priority queue.

        Args:
            pp: The PacketProcessor obj
        """
        self.rdy: deque[NodeState] = deque()

        LOGGER.info("Initializing PrioritySelector")
        node_state: NodeState
        for node_state in pp.nodes.values():
            state = node_state.is_ready()
            # print(node_state.viz())
            if state:
                self.rdy.append(node_state)

    def select_next(self) -> 'NodeState':
        return self.rdy.popleft()

    def update(self, pp: 'PacketProcessor', node_state: 'NodeState'):
        for idx, items in enumerate(node_state.outputs):
            tgt_port = pp.links[node_state.node.id][idx]

            tgt_in = pp.nodes[tgt_port.obj_id].inputs[tgt_port.port]
            tgt_in.extend(items)
            items.clear()

            # for all nodes to which we pushed new scapy_pkt check if
            # they are now ready
            nodes_state_tgt = pp.nodes[tgt_port.obj_id]
            if (nodes_state_tgt.is_ready() and nodes_state_tgt not in
                    self.rdy):
                self.rdy.append(nodes_state_tgt)

        # finally check if we are still ready
        # important for sources, as they are not triggered above
        if node_state.is_ready() and node_state not in self.rdy:
            self.rdy.append(node_state)

    def is_finished(self) -> bool:
        return len(self.rdy) <= 0