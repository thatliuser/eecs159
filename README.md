# ZotPen
A cheap OCR tool for classrooms

## Requirements
If you actually want to record data, you need the following:
- The RealSense tool tracker from [here](https://github.com/stytim/RealSense-ToolTracker/) for the realsense
  module to intake data from.
- The Intel RealSense D415 camera.
- 3D printed bracket for a marker with reflective tape on it.

Otherwise, we have pre-recorded data available in the samples subdirectory.

## Running
If you are using an actual marker, first make sure that the tool tracker is running, then
run `python -m realsense` in the root directory.

If you're just running a sample, run `python -m realsense -f <sample>` to replay the sample.
If you want to see the 2D projection (currently not animated), run `python -m realsense -f <sample> -na`.
