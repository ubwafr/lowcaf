import logging

import dearpygui.dearpygui as dpg

from lowcaf.nodeeditor.linkmanager import LinkManager
from lowcaf.nodeeditor.nodemanager import NodeManager

LOGGER = logging.getLogger(__name__)


class NodePlane:
    def __init__(self, dpg_id: int | str):
        self.dpg_id: int | str = dpg_id
        self.node_mngr: NodeManager = NodeManager()
        self.link_mngr: LinkManager = LinkManager()

    def remove_node(self, node_dpg_id: int):
        """
        Completely and safely removes a node

        This function also takes care of links to this node
        """
        LOGGER.debug(f'Removing node DPG ID: {node_dpg_id}')
        self.node_mngr.rem_dpg(node_dpg_id)

        node_editor_dpg_id = dpg.get_item_parent(node_dpg_id)

        # links are stored for the node_editor as a whole
        lnks = dpg.get_item_children(node_editor_dpg_id, 0)

        # the attributes of the nodes are the connector points for links
        attrs = dpg.get_item_children(node_dpg_id, 1)

        for lnk in lnks:
            lnk_conf = dpg.get_item_configuration(lnk)
            for attr in attrs:
                if lnk_conf['attr_2'] == attr or lnk_conf['attr_1'] == attr:
                    self.link_mngr.delink(lnk)

        dpg.configure_item(node_dpg_id, show=False)
        dpg.delete_item(node_dpg_id)
