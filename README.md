# Welcome to Lowcaf: A Low-Code Protocol Analysis Framework

The Lowcaf Framework allows you to visually analyze communication protocols. In order to make protocol analysis more comprehensible, Lowcaf proposes a low-code-based approach. It allows a native integration of data visualization and a load/store architecture for protocol analysis toolchains and scenarios. Lowcaf also allows manipulating communication traffic in a low-code-based approach. Protocol analysis or manipulation functions can be chained in a row via visually represented and configurable graph nodes.


This repository consists of two parts:
- The Python-based node editor
- An ns-3 application that connects to the node editor

## Installation of the Node Editor
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
4. You can now launch the application by running `poetry run src/nodeeditor.py`
