import logging
import subprocess
from collections import deque
from multiprocessing.connection import Connection
from typing import Callable

import dearpygui.dearpygui as dpg
from scapy.layers.tuntap import TunTapInterface

from lowcaf.nodeeditor.nodebuilder import NodeBuilder
from lowcaf.nodes.ifaces.inode import INode
from lowcaf.nodes.ifaces.rnode import RNode
from lowcaf.nodes.jgf.jnode import JNode
from lowcaf.packetprocessing.bbpacket import BBPacket

LOGGER = logging.getLogger(__name__)


class TunTapG(INode):

    def __init__(
            self,
            node_id: int,
    ):
        # Graphical representation
        with dpg.stage() as _staging_container_id:
            with dpg.node(label="TunTap", show=False) as _id:
                with dpg.node_attribute(
                        label="Node A2",
                        attribute_type=dpg.mvNode_Attr_Input) as self.att_in:
                    self.mode_dpg = dpg.add_radio_button(
                        ('TUN', 'TAP'), default_value='TAP',
                        horizontal=True)

                    with dpg.table(header_row=False, policy=dpg.mvTable_SizingFixedFit):
                        dpg.add_table_column()
                        dpg.add_table_column()

                        with dpg.table_row():
                            dpg.add_text('TUN/TAP name:')
                            self.if_name_dpg = dpg.add_input_text(
                                default_value='tap0', width=200)
                        with dpg.table_row():
                            dpg.add_text('IP adapter:')
                            self.ip_iface_dpg = dpg.add_input_text(
                                default_value='10.0.0.2', width=200)
                        with dpg.table_row():
                            dpg.add_text('IP app:')
                            self.ip_app_dpg = dpg.add_input_text(
                                default_value='10.0.0.3', width=200)

        super().__init__(node_id, _id, _staging_container_id, [self.att_in],
                         [])

    @staticmethod
    def disp_name() -> str:
        return "TunTap"

    def _add_meta_data(self) -> dict:
        return {
            'mode_dpg': dpg.get_value(self.mode_dpg),
            'if_name_dpg': dpg.get_value(self.if_name_dpg),
            'ip_iface_dpg': dpg.get_value(self.ip_iface_dpg),
            'ip_app_dpg': dpg.get_value(self.ip_app_dpg),
        }

    def _from_jgf(self,
                  metadata: dict,
                  in_attrs: list[JNode],
                  out_attrs: list[JNode]):
        dpg.set_value(self.mode_dpg, metadata['mode_dpg'])
        dpg.set_value(self.if_name_dpg, metadata['if_name_dpg'])
        dpg.set_value(self.ip_iface_dpg, metadata['ip_iface_dpg'])
        dpg.set_value(self.ip_app_dpg, metadata['ip_app_dpg'])


class TunTapN(RNode):
    def __init__(
            self,
            node_id: int,
            if_name: str,
            ip_iface: str,
            ip_app: str,
            inode: TunTapG | None = None,
            mode_tun: bool = False
    ):
        assert isinstance(inode, TunTapG | None)
        super().__init__(node_id, 1, 0, inode)

        self.if_name: str = if_name
        self.ip_iface: str = ip_iface
        self.ip_app: str = ip_app
        self.interface: TunTapInterface | None = None
        self.mode_tun: bool = mode_tun

    def process(self, inputs: list[deque[BBPacket]],
                outputs: list[list[BBPacket]]):
        pkt: BBPacket = inputs[0].popleft()

        LOGGER.debug(f"Sending packet to TUN/TAP")
        self.interface.send(pkt.scapy_pkt)

    def is_ready(self, inputs: list[deque[BBPacket]]) -> bool:
        return len(inputs[0]) >= 1

    def setup(self, reg_socks: Callable[[str, int, int], Connection]):
        self.interface = TunTapInterface(self.if_name, self.mode_tun)

        if self.mode_tun:
            subprocess.run(['ip', 'link', 'set', 'dev', self.if_name, 'up'])
            subprocess.run(
                ['ip', 'a', 'add', self.ip_iface, 'peer', self.ip_app, 'dev',
                 'tun0'])
        else:

            # set up the TAP device
            subprocess.run(['ip', 'link', 'set', 'dev', self.if_name,
                            'up'])
            subprocess.run(
                ['ip', 'link', 'set', 'address', 'aa:aa:aa:aa:aa:aa', 'dev',
                 self.if_name])

    def teardown(self):
        self.interface.close()

    @staticmethod
    def create_from_inode(inode: TunTapG) -> 'RNode':
        assert isinstance(inode, TunTapG)

        mapping = {
            'TUN': True,
            'TAP': False,
        }

        val = dpg.get_value(inode.mode_dpg)
        mode_tun = mapping[val]

        return TunTapN(
            inode.node_id,
            dpg.get_value(inode.if_name_dpg),
            dpg.get_value(inode.ip_iface_dpg),
            dpg.get_value(inode.ip_app_dpg),
            inode,
            mode_tun
        )


NodeBuilder.register_node(TunTapG, TunTapN)
