from collections import deque

import dearpygui.dearpygui as dpg

from lowcaf.nodeeditor.nodebuilder import NodeBuilder
from lowcaf.nodes.ifaces.inode import INode
from lowcaf.packetprocessing.bbpacket import BBPacket
from lowcaf.nodes.ifaces.rnode import RNode


class HistogramG(INode):

    def __init__(
            self,
            node_id: int
    ):
        self.data = {}

        with dpg.stage() as _staging_container_id:
            with dpg.node(label="Gui", show=False) as _id:
                with dpg.node_attribute() as self.in_attr:
                    with dpg.plot(label='Packet Sizes') as self.plot:
                        dpg.add_plot_legend()

                        self.x_axis = dpg.add_plot_axis(
                            dpg.mvXAxis,
                            label='Bytes Transmitted')
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
                ) as self.out_attr:
                    dpg.add_text('Output')

        super().__init__(
            node_id,
            _id,
            _staging_container_id,
            [self.in_attr],
            [self.out_attr])

    @staticmethod
    def disp_name():
        return 'Histogram'

    def _show(self, dpcm: int):
        dpg.set_item_width(self.plot, 10 * dpcm)
        dpg.set_item_height(self.plot, 5 * dpcm)

    def update(self, data: dict):
        nr_bytes = data['bytes']

        try:
            self.data[nr_bytes] = self.data[nr_bytes] + 1
        except KeyError:
            self.data[nr_bytes] = 1

        print("Histogram data")
        print(dpg.get_value(self.series))
        dpg.set_value(self.series, [list(self.data.keys()),
                                    list(self.data.values()), [],
                                    [], []])
        dpg.fit_axis_data(self.y_axis)
        dpg.fit_axis_data(self.x_axis)


class HistogramN(RNode):
    def __init__(
            self,
            node_id: int,
            inode: HistogramG | None,
    ):
        assert isinstance(inode, HistogramG | None)
        super().__init__(node_id, 1, 1, inode)

        self.inode: HistogramG | None = inode

    @staticmethod
    def create_from_inode(inode: HistogramG) -> 'RNode':
        assert isinstance(inode, HistogramG)
        return HistogramN(
            inode.node_id,
            inode,
        )

    def process(self, inputs: list[deque], outputs: list[list]):
        pkt: BBPacket = inputs[0].popleft()
        if self.inode is not None:
            self.inode.update({'bytes': len(pkt.scapy_pkt)})
        outputs[0].append(pkt)

    def is_ready(self, inputs: list[deque]) -> bool:
        return len(inputs[0]) >= 1


NodeBuilder.register_node(HistogramG, HistogramN)
