"""
Script to throw out all audio except japanese and convert (english!) subs to something
my LG tv supports and enable it by default

Script requires you have installed ffmpeg, mkvextract, mkvmerge and subtitleedit
"""
import argparse
from pathlib import Path
import subprocess
import json
from typing import *


SUBS_DIR_NAME = "1_converted_subs"
OUT_DIR_NAME = "2_filtered_video"
OUT_DIR_NAME_2 = "3_converted_video"


def existing_directory(path: str) -> Path:
    path = Path(path)
    if not path.is_dir():
        raise argparse.ArgumentTypeError(f"'{path}' is not a valid directory.")
    return path


def get_mkv_info(filepath: Path) -> dict:
    p = subprocess.run(
        ["mkvmerge", "-J", filepath.name],
        cwd=filepath.parent,
        capture_output=True,
        check=True,
    )
    print("got mkv info")
    return json.loads(p.stdout)


def get_track_ids(info: dict) -> Tuple[int, int, int]:
    video_tracks = [t for t in info["tracks"] if t["type"] == "video"]
    assert len(video_tracks) == 1

    audio_tracks = [t for t in info["tracks"] if t["type"] == "audio"]
    if len(audio_tracks) > 1:
        audio_tracks = [t for t in audio_tracks if "japanese" in t["properties"].get("track_name", "").lower()]
    assert len(audio_tracks) == 1

    sub_tracks = [t for t in info["tracks"] if t["type"] == "subtitles"]
    if len(sub_tracks) > 1:
        sub_tracks = [
            t for t in sub_tracks if (
                "eng" in t["properties"].get("language", "").lower() or 
                "english" in t["properties"].get("track_name", "").lower()
            )
        ]
    if len(sub_tracks) > 1:
        sub_tracks = [sorted(sub_tracks, key=lambda t: t["properties"].get("num_index_entries", 0), reverse=True)[0]]
    assert len(sub_tracks) == 1

    print("got track ids")
    return video_tracks[0]["id"], audio_tracks[0]["id"], sub_tracks[0]["id"]


def extract_subs(filepath: Path, track: int, force: bool) -> Path:
    sub_filepath = filepath.parent / SUBS_DIR_NAME / filepath.with_suffix(".sup").name
    if not sub_filepath.exists() or force:
        subprocess.run(
            ["mkvextract", "tracks", filepath.name, f"{track}:{SUBS_DIR_NAME}/{sub_filepath.name}"],
            cwd=filepath.parent,
            check=True,
        )
        assert sub_filepath.exists()
    else:
        print("subs already extracted")
    return sub_filepath


def convert_subs(filepath: Path, force: bool) -> Path:
    new_filepath = filepath.parent / filepath.with_suffix(".ass").name
    if not new_filepath.exists() or force:
        subprocess.run(
            ["SubtitleEdit", "/convert", filepath.name, "AdvancedSubStationAlpha"],
            cwd=filepath.parent,
            check=True,
        )
        assert new_filepath.exists()
    else:
        print("subs already converted")
    return new_filepath


def create_mkv(mkv: Path, ass: Path, video_track: int, audio_track: int, force: bool) -> Path:
    new_filepath = mkv.parent / OUT_DIR_NAME / mkv.name
    if not new_filepath.exists() or force:
        subprocess.run(
            [
                "mkvmerge",
                "-o",
                f"{OUT_DIR_NAME}/{mkv.name}",
                "--audio-tracks",
                f"{audio_track}",
                "--no-subtitles",
                "--default-track",
                f"{audio_track}:yes",
                mkv.name,
                f"{SUBS_DIR_NAME}/{ass.name}",
                "--default-track",
                "0:yes",
                "--forced-track",
                "0:yes",
            ],
            cwd=mkv.parent,
            check=True,
        )
        assert new_filepath.exists()
    else:
        print("new mkv already created")
    return new_filepath


def convert_mkv(mkv: Path, force: bool) -> Path:
    new_filepath = mkv.parent.parent / OUT_DIR_NAME_2 / mkv.name
    if not new_filepath.exists() or force:
        subprocess.run(
            [
                "ffmpeg",
                "-i",
                f"{OUT_DIR_NAME}/{mkv.name}",
                "-map",
                "0:v:0",
                "-map",
                "0:a",
                "-map",
                "0:s",
                "-map",
                "-0:t",
                "-c:v",
                "hevc_nvenc",
                "-pix_fmt",
                "yuv420p",
                "-preset",
                "slow",
                "-crf",
                "23",
                "-c:a",
                "ac3",
                "-b:a",
                "192k",
                "-c:s",
                "copy",
                f"{OUT_DIR_NAME_2}/{mkv.name}",
            ],
            cwd=mkv.parent.parent,
            check=True,
        )
        assert new_filepath.exists()
    else:
        print("new mkv already created")
    return new_filepath


def _main(dir: Path, reencode: bool=False, debug: bool=False, force: bool=False) -> None:
    (dir / OUT_DIR_NAME).mkdir(parents=True, exist_ok=True)
    (dir / OUT_DIR_NAME_2).mkdir(parents=True, exist_ok=True)
    (dir / SUBS_DIR_NAME).mkdir(parents=True, exist_ok=True)

    src_mkvs = list(dir.glob("*.mkv"))
    for i, mkv in enumerate(src_mkvs):
        print(f"+ {i+1}/{len(src_mkvs)} {mkv.name}")
        info = get_mkv_info(mkv)
        video_track, audio_track, sub_track = get_track_ids(info)
        sup = extract_subs(mkv, sub_track, force)
        ass = convert_subs(sup, force)
        new_mkv = create_mkv(mkv, ass, video_track, audio_track, force)
        if reencode:
            new_mkv = convert_mkv(new_mkv, force)
        if debug:
            print("[debug] exit early")
            break


def main() -> None:
    parser = argparse.ArgumentParser(description="Provide a folder path.")
    parser.add_argument(
        "dir",
        type=existing_directory,
        help="The path to the videos.",
    )
    parser.add_argument(
        "-d, --debug",
        dest="debug",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-f, --force",
        dest="force",
        action="store_true",
        default=False,
    )
    parser.add_argument(
        "-r, --reencode",
        dest="reencode",
        action="store_true",
        default=False,
    )
    args = parser.parse_args()
    _main(args.dir, args.reencode, args.debug, args.force)


if __name__ == "__main__":
    main()
