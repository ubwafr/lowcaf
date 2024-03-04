import logging
from collections import deque
from multiprocessing.connection import Connection
from typing import Callable

import dearpygui.dearpygui as dpg
from scapy.layers.l2 import Ether

from lowcaf.nodeeditor.nodebuilder import NodeBuilder
from lowcaf.nodes.ifaces.inode import INode
from lowcaf.nodes.ifaces.rnode import RNode
from lowcaf.packetprocessing.bbpacket import BBPacket

LOGGER = logging.getLogger(__name__)


class DummySrcG(INode):

    def __init__(
            self,
            node_id: int,
    ):
        default = 100
        with dpg.stage() as _staging_container_id:
            with dpg.node(label=self.disp_name(), show=False) as _id:
                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Output
                ) as self.out_attr:
                    self.nr_packets = dpg.add_input_int(
                        label='Number of Packets',
                        default_value=default,
                        min_value=0,
                        min_clamped=True,
                        callback=self.self_set_ctr_cb
                    )

        self.ctr = default
        super().__init__(node_id,
                         _id, _staging_container_id, [],
                         [self.out_attr])

    def self_set_ctr_cb(self, sender, val):
        LOGGER.debug(f'{val}')
        self.ctr = val

    @staticmethod
    def disp_name() -> str:
        return 'Dummy Src'

    def _show(self, dpcm: int):
        self.dpcm = dpcm

        dpg.set_item_width(self.nr_packets, 3 * self.dpcm)


class DummySrcN(RNode):
    def __init__(
            self,
            node_id: int,
            nr_packets: int,
            inode: INode | None
    ):
        super().__init__(node_id, 0, 1, inode)

        assert isinstance(nr_packets, int)
        self.nr_packets = nr_packets
        self.ctr = self.nr_packets

    @staticmethod
    def create_from_inode(inode: DummySrcG) -> 'RNode':
        assert isinstance(inode, DummySrcG)
        return DummySrcN(
            inode.node_id,
            dpg.get_value(inode.nr_packets),
            inode
        )

    def process(self, inputs: list[deque], outputs: list[list]):
        pkt = BBPacket(Ether(b'abcdefgh'), 0)
        self.ctr -= 1

        outputs[0].append(pkt)

    def is_ready(self, inputs: list[deque]) -> bool:
        if self.ctr > 0:
            return True
        else:
            self.ctr = self.nr_packets
            return False


class NullSnkG(INode):

    def __init__(
            self,
            node_id: int
    ):
        with dpg.stage() as _staging_container_id:
            with dpg.node(label=self.disp_name(), show=False) as _id:
                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Input
                ) as self.in_attr:
                    self.ctr = dpg.add_input_int(
                        default_value=0,
                        width=200
                    )

        super().__init__(node_id,
                         _id, _staging_container_id,
                         [self.in_attr], [])

    @staticmethod
    def disp_name() -> str:
        return 'Null Sink'


class NullSnkN(RNode):

    def __init__(
            self,
            node_id: int,
            inode: NullSnkG | None = None,
    ):
        assert isinstance(inode, NullSnkG | None)
        super().__init__(node_id, 1, 0, inode)
        self.inode: NullSnkG | None = inode

    @staticmethod
    def create_from_inode(inode: NullSnkG) -> 'RNode':
        assert isinstance(inode, NullSnkG)
        return NullSnkN(
            inode.node_id,
            inode,
        )

    def process(self, inputs: list[deque], outputs: list[list]):
        LOGGER.debug("NullSnk Operation")
        inputs[0].popleft()

        if self.inode is not None:
            val = dpg.get_value(self.inode.ctr)
            dpg.set_value(self.inode.ctr, val + 1)

    def is_ready(self, inputs: list[deque]) -> bool:
        LOGGER.debug(f"Is NullSnk ready? {len(inputs[0]) >= 1}")
        return len(inputs[0]) >= 1

    def setup(self, reg_socks: Callable[[str, int, int], Connection]):
        if self.inode is not None:
            dpg.set_value(self.inode.ctr, 0)


class CounterG(INode):

    def __init__(
            self,
            node_id: int
    ):
        with dpg.stage() as _staging_container_id:
            with dpg.node(label=self.disp_name(), show=False) as _id:
                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Input
                ) as self.in_attr:
                    self.ctr = dpg.add_text(
                        default_value='0',
                    )
                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Output
                ) as self.out_attr:
                    dpg.add_text('Output')

        super().__init__(
            node_id,
            _id,
            _staging_container_id,
            [self.in_attr],
            [self.out_attr])

    @staticmethod
    def disp_name() -> str:
        return 'Counter'


class CounterN(RNode):
    def __init__(
            self,
            node_id: int,
            inode: CounterG | None = None,
    ):
        assert isinstance(inode, CounterG | None)
        super().__init__(node_id, 1, 1, inode)

        self.inode: CounterG | None = inode

        self.ctr = 0

    @staticmethod
    def create_from_inode(inode: CounterG) -> 'RNode':
        assert isinstance(inode, CounterG)
        return CounterN(
            inode.node_id,
            inode,
        )

    def process(self,
                inputs: list[deque[BBPacket]],
                outputs: list[list[BBPacket]]):
        pkt = inputs[0].popleft()

        self.ctr += 1

        if self.inode is not None:
            dpg.set_value(self.inode.ctr, str(self.ctr))

        outputs[0].append(pkt)

    def is_ready(self, inputs: list[deque]) -> bool:
        return len(inputs[0]) >= 1

    def setup(self, reg_socks: Callable[[str, int, int], Connection]):
        self.ctr = 0
        if self.inode is not None:
            dpg.set_value(self.inode.ctr, 0)


NodeBuilder.register_node(NullSnkG, NullSnkN)
NodeBuilder.register_node(CounterG, CounterN)
