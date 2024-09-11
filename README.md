# Welcome to Lowcaf: A Low-Code Protocol Analysis Framework

The Lowcaf Framework allows you to visually analyze communication protocols. In order to make protocol analysis more comprehensible, Lowcaf proposes a low-code-based approach. It allows a native integration of data visualization and a load/store architecture for protocol analysis toolchains and scenarios. Lowcaf also allows manipulating communication traffic in a low-code-based approach. Protocol analysis or manipulation functions can be chained in a row via visually represented and configurable graph nodes.


This repository consists of two parts:
- The Python-based node editor
- An ns-3 application that connects to the node editor (see the respective [README](./ns-3-connector-app/README.md))


## The Lowcaf Node Editor


### Installation of the Node Editor
1. Clone this repository
~~~bash
git clone https://github.com/ubwafr/lowcaf.git
~~~
2. Python dependencies are easiest installed via Poetry (but you can of course any other dependency manager or just plain pip). Download Poetry from https://python-poetry.org/.
3. Navigate to the subdirectory and create a virtual environment
~~~bash
cd node-editor
poetry shell
poetry install
exit
~~~
4. You can now launch the application by running:
~~~bash
cd node-editor
poetry shell      # activate the virtual environment
python -m lowcaf  # run the module
~~~

### Usage of the Node Editor
When launching the Node Editor a window with an initially empty node area appears. You can populate this area either by loading an existing JGF file or by manually adding new nodes.

- Adding nodes: Hover over the node area with the mouse and press `CMD + A` to open a drop-down menu.
- Deleting nodes: Right click the title bar of a node and select `Delete Node`
- Running the simulation: Click `File -> RunBBPacket Processor`
- Loading nodes: `File -> Import Nodes`
- Exporting nodes: `File -> Export Nodes`

**A Note on Privacy:** The JGF files are meant to be shared. However, be aware that certain nodes store absolute file paths, e.g., the nodes for writing or reading PCAPs.

A few small JGF files can be found in the `node-editor/examples` directory.
