"""
The HistTime node displays inter-packet times

For this arriving packets should be tagged with their inter packet time. The
correct tag is t_diff and it should provide a float in seconds.
"""
import math
from collections import deque
from multiprocessing.connection import Connection
from typing import Callable

import dearpygui.dearpygui as dpg

from lowcaf.nodeeditor.nodebuilder import NodeBuilder
from lowcaf.nodes.ifaces.inode import INode
from lowcaf.packetprocessing.bbpacket import BBPacket
from lowcaf.nodes.ifaces.rnode import RNode


class HistTimeG(INode):

    def __init__(
            self,
            node_id: int
    ):
        self.data = {}

        with dpg.stage() as _staging_container_id:
            with dpg.node(label="Gui", show=False) as _id:
                with dpg.node_attribute() as self.in_attr:
                    with dpg.plot(label='Inter-Packet Times') as self.plot:
                        dpg.add_plot_legend()

                        self.x_axis = dpg.add_plot_axis(
                            dpg.mvXAxis,
                            label='Time Difference in [Seconds]',)
                        self.y_axis = dpg.add_plot_axis(
                            dpg.mvYAxis,
                            label='Nr. of Packets')

                        self.series = dpg.add_bar_series(
                            [],
                            [],
                            parent=self.y_axis
                        )
                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Output
                ) as self.out_attr_valid:
                    dpg.add_text('Duty Cycle Met')

                with dpg.node_attribute(
                        attribute_type=dpg.mvNode_Attr_Output
                ) as self.out_attr_invalid:
                    dpg.add_text('Duty Cycle Violation')

        super().__init__(
            node_id,
            _id,
            _staging_container_id,
            [self.in_attr],
            [self.out_attr_valid, self.out_attr_invalid])

    @staticmethod
    def disp_name():
        return 'Times'

    def _show(self, dpcm: int):
        dpg.set_item_width(self.plot, 10 * dpcm)
        dpg.set_item_height(self.plot, 5 * dpcm)

    def update(self, data: dict):
        inter_pkt_time = data['inter_pkt_time']
        inter_pkt_time = int(inter_pkt_time)

        try:
            self.data[inter_pkt_time] = self.data[inter_pkt_time] + 1
        except KeyError:
            self.data[inter_pkt_time] = 1

        dpg.set_value(self.series, [list(self.data.keys()),
                                    list(self.data.values()), [],
                                    [], []])
        dpg.fit_axis_data(self.y_axis)
        dpg.fit_axis_data(self.x_axis)


def compute_time_on_air(
        spreading_factor: int,
    bandwidth: int,
    nr_sym_preamble: int,
    header: bool,
    payload_size: int,
    low_data_rate_optimized: bool,
    coding_rate: int,
):
    """
    This function computes the time on air for a LoRa frame

    The calculation based on the formula presented [here](
    https://www.rfwireless-world.com/calculators/LoRaWAN-Airtime-calculator.html)

    Args:
        spreading_factor: from 7-12
        bandwidth: the bandwidth in Hz (125 KHz, 250 KHz, 500 KHz)
        nr_sym_preamble: number of symbols in the preamble
        header: flag indicating if a header is present
        payload_size: in bytes
        low_data_rate_optimized: flag indicating if low data rate is optimized
        coding_rate: coding rate can be set in the range 1-4
    Return:
        Time-on-air in seconds
    """

    sf = spreading_factor
    h = 1 if header else 0
    de = 1 if low_data_rate_optimized else 0
    pl = payload_size
    cr = coding_rate

    t_sym = (2**sf) / bandwidth
    payload_symb_nb = 8 + max(
        math.ceil((8*pl - 4*sf + 28 + 16 - 20*h)/(4*(sf - 2*de))) * (cr + 4),
        0)


    t_preamble = (nr_sym_preamble + 4.25) * t_sym
    t_payload = payload_symb_nb * t_sym

    t_packet = t_preamble + t_payload

    return t_packet


class HistTimeN(RNode):
    def __init__(
            self,
            node_id: int,
            inode: HistTimeG | None,
    ):
        assert isinstance(inode, HistTimeG | None)
        super().__init__(node_id, 1, 2, inode)

        self.inode: HistTimeG | None = inode
        self._last_diff: float | None = None

    @staticmethod
    def create_from_inode(inode: HistTimeG) -> 'RNode':
        assert isinstance(inode, HistTimeG)
        return HistTimeN(
            inode.node_id,
            inode,
        )

    def process(self, inputs: list[deque], outputs: list[list]):
        pkt: BBPacket = inputs[0].popleft()

        time_to_nxt: float = pkt.metadata['t_diff']
        if self.inode is not None:
            self.inode.update({'inter_pkt_time': time_to_nxt})

        lora_meta = pkt.metadata['lora_tap']
        time_on_air = compute_time_on_air(
            lora_meta['spreading_factor'],
            lora_meta['bandwidth'],
            8,
            True,
            len(pkt.scapy_pkt),
            lora_meta['bandwidth'] == 125000 and lora_meta[
                'spreading_factor'] > 10,
            lora_meta['coding_rate']
        )

        if time_to_nxt > time_on_air * 99:
            # duty cycle respected
            outputs[0].append(pkt)
        else:
            # duty cycle exceeded
            outputs[1].append(pkt)

    def is_ready(self, inputs: list[deque]) -> bool:
        return len(inputs[0]) >= 1

    def setup(self, reg_socks: Callable[[str, int, int], Connection]):
        self.inode.data = {}
        self._last_diff = None


NodeBuilder.register_node(HistTimeG, HistTimeN)
