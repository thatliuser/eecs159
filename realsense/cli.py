from argparse import ArgumentParser
from .plot import Plotter


def cli_main():
    top = ArgumentParser(
        prog="realsense_cli", description="Plot RealSense tool position with Matplotlib"
    )
    sub = top.add_subparsers(
        required=True, help="Which mode to use (record or replay)."
    )
    top.add_argument(
        "-f",
        "--file",
        help="Specify a file to record to or replay from.",
        default="recording.csv",
    )
    top.add_argument(
        "-cf",
        "--calibrate-file",
        default="calibrate.csv",
        help="Specify a file with a calibration replay. If it doesn't exist, the calibration is skipped.",
    )
    top.add_argument(
        "-ca",
        "--calibrate-anim",
        action="store_true",
        default=False,
        help="Whether to replay the calibration file as an animation",
    )
    sub.add_parser("record", help="Record a tool in realtime")
    rep = sub.add_parser("replay", help="Replay a tool from a file")
    rep.add_argument(
        "-na",
        "--no-anim",
        action="store_true",
        default=False,
        help="In replay mode, whether or not to animate the sequence.",
    )
    args = top.parse_args()

    anim = not args.no_anim if hasattr(args, "no_anim") else None

    plot = Plotter(
        args.calibrate_file,
        args.file,
        args.calibrate_anim,
        anim,
    )
    plot.run()
