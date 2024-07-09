import argparse
import numpy as np
import pandas as pd
from tqdm import tqdm
from sstcam_waveform.io import EventFileReader, EventFileWriter
from sstcam_analysis.io.waveform import WaveformReader, WaveformEvent
from sstcam_analysis.config import Configuration
from pathlib import Path
import yaml
from numba import njit, prange, float64, float32, int64
from IPython import embed
from sstcam_waveform.descriptions import create_waveform_event_r1_from_samples
from typing import Optional, List


@njit(fastmath=True, parallel=True)
def JITApplyBlkDepDCTF_pedshape(
    dc_tf,
    waveforms,
    fci,
    min_chn=0,
    max_chn=64,
    ADC_step=32,
    lower_bound=-256,
    upper_bound=3584,
):
    fblock = fci // 32
    fblock_phase = fci % 32
    for chn in prange(min_chn, max_chn):
        for cell in prange(int(waveforms.shape[1])):
            fbpisam = fblock_phase + cell  # fbp firstblockphase
            index = int((waveforms[chn, cell] + np.abs(lower_bound)) // ADC_step)
            # if only for last entry in tf -> build slope with next point as there is none
            if index > int((np.abs(lower_bound) + upper_bound) / ADC_step + 0.5) - 1:
                index -= 1
            slope = (
                dc_tf[chn, fblock, fbpisam, index + 1]
                - dc_tf[chn, fblock, fbpisam, index]
            ) / ADC_step
            waveforms[chn, cell] = dc_tf[chn, fblock, fbpisam, index] + slope * (
                (waveforms[chn, cell]) % ADC_step
            )
    return waveforms


def process_file(input_path: Path, output_path: Path, DC_TF: List["float"]):
    """
    Process data from an input file pedestal subtracted file, applying DC TF, and write
    to an output .tio file.

    Parameters
    ----------
    input_path : Path
        Path to the input file.
    output_path : Path
        Path to the output file.
    DC_TF : List[float]
        List of floats representing the DC transfer functions for calibration.
    """
    with EventFileReader(path=str(input_path)) as reader:
        header = reader.file_header
        n_packets_per_event = reader.n_packets_per_event
        packet_size = reader.packet_size

        # Specify R1 file parameters
        header.is_r1 = True
        header.scale = reader.scale
        header.offset = reader.offset

        print(f"scale = {reader.scale}")
        print(f"offset = {reader.offset}")

        with EventFileWriter(
            path=str(output_path),
            n_packets_per_event=n_packets_per_event,
            packet_size=packet_size,
            file_header=header,
        ) as writer:
            for event in tqdm(reader, total=reader.n_events):
                samples = event.get_array()

                calibrated_samples = JITApplyBlkDepDCTF_pedshape(
                    DC_TF, waveforms=np.copy(samples), fci=event.first_cell_id
                )
                # Wrap the calibrated samples into a WaveformEventR1
                calibrated_event = create_waveform_event_r1_from_samples(
                    array=calibrated_samples,
                    n_packets_per_event=n_packets_per_event,
                    n_waveforms_per_packet=event.n_waveforms_per_packet,
                    first_cell_id=event.first_cell_id,
                    tack=event.tack,
                    first_active_module_slot=event.first_active_module_slot,
                    cpu_time_second=event.cpu_time_second,
                    cpu_time_nanosecond=event.cpu_time_nanosecond,
                    index=event.index,
                    scale=header.scale,
                    offset=header.offset,
                )

                # Write the calibrated event to the file
                writer.write_event(calibrated_event)


def main():
    parser = argparse.ArgumentParser(
        description="Apply DC TFs to pedestal subtracted files",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "-f",
        "--files",
        dest="input_paths",
        nargs="+",
        help="path to the file containing waveforms (TIO or simtel)",
    )
    parser.add_argument(
        "-o",
        "--output",
        dest="output_path",
        action="store",
        help="path to store the output .tio file (OPTIONAL, will be "
        "automatically set if not specified)",
    )
    parser.add_argument(
        "-c", "--dctf_path", dest="dctf_path", type=Path, help="Path to DC TF file."
    )
    args = parser.parse_args()
    input_paths = args.input_paths
    n_files = len(input_paths)
    output_path = args.output_path
    dc_tf_path = args.dctf_path
    print(f"input paths = {input_paths}")
    DC_TF = np.load(dc_tf_path, allow_pickle=True)

    for i_path, input_path in enumerate(input_paths):
        if output_path is None:
            output_path = Path(str(input_path).replace(".tio", "_dc.tio"))
        print(output_path)
        print("PROGRESS: Reducing file {}/{}".format(i_path + 1, n_files))
        input_path = Path(input_path)
        process_file(input_path, output_path, DC_TF)


if __name__ == "__main__":
    main()
