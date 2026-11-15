#!/usr/bin/env python3
"""Generate an original offline English TTS track and mux with OBNOTE Shorts.

Uses Ubuntu's open-source eSpeak NG and imageio-ffmpeg. No uploaded voice,
music, cloud voice account, or external audio source required.
Each voice segment fits a scene and is padded to match its caption timing.
"""
import argparse
import json
from pathlib import Path
import subprocess
import wave

from imageio_ffmpeg import get_ffmpeg_exe


def wav_duration(path):
    with wave.open(str(path), "rb") as audio:
        return audio.getnframes() / audio.getframerate()


def create_voice_segments(plan, folder, executable="espeak-ng"):
    segments = plan["segments"]
    if len(segments) != 5:
        raise ValueError("Expected exactly five narration segments")
    folder.mkdir(parents=True, exist_ok=True)
    tracks = []
    durations = []
    for i, segment in enumerate(segments):
        duration = float(segment["end_seconds"]) - float(segment["start_seconds"])
        if not 0.5 <= duration <= 15:
            raise ValueError("Invalid scene duration")
        words = str(segment["narration"]).strip()
        if not words or len(words) > 240:
            raise ValueError("Narration must contain concise text")
        path = folder / f"voice-{i + 1}.wav"
        # Re-synthesize at slightly faster rates if voice exceeds the slide.
        for speed in (190, 220, 250, 280, 310):
            subprocess.run(
                [executable, "-v", "en-us", "-s", str(speed), "-w", str(path), words],
                check=True, stdout=subprocess.DEVNULL
            )
            if wav_duration(path) <= duration - 0.08:
                break
        # FFmpeg trims any unusually long text to keep the timeline in sync.
        tracks.append(path)
        durations.append(duration)
    return tracks, durations


def mux_voice(video, tracks, durations, output, ffmpeg=None):
    if len(tracks) != len(durations) or not tracks:
        raise ValueError("Voice segments must match scene durations")
    ffmpeg = ffmpeg or get_ffmpeg_exe()
    filters = []
    for i, length in enumerate(durations):
        filters.append(
            f"[{i+1}:a]aresample=44100,apad,atrim=duration={length:.3f},"
            f"asetpts=PTS-STARTPTS[a{i}]"
        )
    streams = "".join(f"[a{i}]" for i in range(len(tracks)))
    filters.append(
        streams + f"concat=n={len(tracks)}:v=0:a=1[aout]"
    )
    args = [
        ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video)
    ]
    for p in tracks:
        args += ["-i", str(p)]
    args += [
        "-filter_complex", ";".join(filters),
        "-map", "0:v:0", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
        "-t", f"{sum(durations):.3f}",
        "-movflags", "+faststart", str(output)
    ]
    subprocess.run(args, check=True)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Voiceover video was not generated")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--storyboard", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    plan = json.loads(Path(args.storyboard).read_text(encoding="utf-8"))
    video = Path(args.video)
    output = Path(args.output)
    if not video.is_file():
        raise ValueError("The silent base video must exist")
    if output.resolve() == video.resolve():
        raise ValueError("Output must not overwrite the silent source video")
    tracks, durations = create_voice_segments(plan, output.parent / "voice-wavs")
    mux_voice(video, tracks, durations, output)
    print("Created original narrated OBNOTE Shorts:", output)


if __name__ == "__main__":
    main()
