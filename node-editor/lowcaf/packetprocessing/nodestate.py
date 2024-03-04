from collections import deque

from lowcaf.nodes.ifaces.rnode import RNode


class NodeState:
    def __init__(self, node: RNode):
        assert isinstance(node, RNode)
        self.node: RNode = node

        self.inputs: list[deque] = []
        for _ in range(self.node.nr_inputs):
            self.inputs.append(deque())

        self.outputs: list[list] = []
        for _ in range(self.node.nr_outputs):
            self.outputs.append([])

    def is_ready(self):
        return self.node.is_ready(self.inputs)

    def process(self) -> list[list]:
        return self.node.process(self.inputs, self.outputs)

    def viz(self) -> str:
        ts = ('{name}({id}):\n\tinputs: {inputs}\n\toutputs: {'
              'outputs}\n\tready? {ready}')

        return ts.format(
            id=self.node.id,
            name=type(self.node),
            inputs=str(self.inputs),
            outputs=str(self.outputs),
            ready=str(self.is_ready())
        )
