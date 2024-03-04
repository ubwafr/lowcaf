from abc import abstractmethod
from collections import deque
from multiprocessing.connection import Connection
from typing import Callable

from lowcaf.packetprocessing.bbpacket import BBPacket
from lowcaf.nodes.ifaces.inode import INode


class RNode:
    """
    An RNode is a "real" node, e.g., it extends normal INodes by functions to
    actually execute processing upon this node.

    If a node is only used for external processing then an INode is sufficient
    """

    def __init__(
            self,
            own_id: int,
            nr_inputs: int,
            nr_outputs: int,
            inode: INode | None = None
    ):
        assert isinstance(own_id, int)
        self.id: int = own_id

        assert isinstance(nr_inputs, int)
        assert isinstance(nr_outputs, int)
        self.nr_inputs: int = nr_inputs
        self.nr_outputs: int = nr_outputs

        assert isinstance(inode, INode | None)
        self.inode: INode | None = inode


    @abstractmethod
    def process(
            self,
            inputs: list[deque[BBPacket]],
            outputs: list[list[BBPacket]]):
        """
        This method should be overriden to provide the processing mad

        Args:
            inputs: A list corresponding to the inputs
            outputs: The list of outputs
        """
        raise NotImplementedError

    @abstractmethod
    def is_ready(
            self,
            inputs: list[deque[BBPacket]]) -> bool:
        """
        Check if this node is currently able to run its process method
        """
        raise NotImplementedError

    def setup(self, reg_socks: Callable[[str, int, int], Connection]):
        """
        This method is called once prior to simulation start. Nodes may use
        this function to prepare themselves for execution.

        In addition they can register themselves for a specific socket. See the
        method PacketProcessor.register_socket for more information.
        """
        pass

    def teardown(self):
        """
        This method is called once the simulation is finished. If anything
        needs to be cleaned up, this can be performed here
        """
        pass

    @staticmethod
    @abstractmethod
    def create_from_inode(inode: INode) -> 'RNode':
        raise NotImplementedError
