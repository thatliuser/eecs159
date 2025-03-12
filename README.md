# ZotPen
A cheap OCR tool for classrooms.

## Developer documentation
See [here.](./CONTRIBUTING.md)

## Requirements
If you actually want to record data, you need the following:
- The RealSense tool tracker from [here](https://github.com/stytim/RealSense-ToolTracker/) for the realsense
  module to intake data from.
- The Intel RealSense D415 camera.
- 3D printed bracket for a marker with reflective tape on it.

Otherwise, we have pre-recorded data available in the samples subdirectory.

## Running
Run `pip install -r requirements.txt` to install dependencies.

If you are using an actual marker, first make sure that the tool tracker is running, then
run `python -m realsense record` in the root directory.

If you're just running a sample, run `python -m realsense -f <sample> replay` to replay the sample.
If you want to see the 2D projection (currently not animated), you need to specify a calibration file:
run `python -m realsense -cf <calibration_file> -f <sample> replay`. For example, you can run
`python -m realsense -cf samples/calibrate.csv -f samples/eric.csv replay`, which shows the following output:

![Output of the sample `eric.csv`.](./samples/eric-out.png)
