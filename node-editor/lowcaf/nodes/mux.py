"""
This module contains nodes for multiplexing and demultiplexing.

Both nodes operate deterministically, i.e., the demultiplexer puts the first
input it receives into the first output, the second into the second output and
so on until all outputs have received a packet. Then it starts again from
the beginning. The multiplexer does the same thing. It will first take a
packet from the first input, then from the second and so on.
"""
import copy
from collections import deque
from typing import Literal

import dearpygui.dearpygui as dpg

from lowcaf.nodeeditor.nodebuilder import NodeBuilder
from lowcaf.nodes.ifaces.inode import INode
from lowcaf.packetprocessing.bbpacket import BBPacket
from lowcaf.nodes.ifaces.rnode import RNode
from lowcaf.nodes.jgf.jnode import JNode


class DeMuxG(INode):

    def __init__(
            self,
            node_id: int
    ):
        with dpg.stage() as _staging_container_id:
            with dpg.node(label="Demultiplexer", show=False) as _id:
                with dpg.node_attribute() as self.in_attr:
                    with dpg.group(horizontal=True):
                        dpg.add_text("Number of Outputs: ")
                        self.widget = dpg.add_text("0")
                        with dpg.group(horizontal=False):
                            dpg.add_button(arrow=True, direction=dpg.mvDir_Up,
                                           user_data=self.widget,
                                           callback=self.add_output_cb)
                            dpg.add_button(arrow=True,
                                           direction=dpg.mvDir_Down,
                                           user_data=self.widget,
                                           callback=self.remove_output_cb)

                    with dpg.group(horizontal=True):
                        dpg.add_text("Mode")
                        self.mode = dpg.add_combo(
                            ['Alternate', 'Duplicate'],
                            default_value='Alternate',
                            width=200,
                        )

        super().__init__(node_id, _id, _staging_container_id,
                         [self.in_attr], [])

    @staticmethod
    def disp_name():
        return 'Demultiplexer'

    def add_output_cb(self, sender, appdata, userdata):
        with dpg.node_attribute(
                label="Node A2",
                attribute_type=dpg.mvNode_Attr_Output,
                parent=self.dpg_id) as attr:
            dpg.add_text('Output')

        self.outputs.append(attr)
        dpg.set_value(self.widget, int(dpg.get_value(self.widget)) + 1)
        return attr

    def remove_output_cb(self, sender, appdata, userdata):
        try:
            attr_id = self.outputs.pop()
        except IndexError:
            # the list is already empty
            return

        parent = dpg.get_item_parent(self.dpg_id)
        lnks = dpg.get_item_children(parent, 0)

        for lnk in lnks:
            if dpg.get_item_configuration(lnk)['attr_1'] == attr_id:
                nodeeditor = dpg.get_item_user_data(lnk)
                nodeeditor.delink_cb(nodeeditor, lnk)

        dpg.delete_item(attr_id)
        dpg.set_value(userdata, int(dpg.get_value(userdata)) - 1)


    def _add_meta_data(self) -> dict:
        return {
            'mode': dpg.get_value(self.mode),
        }

    def _from_jgf(self,
                  metadata,
                  in_attrs: list[JNode],
                  out_attrs: list[JNode]):

        for _ in out_attrs:
            self.add_output_cb(None, None, None)

        dpg.set_value(self.mode, metadata['mode'])

class DeMuxN(RNode):
    def __init__(
            self,
            node_id: int,
            nr_outputs: int,
            mode: str,
            inode: DeMuxG | None,
    ):
        assert isinstance(inode, DeMuxG | None)
        super().__init__(node_id, 1, nr_outputs, inode)

        self.inode: DeMuxG | None = inode
        self.active_output: int = 0
        self.mode: str = mode

    @staticmethod
    def create_from_inode(inode: DeMuxG) -> 'RNode':
        assert isinstance(inode, DeMuxG)
        return DeMuxN(
            inode.node_id,
            len(inode.outputs),
            dpg.get_value(inode.mode),
            inode,
        )

    def process(self, inputs: list[deque[BBPacket]],
                outputs: list[list[BBPacket]]):
        pkt: BBPacket = inputs[0].popleft()

        match self.mode:
            case 'Alternate':
                outputs[self.active_output].append(pkt)

                self.active_output = (self.active_output + 1) % self.nr_outputs
            case 'Duplicate':
                for output in outputs:
                    output.append(copy.deepcopy(pkt))
            case _:
                raise ValueError(f'Invalid mode: {self.mode}')

    def is_ready(self, inputs: list[deque[BBPacket]]) -> bool:
        if len(inputs[0]) > 0:
            return True
        else:
            return False


class MuxG(INode):

    def __init__(
            self,
            node_id: int
    ):
        with dpg.stage() as _staging_container_id:
            with dpg.node(label="Multiplexer", show=False) as _id:
                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Output
                ) as self.out_attr:
                    with dpg.group(horizontal=True):
                        dpg.add_text("Number of Inputs: ")
                        self.widget = dpg.add_text("0")
                        with dpg.group(horizontal=False):
                            dpg.add_button(arrow=True, direction=dpg.mvDir_Up,
                                           callback=self.add_input_cb)
                            dpg.add_button(arrow=True,
                                           direction=dpg.mvDir_Down,
                                           callback=self.remove_input_cb)

        super().__init__(node_id, _id, _staging_container_id, [],
                         [self.out_attr])

    @staticmethod
    def disp_name():
        return 'Multiplexer'

    def add_input_cb(self, sender, appdata, userdata) -> int | str:
        with dpg.node_attribute(
                label="Node A2",
                attribute_type=dpg.mvNode_Attr_Input,
                parent=self.dpg_id) as attr:
            dpg.add_text('Input')

        self.inputs.append(attr)
        dpg.set_value(self.widget, int(dpg.get_value(self.widget)) + 1)

        return attr

    def remove_input_cb(self, sender, appdata, userdata):
        try:
            attr_id = self.inputs.pop()
        except IndexError:
            # the list is already empty
            return

        parent = dpg.get_item_parent(self.dpg_id)
        lnks = dpg.get_item_children(parent, 0)

        for lnk in lnks:
            if dpg.get_item_configuration(lnk)['attr_2'] == attr_id:
                nodeeditor = dpg.get_item_user_data(lnk)
                nodeeditor.delink_cb(nodeeditor, lnk)

        dpg.delete_item(attr_id)
        dpg.set_value(self.widget, int(dpg.get_value(self.widget)) - 1)

    def _from_jgf(self,
                  metadata: dict,
                  in_attrs: list[JNode],
                  out_attrs: list[JNode]):

        for _ in in_attrs:
            self.add_input_cb(None, None, None)


class MuxN(RNode):
    def __init__(
            self,
            node_id: int,
            nr_inputs: int,
            inode: MuxG | None,
    ):
        assert isinstance(inode, MuxG | None)
        super().__init__(node_id, nr_inputs, 1, inode)

        self.inode: MuxG | None = inode
        self.active_input = 0

    @staticmethod
    def create_from_inode(inode: MuxG) -> 'RNode':
        assert isinstance(inode, MuxG)
        return MuxN(
            inode.node_id,
            len(inode.inputs),

            inode,
        )

    def process(self, inputs: list[deque[BBPacket]],
                outputs: list[list[BBPacket]]):
        pkt: BBPacket = inputs[self.active_input].popleft()
        self.active_input = (self.active_input + 1) % self.nr_inputs

        outputs[0].append(pkt)

    def is_ready(self, inputs: list[deque[BBPacket]]) -> bool:
        if len(inputs[self.active_input]) > 0:
            return True
        else:
            return False


NodeBuilder.register_node(MuxG, MuxN)
NodeBuilder.register_node(DeMuxG, DeMuxN)
dpg.destroy_context()
