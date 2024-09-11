"""
The compare node allows to compare two incoming packets with each other
"""
from collections import deque

import dearpygui.dearpygui as dpg

from lowcaf.nodeeditor.nodebuilder import NodeBuilder
from lowcaf.nodes.ifaces.inode import INode
from lowcaf.nodes.ifaces.rnode import RNode
from lowcaf.packetprocessing.bbpacket import BBPacket


class CompG(INode):

    def __init__(
            self,
            node_id: int
    ):
        with dpg.stage() as _staging_container_id:
            with dpg.node(label="Compare", show=False) as _id:
                with dpg.node_attribute() as self.in_attr_1:
                    dpg.add_text("Input A")
                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Output
                ) as self.out_attr_1:
                    pass
                with dpg.node_attribute() as self.in_attr_2:
                    dpg.add_text("Input B")
                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Output
                ) as self.out_attr_2:
                    pass

        super().__init__(node_id, _id, _staging_container_id,
                         [self.in_attr_1, self.in_attr_2],
                         [self.out_attr_1, self.out_attr_2])

    @staticmethod
    def disp_name():
        return 'Compare'

class CompN(RNode):
    def __init__(
            self,
            node_id: int,
            inode: CompG | None,
    ):
        assert isinstance(inode, CompG | None)
        super().__init__(node_id, 2, 2, inode)

        self.inode: CompG | None = inode

    @staticmethod
    def create_from_inode(inode: CompG) -> 'RNode':
        assert isinstance(inode, CompG)
        return CompN(
            inode.node_id,
            inode,
        )

    def process(self, inputs: list[deque[BBPacket]],
                outputs: list[list[BBPacket]]):
        pkt_a: BBPacket = inputs[0].popleft()
        pkt_b: BBPacket = inputs[1].popleft()

        diff = pkt_b.scapy_pkt.time - pkt_a.scapy_pkt.time
        pkt_a.metadata['t_diff'] = diff
        pkt_b.metadata['t_diff'] = diff

        outputs[0].append(pkt_a)
        outputs[1].append(pkt_b)

    def is_ready(self, inputs: list[deque[BBPacket]]) -> bool:
        if len(inputs[0]) > 0 and len(inputs[1]) > 0:
            return True
        else:
            return False


NodeBuilder.register_node(CompG, CompN)
