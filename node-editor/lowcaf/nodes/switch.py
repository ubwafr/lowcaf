from multiprocessing.connection import Connection

import dearpygui.dearpygui as dpg
from scapy.all import *

from lowcaf.nodeeditor.nodebuilder import NodeBuilder
from lowcaf.nodes.ifaces.inode import INode
from lowcaf.nodes.ifaces.rnode import RNode
from lowcaf.nodes.jgf.jnode import JNode
from lowcaf.packetprocessing.bbpacket import BBPacket


class SwitchG(INode):

    def __init__(
            self,
            node_id: int
    ):
        self.out_matchers = []

        with dpg.stage() as _staging_container_id:
            with dpg.node(label="Switch", show=False) as _id:
                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Static,
                ) as self.static:
                    with dpg.table(policy=dpg.mvTable_SizingFixedFit,
                                   header_row=False):
                        dpg.add_table_column()
                        dpg.add_table_column()

                        with dpg.table_row():
                            dpg.add_text('Layer Name:')
                            self.layer = dpg.add_input_text(
                                hint='Enter the layer identifier',
                                width=200
                            )

                        with dpg.table_row():
                            dpg.add_text('Field Name:')
                            self.field = dpg.add_input_text(
                                hint='Enter the field identifier',
                                width=200
                            )

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

                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Output
                ) as self.default_out:
                    dpg.add_text('Default Output')

        super().__init__(node_id,
                         _id, _staging_container_id,
                         [self.in_attr],
                         [self.default_out])

    @staticmethod
    def disp_name():
        return 'Switch Node'

    def add_output_cb(self, sender, appdata, userdata):
        with dpg.node_attribute(
                label="Node A2",
                attribute_type=dpg.mvNode_Attr_Output,
                parent=self.dpg_id) as attr:
            matcher = dpg.add_input_text(
                hint='Match Val',
                width=200,
            )

        self.out_matchers.append(matcher)
        self.outputs.append(attr)
        dpg.set_value(self.widget, int(dpg.get_value(self.widget)) + 1)
        return attr

    def remove_output_cb(self, sender, appdata, userdata):
        try:
            if len(self.outputs) > 1:
                self.out_matchers.pop()
                attr_id = self.outputs.pop()
            else:
                return
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
            'layer': dpg.get_value(self.layer),
            'field': dpg.get_value(self.field),
            'out_matchers': [dpg.get_value(x) for x in self.out_matchers]
        }

    def _from_jgf(self,
                  metadata: dict,
                  in_attrs: list[JNode],
                  out_attrs: list[JNode]):

        dpg.set_value(self.layer, metadata['layer'])
        dpg.set_value(self.field, metadata['field'])

        for _ in out_attrs[1:]:
            self.add_output_cb(None, None, None)

        for val, matcher in zip(metadata['out_matchers'], self.out_matchers):
            dpg.set_value(matcher, val)


class SwitchN(RNode):
    def __init__(
            self,
            node_id: int,
            nr_outputs: int,
            inode: SwitchG | None,
            layer: str,
            field: str,
            out_matchers: list[str]
    ):
        assert isinstance(inode, SwitchG | None)
        super().__init__(node_id, 1, nr_outputs)

        self.inode: SwitchG | None = inode

        assert isinstance(layer, str)
        assert isinstance(field, str)
        assert isinstance(out_matchers, list)

        self.layer: str = layer
        self.field: str = field
        self.out_matchers: list[str] = out_matchers

        self._tmp_dict = {}

    @staticmethod
    def create_from_inode(inode: SwitchG) -> 'RNode':
        assert isinstance(inode, SwitchG)
        return SwitchN(
            inode.node_id,
            len(inode.outputs),
            inode,
            dpg.get_value(inode.layer),
            dpg.get_value(inode.field),
            [dpg.get_value(x) for x in inode.out_matchers]
        )

    def process(
            self,
            inputs: list[deque[BBPacket]],
            outputs: list[list[BBPacket]]):
        pkt: BBPacket = inputs[0].popleft()

        import scapy.contrib.loraphy2wan

        ssp = pkt.scapy_pkt
        scapy_pkt = ssp.getlayer(self.layer)

        try:
            comp = scapy_pkt.getfieldval(self.field)
            try:
                self._tmp_dict[comp] += 1
            except KeyError:
                self._tmp_dict[comp] = 1
        except AttributeError as e:
            ssp.show()
            raise AttributeError(f'{self.field} not present. See add output') \
                from e

        for i, matcher in enumerate(self.out_matchers):
            if matcher == str(comp):
                outputs[i + 1].append(pkt)
                break

        else:
            outputs[0].append(pkt)

    def is_ready(self, inputs: list[deque]) -> bool:
        return len(inputs[0]) >= 1

    def setup(self, reg_socks: Callable[[str, int, int], Connection]):
        if '' in [dpg.get_value(x) for x in self.out_matchers]:
            raise RuntimeError(
                f'Field {self.inode.disp_name()} ({self.inode.dpg_id}) has matchers which '
                f'are empty'
            )


NodeBuilder.register_node(SwitchG, SwitchN)

