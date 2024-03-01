from copy import deepcopy

import dearpygui.dearpygui as dpg
from collections import deque

from src.nodeeditor.nodebuilder import NodeBuilder
from src.packetprocessing.bbpacket import BBPacket
from src.nodes.ifaces.inode import INode
from src.nodes.ifaces.rnode import RNode


class RepeaterG(INode):

    def __init__(
            self,
            node_id: int
    ):
        with dpg.stage() as _staging_container_id:
            with dpg.node(label=self.disp_name(), show=False) as _id:
                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Input
                ) as self.in_attr:
                    self.repeat = dpg.add_input_int(
                        default_value=2,
                        min_value=1,
                        min_clamped=True,
                        width=200
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
        return 'Repeater'


class RepeaterN(RNode):

    def __init__(
            self,
            node_id: int,
            inode: RepeaterG | None = None,
            repeats: int = 2,

    ):
        assert isinstance(inode, RepeaterG | None)
        super().__init__(node_id, 1, 1, inode)
        self.inode: RepeaterG | None = inode
        self.repeats: int = repeats

    @staticmethod
    def create_from_inode(inode: RepeaterG) -> 'RNode':
        assert isinstance(inode, RepeaterG)
        return RepeaterN(
            inode.node_id,
            inode,
            repeats=dpg.get_value(inode.repeat)
        )

    def process(self, inputs: list[deque], outputs: list[list]):
        pkt: BBPacket = inputs[0].popleft()

        for _ in range(self.repeats):
            cpy = deepcopy(pkt)
            outputs[0].append(cpy)

    def is_ready(self, inputs: list[deque]) -> bool:
        return len(inputs[0]) > 0


NodeBuilder.register_node(RepeaterG, RepeaterN)
