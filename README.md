# Welcome to Lowcaf: A Low-Code Protocol Analysis Framework

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