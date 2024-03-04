import dearpygui.dearpygui as dpg
from abc import ABC, abstractmethod

from lowcaf.nodes.jgf.jedge import JEdge
from lowcaf.nodes.jgf.jfgkeys import JEDGE_REL_ATTR_NODE, JEDGE_REL_NODE_ATTR, \
    JNODE_ATTR_ID
from lowcaf.nodes.jgf.jnode import JNode


class INode(ABC):

    def __init__(self,
                 node_id: int,
                 dpg_id: str | int,
                 staging_container_id: str | int,
                 inputs: list[int],
                 outputs: list[int]):
        """
        A generic interface for all nodes supported by our Nodeeditor
        """
        self.node_id: int = node_id
        self.dpg_id: int | str = dpg_id
        self._staging_container_id: int | str = staging_container_id
        self.inputs: list[int] = inputs
        self.outputs: list[int] = outputs

        # bind right click menu for nodes
        dpg.bind_item_handler_registry(self.dpg_id, 'node_handler')

        label = dpg.get_item_label(self.dpg_id)
        dpg.set_item_label(self.dpg_id, f'{label}: {self.node_id}')

        with dpg.window(modal=True, show=False,
                        no_title_bar=True) as self._right_click:
            self._del_button = dpg.add_button(
                label="Delete Node",
                callback=self._delete_cb
            )
            dpg.add_separator()
            dpg.add_button(label="Cancel",
                           callback=self._hide_right_click_cb)

    @staticmethod
    @abstractmethod
    def disp_name() -> str:
        """
        The display name is the name that is shown to the user as the
        name of this block. It should be descriptive and easily recognizable.

        Returns:
            str: a display name
        """
        raise NotImplementedError

    @classmethod
    def type_name(cls):
        return cls.__name__

    def _delete_cb(self, sender, appdata, userdata):
        dpg.configure_item(self._right_click, show=False)
        dpg.delete_item(self._right_click)

        userdata(self.dpg_id)

    def _hide_right_click_cb(self):
        dpg.configure_item(self._right_click, show=False)

    def submit(self, parent):
        dpg.push_container_stack(parent)
        dpg.unstage(self._staging_container_id)
        dpg.pop_container_stack()

    def show(self, dpcm: int, pos: list[int] = None):
        """
        Shows this node at a given position.

        Args:
            dpcm: dots per centimeter
            pos: Position where this node should be shown
        """
        if pos is not None:
            dpg.configure_item(self.dpg_id, pos=pos)

        self._show(dpcm)
        dpg.show_item(self.dpg_id)

    def _show(self, dpcm: int):
        """
        This function can be overriden by node instances to update the size
        widgets

        Args:
            dpcm: dots per centimeter
        """
        pass

    def right_click_cb(self, remove_node_fn):
        """
        Displays the right-click menu for a node. Currently just for demo.
        """
        config = dpg.get_item_configuration(self._right_click)
        # if True:
        if not config['show']:
            dpg.configure_item(self._right_click, show=True,
                               pos=dpg.get_mouse_pos(local=False))
            dpg.set_item_user_data(self._del_button, remove_node_fn)
        else:
            dpg.configure_item(self._right_click, show=False)

    # noinspection PyMethodMayBeStatic
    def _add_meta_data_in_attr(self, idx: int) -> dict | None:
        return None

    # noinspection PyMethodMayBeStatic
    def _add_meta_data_out_attr(self, idx: int) -> dict | None:
        return None

    # noinspection PyMethodMayBeStatic
    def _add_meta_data(self) -> dict:
        return {}

    def _to_jgf(self) -> tuple[JNode, list[JNode], list[JNode]]:
        main = JNode(self.node_id, self.disp_name(), self.type_name(),
                     dpg.get_item_pos(self.dpg_id), self._add_meta_data())

        in_attrs = []
        for idx, att in enumerate(self.inputs):
            in_attrs.append(JNode.init_attr(
                att,
                idx,
                self._add_meta_data_in_attr(idx)
            ))

        out_attrs = []
        for idx, att in enumerate(self.outputs):
            out_attrs.append(JNode.init_attr(
                att,
                idx,
                self._add_meta_data_out_attr(idx)
            ))

        return main, in_attrs, out_attrs

    def to_jgf(self) -> tuple[dict, list]:
        """
        Each node should be able to export itself into the JSON Graph
        Format, aka JGF. See https://jsongraphformat.info/

        This is the *Edge with Metadata* variant.

        Returns:
            (nodes, edges) where nodes is a dict containing nodes and edges
            is a list containing edges
        """
        main, in_attrs, out_attrs = self._to_jgf()
        nodes = main.to_jgf()
        edges = []

        for node in in_attrs:
            nodes |= node.to_jgf()
            edges.append(JEdge(
                node.node_id, self.node_id, JEDGE_REL_ATTR_NODE).to_jgf())

        for node in out_attrs:
            nodes |= node.to_jgf()
            edges.append(JEdge(
                self.node_id, node.node_id, JEDGE_REL_NODE_ATTR).to_jgf())

        return nodes, edges

    def _from_jgf(self,
                  metadata: dict,
                  in_attrs: list[JNode],
                  out_attrs: list[JNode]):
        """
        If this object needs to further initialization, this could be performed
        here.
        """
        pass

    def from_jgf(self,
                 node: JNode,
                 in_attrs: list[JNode],
                 out_attrs: list[JNode],
                 id_mapping: dict[int, int]) -> 'INode':

        id_mapping[node.node_id] = self.node_id

        # we need to sort inputs and outputs, as their ordering in jgf is
        # not guaranteed
        in_attrs = sorted(in_attrs, key=lambda x: x.add_metadata[
            JNODE_ATTR_ID])
        out_attrs = sorted(out_attrs, key=lambda x: x.add_metadata[
            JNODE_ATTR_ID])

        self._from_jgf(node.add_metadata, in_attrs, out_attrs)

        print(self.disp_name())
        print(in_attrs)
        for idx, in_attr in enumerate(in_attrs):
            id_mapping[in_attr.node_id] = self.inputs[idx]

        for idx, out_attr in enumerate(out_attrs):
            id_mapping[out_attr.node_id] = self.outputs[idx]

        return self

    def update(self, data: dict):
        pass

