# Developer documentation
This is a quick overview of the codebase to get you familiar with where to look for specific logic.

The current code lives under the `realsense` directory and is a Python module. To run it,
you can clone the Git repository and use `python -m realsense` as a command line tool. For
further information on the flags that the command line tool accepts, run the tool with `-h`
or look at `cli.py` for specifics on the argument parser.

## Required packages
Install the requirements.txt or look at the requirements.txt and install the packages listed.
For now, the list is the following (please consult the actual file for up-to-date packages):
- matplotlib
- numpy
- python-uinput (if on Linux)

## Control flow
The current logic of the program is as follows:
- Entrypoint at `cli.py` under `cli_main`
- After arguments are parsed, a `Plotter` instance is created and ran
- The `Plotter` loads optional calibration and recording data in its `__init__`
  method and instantiates an instance of a class that implements the `DataSource` abstract class.
- The `DataSource` is ran, which updates the plot with data it has read.
- The `DataSource` finishes, and the `Plotter` either stops updating interactively or loads another `DataSource`.

## Classes of interest
### Plotter
The plotter manages an instance of a matplotlib figure along with some computation if it has been calibrated.
Position data from the data source is plotted on a 3D graph, and projected onto a 2D graph if calibration
data is available. The plotter also provides two buttons to reset the data (if recording live data)
and (re)calibrate the projection plane.

### Data sources
Data sources provide the plotter with position data. Currently there are two sources of data available:
- A `FileSource` that reads data from a CSV file.
- A `SocketSource` that receives data from the RealSense-ToolTracker application.


## File structure
The current file structure is as follows:
- `cli.py` - Command line interface, parses arguments and creates a plotter.
- `plot.py` - `Plotter` class, as described in the classes of interest. In short, manages a matplotlib figure.
- `source.py` - `DataSource` class, also described in the classes of interest. In short, an abstract class
  that provides a `Plotter` with position data.
- `record.py` - `SocketSource` class that implements `DataSource`, receives position data from a UDP socket.
- `replay.py` - `FileSource` class that implements `DataSource`, reads position data from a CSV file.
- `types.py` - Shared types like `Position` (which represents position data that the plotter receives)
  and `RecordingRow` (which describes what each row of the CSV file in the `FileSource` looks like).
