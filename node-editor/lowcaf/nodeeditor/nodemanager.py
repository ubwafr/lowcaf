from lowcaf.nodes.ifaces.inode import INode


class NodeManager:

    def __init__(self):
        self._dpg2inode: dict[int, INode] = {}
        self._node_id2inode: dict[int, INode] = {}

    def add_node(
            self,
            inode: INode,
    ):
        self._node_id2inode[inode.node_id] = inode
        self._dpg2inode[inode.dpg_id] = inode

    def rem_dpg(self, dpg_id: int):
        ret = self._dpg2inode[dpg_id]
        node_id = ret.node_id

        del self._dpg2inode[dpg_id]
        del self._node_id2inode[node_id]

    def rem_node_id(self, node_id: int):
        ret = self._node_id2inode[node_id]
        dpg_id = ret.dpg_id

        del self._dpg2inode[dpg_id]
        del self._node_id2inode[node_id]

    def get_dpg(self, dpg_id: int):
        return self._dpg2inode[dpg_id]

    def get_node_id(self, node_id: int):
        return self._node_id2inode[node_id]

    def values(self):
        for value in self._node_id2inode.values():
            yield value

    def items(self):
        for node_id in self._node_id2inode:
            inode = self._node_id2inode[node_id]
            yield (inode.node_id, inode.dpg_id), inode

    def cpy_node_id_dict(self):
        return self._node_id2inode.copy()

    def get_free_node_id(self):
        """
        Returns a currently unused node_id
        """
        node_ids = self._node_id2inode.keys()
        node_id = 0
        while True:
            if node_id not in node_ids:
                return node_id
            else:
                node_id += 1

    def is_node_id_free(self, node_id: int) -> bool:
        """
        Returns true if the requested node_id is currently free and can be used
        """
        return node_id not in self._node_id2inode.keys()