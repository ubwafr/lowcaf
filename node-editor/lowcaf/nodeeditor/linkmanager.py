import dearpygui.dearpygui as dpg


class LinkManager:
    """
    Keeps track of links between nodes.
    """

    def __init__(self):
        self._links = set()

    def _add_link(self, lnk: int):
        assert isinstance(lnk, int)
        self._links.add(lnk)

    def remove_link(self, lnk: int):
        assert isinstance(lnk, int)
        self._links.remove(lnk)

    def get_links(self):
        return self._links.copy()

    def delink(self, dpg_id: int | str):
        dpg.delete_item(dpg_id)
        self.remove_link(dpg_id)

    def link(self,
             start: int | str,
             end: int | str,
             parent: int | str) -> int | str:
        """
        Add a link between two attributes.

        If there is another link to the target, the other link will be removed

        Args:
            start: ID of the start attribute
            end: ID of the end attribute
            parent: ID of the parent

        Returns:
            ID of the created link
        """

        def check_remove_lnk(link):
            if link is not None:
                self.delink(link)

        s = self._check_id_already_connected_to(start, start=True)
        e = self._check_id_already_connected_to(end, start=False)
        check_remove_lnk(s)
        check_remove_lnk(e)

        # a node link also has an ID!!
        lnk = dpg.add_node_link(start, end, parent=parent)

        self._add_link(lnk)

        return lnk

    def _check_id_already_connected_to(
            self,
            attr_id,
            start: bool
    ) -> None | str | int:
        if start:
            attr = 'attr_1'
        else:
            attr = 'attr_2'

        for link in self.get_links():
            point = dpg.get_item_configuration(link)[attr]
            if point == attr_id:
                return link
        else:
            return None
