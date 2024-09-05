"""
The delete node drops specified packets
"""
import copy
from collections import deque
from multiprocessing.connection import Connection
from typing import Literal, Callable

import dearpygui.dearpygui as dpg

from lowcaf.nodeeditor.nodebuilder import NodeBuilder
from lowcaf.nodes.ifaces.inode import INode
from lowcaf.packetprocessing.bbpacket import BBPacket
from lowcaf.nodes.ifaces.rnode import RNode
from lowcaf.nodes.jgf.jnode import JNode


class DelG(INode):

    def __init__(
            self,
            node_id: int
    ):
        with dpg.stage() as _staging_container_id:
            with dpg.node(label="Delete", show=False) as _id:
                with dpg.node_attribute() as self.in_attr:
                    with dpg.group(horizontal=True):
                        dpg.add_text('Start, Stop, Step:')
                        self.range = dpg.add_input_intx(
                            size=3,
                            default_value=(0, 0, 1, 0),
                            width=200
                        )
                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Output
                ) as self.out_attr:
                    pass

        super().__init__(node_id, _id, _staging_container_id,
                         [self.in_attr],
                         [self.out_attr])

    @staticmethod
    def disp_name():
        return 'Delete'

    def _add_meta_data(self) -> dict:
        (start, stop, step, _) = dpg.get_value(self.range)

        return {
            'start': start,
            'stop': stop,
            'step': step
        }

    def _from_jgf(self,
                  metadata: dict,
                  in_attrs: list[JNode],
                  out_attrs: list[JNode]):
        start = metadata['start']
        stop = metadata['stop']
        step = metadata['step']

        dpg.set_value(self.range, (start, stop, step, 0))


class DelN(RNode):
    def __init__(
            self,
            node_id: int,
            start: int,
            stop: int,
            step: int,
            inode: DelG | None,
    ):
        assert isinstance(inode, DelG | None)
        super().__init__(node_id, 1, 1, inode)

        self.inode: DelG | None = inode
        self._ctr = 0
        self._it = iter(range(start, stop, step))

    def _should_drop(self):
        try:
            nxt_drop = next(self._it)
            while True:
                if self._ctr < nxt_drop:
                    yield False
                elif self._ctr == nxt_drop:
                    yield True
                    nxt_drop = next(self._it)
        except StopIteration:
            while True:
                yield False

    @staticmethod
    def create_from_inode(inode: DelG) -> 'RNode':
        assert isinstance(inode, DelG)
        print(dpg.get_value(inode.range))
        start, stop, step, _ = dpg.get_value(inode.range)
        return DelN(
            inode.node_id,
            start,
            stop,
            step,
            inode,
        )

    def process(self, inputs: list[deque[BBPacket]],
                outputs: list[list[BBPacket]]):
        pkt: BBPacket = inputs[0].popleft()

        if not next(self._should_drop()):
            outputs[0].append(pkt)

        self._ctr += 1

    def is_ready(self, inputs: list[deque[BBPacket]]) -> bool:
        if len(inputs[0]) > 0:
            return True
        else:
            return False

    def setup(self, reg_socks: Callable[[str, int, int], Connection]):
        self._ctr = 0


NodeBuilder.register_node(DelG, DelN)
