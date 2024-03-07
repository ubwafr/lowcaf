class LinkManager:
    """
    Keeps track of links between nodes.
    """

    def __init__(self):
        self._links = set()

    def add_link(self, lnk: int):
        assert isinstance(lnk, int)
        self._links.add(lnk)

    def remove_link(self, lnk: int):
        assert isinstance(lnk, int)
        self._links.remove(lnk)

    def get_links(self):
        for lnk in self._links:
            yield lnk

