"""Download YouTube playlists and videos as MP4 files with automatic recovery."""

from __future__ import annotations

import argparse
import hashlib
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from urllib.parse import parse_qs, urlparse


__version__ = "1.0.0"
MAX_RETRY_DELAY = 300
DEFAULT_CONCURRENT_FRAGMENTS = 8
MAX_CONCURRENT_FRAGMENTS = 16
VIDEO_ID = re.compile(r"[A-Za-z0-9_-]{11}")
YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
}
SHORT_HOSTS = {"youtu.be", "www.youtu.be"}
OUTPUT_TEMPLATE = "%(title).100B [%(id)s] (requested-{resolution}p).%(ext)s"
STAGED_VIDEO_NAME = re.compile(
    r"^(?:\d{3,} - )?(?P<title>.+) \[(?P<id>[A-Za-z0-9_-]{11})\]"
    r"(?: \(requested-\d+p\))?\.mp4$"
)


@dataclass(frozen=True)
class YouTubeSource:
    """Identify the kind of YouTube URL and its stable archive key."""

    kind: Literal["playlist", "video", "short"]
    source_id: str


def source_from_url(url: str) -> YouTubeSource:
    """Classify a YouTube playlist, video, or Short URL."""
    parsed = urlparse(url)
    host = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or host not in YOUTUBE_HOSTS | SHORT_HOSTS:
        raise ValueError("Enter a YouTube playlist, video, or Shorts URL beginning with https://")

    query = parse_qs(parsed.query, keep_blank_values=True)
    if "list" in query:
        playlist_ids = query["list"]
        if len(playlist_ids) != 1 or not playlist_ids[0]:
            raise ValueError("The list parameter must contain one playlist ID")
        return YouTubeSource("playlist", playlist_ids[0])

    parts = [part for part in parsed.path.split("/") if part]
    if host in SHORT_HOSTS and len(parts) == 1:
        video_id, kind = parts[0], "video"
    elif host in YOUTUBE_HOSTS and parts == ["watch"]:
        video_ids = query.get("v", [])
        video_id, kind = (video_ids[0] if len(video_ids) == 1 else ""), "video"
    elif host in YOUTUBE_HOSTS and len(parts) == 2 and parts[0] in {"shorts", "live", "embed"}:
        video_id = parts[1]
        kind = "short" if parts[0] == "shorts" else "video"
    else:
        raise ValueError("The URL must point to one YouTube playlist, video, or Short")
    if VIDEO_ID.fullmatch(video_id) is None:
        raise ValueError("The YouTube video URL must contain a valid video ID")
    return YouTubeSource(kind, video_id)


def positive_int(value: str) -> int:
    """Parse a positive integer for a command line option."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a positive integer") from exc
    if number < 1:
        raise argparse.ArgumentTypeError("expected a positive integer")
    return number


def nonnegative_int(value: str) -> int:
    """Parse a nonnegative integer for a command line option."""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected a nonnegative integer") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("expected a nonnegative integer")
    return number


def fragment_count(value: str) -> int:
    """Parse a supported fragment concurrency value."""
    range_error = f"expected an integer from 1 to {MAX_CONCURRENT_FRAGMENTS}"
    try:
        count = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(range_error) from exc
    if not 1 <= count <= MAX_CONCURRENT_FRAGMENTS:
        raise argparse.ArgumentTypeError(range_error)
    return count


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the URL, quality, output, and retry settings."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--version", action="version", version=f"youtube-video-downloader {__version__}"
    )
    parser.add_argument("url", help="YouTube playlist, video, or Shorts URL")
    parser.add_argument(
        "-r",
        "--resolution",
        type=positive_int,
        default=1080,
        metavar="HEIGHT",
        help="maximum video resolution in pixels (default: 1080)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "Videos" / "youtube-video-downloader",
        help="download root directory (default: ~/Videos/youtube-video-downloader)",
    )
    parser.add_argument(
        "--max-attempts",
        type=nonnegative_int,
        default=0,
        metavar="N",
        help="download attempts; 0 retries indefinitely (default: 0)",
    )
    parser.add_argument(
        "--retry-delay",
        type=positive_int,
        default=10,
        metavar="SECONDS",
        help="initial delay between download attempts (default: 10)",
    )
    parser.add_argument(
        "-c",
        "--concurrent-fragments",
        type=fragment_count,
        default=DEFAULT_CONCURRENT_FRAGMENTS,
        metavar="N",
        help="simultaneous HLS/DASH fragments, 1-16 (default: 8)",
    )
    parser.add_argument(
        "--cookies",
        type=Path,
        help="optional Netscape cookies file for URLs requiring sign-in",
    )
    return parser.parse_args(argv)


def find_dependencies() -> dict[str, str]:
    """Locate the external programs needed by yt-dlp on YouTube."""
    programs = {name: shutil.which(name) for name in ("yt-dlp", "ffmpeg", "ffprobe", "deno")}
    missing = [name for name, path in programs.items() if path is None]
    if missing:
        raise RuntimeError(f"Missing required programs on PATH: {', '.join(missing)}")
    return {name: path for name, path in programs.items() if path is not None}


def archive_path(output_root: Path, source: YouTubeSource, resolution: int) -> Path:
    """Keep each playlist or single-video collection's archive separate."""
    if source.kind == "playlist":
        key = hashlib.sha256(source.source_id.encode("utf-8")).hexdigest()[:16]
    else:
        key = "shorts" if source.kind == "short" else "single-videos"
    return output_root / ".archives" / f"{key}-{resolution}p.txt"


def build_command(
    args: argparse.Namespace, source: YouTubeSource, programs: dict[str, str]
) -> list[str]:
    """Build one yt-dlp attempt with stable output and archive paths."""
    output_root = args.output_dir.resolve()
    archive = archive_path(output_root, source, args.resolution)
    folder = {
        "playlist": "%(playlist).100B",
        "video": "Single Videos",
        "short": "Shorts",
    }[source.kind]
    output_template = f"{folder}/{OUTPUT_TEMPLATE.format(resolution=args.resolution)}"
    portrait = f"bv[width<={args.resolution}][aspect_ratio<1]+ba/b[width<={args.resolution}][aspect_ratio<1]"
    landscape = f"bv[height<={args.resolution}]+ba/b[height<={args.resolution}]"
    format_selector = f"{portrait}/{landscape}"
    command = [
        programs["yt-dlp"],
        "--no-config-locations",
        "--yes-playlist" if source.kind == "playlist" else "--no-playlist",
        "--no-abort-on-error",
        "--abort-on-unavailable-fragments",
        "--continue",
        "--part",
        "--no-overwrites",
        "--download-archive",
        str(archive),
        "--paths",
        str(output_root),
        "--output",
        output_template,
        "--format",
        format_selector,
        "--format-sort",
        "res,proto:m3u8,vcodec:h264,acodec:aac",
        "--merge-output-format",
        "mp4",
        "--remux-video",
        "mp4",
        "--js-runtimes",
        f"deno:{programs['deno']}",
        "--socket-timeout",
        "30",
        "--http-chunk-size",
        "8M",
        "--concurrent-fragments",
        str(args.concurrent_fragments),
        "--newline",
        "--progress-delta",
        "10",
        "--retries",
        "10",
        "--fragment-retries",
        "10",
        "--extractor-retries",
        "5",
        "--file-access-retries",
        "5",
        "--retry-sleep",
        "http:exp=1:30",
        "--retry-sleep",
        "fragment:exp=1:30",
        "--retry-sleep",
        "extractor:exp=1:30",
        "--retry-sleep",
        "file_access:exp=1:30",
    ]
    if args.cookies is not None:
        command.extend(("--cookies", str(args.cookies.resolve())))
    command.append(args.url)
    return command


def video_quality(video: Path, ffprobe: str) -> int:
    """Read the shorter video dimension from a completed MP4."""
    result = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0",
            str(video),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {video}: {result.stderr.strip()}")
    try:
        width, height = (int(value) for value in result.stdout.strip().split(","))
    except ValueError as exc:
        raise RuntimeError(f"ffprobe returned no video dimensions for {video}") from exc
    if width < 1 or height < 1:
        raise RuntimeError(f"ffprobe returned invalid video dimensions for {video}")
    return min(width, height)


def normalize_downloads(output_root: Path, archive: Path, ffprobe: str) -> int:
    """Name archived MP4s by title and measured quality without collisions."""
    if not archive.exists():
        return 0
    archived_ids = set()
    for line in archive.read_text(encoding="utf-8").splitlines():
        extractor, separator, video_id = line.partition(" ")
        if extractor == "youtube" and separator and video_id:
            archived_ids.add(video_id)
    renamed = 0
    for media_dir in output_root.iterdir():
        if not media_dir.is_dir() or media_dir.is_symlink():
            continue
        occupied = {entry.name.casefold() for entry in media_dir.iterdir()}
        for video in sorted(media_dir.glob("*.mp4")):
            match = STAGED_VIDEO_NAME.fullmatch(video.name)
            if match is None or match.group("id") not in archived_ids:
                continue
            title = match.group("title")
            quality = video_quality(video, ffprobe)
            target = media_dir / f"{title} ({quality}p).mp4"
            suffix = 2
            while target.exists() or target.name.casefold() in occupied:
                target = media_dir / f"{title} ({suffix}) ({quality}p).mp4"
                suffix += 1
            video.rename(target)
            occupied.remove(video.name.casefold())
            occupied.add(target.name.casefold())
            renamed += 1
    return renamed


def run(argv: list[str] | None = None) -> int:
    """Keep trying the URL until it succeeds or the attempt limit is reached."""
    args = parse_args(argv)
    try:
        source = source_from_url(args.url)
        programs = find_dependencies()
        if args.cookies is not None and not args.cookies.is_file():
            raise ValueError(f"Cookies file does not exist: {args.cookies}")
        output_root = args.output_dir.resolve()
        (output_root / ".archives").mkdir(parents=True, exist_ok=True)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    command = build_command(args, source, programs)
    archive = archive_path(output_root, source, args.resolution)
    attempt = 0
    while True:
        attempt += 1
        print(f"Download attempt {attempt}: {args.url}", flush=True)
        try:
            result = subprocess.run(command, check=False)
        except OSError as exc:
            print(f"Could not start yt-dlp: {exc}", file=sys.stderr)
            return 2
        try:
            renamed = normalize_downloads(output_root, archive, programs["ffprobe"])
        except (OSError, UnicodeError, RuntimeError) as exc:
            print(f"Could not clean video filenames: {exc}", file=sys.stderr)
            renamed = -1
        if renamed > 0:
            print(f"Cleaned {renamed} video filename(s).", flush=True)
        if result.returncode == 0 and renamed >= 0:
            print(f"Download complete. Files are under {output_root}")
            return 0
        if args.max_attempts and attempt >= args.max_attempts:
            print(f"Download still has errors after {attempt} attempts.", file=sys.stderr)
            return 1

        delay = min(args.retry_delay * (2 ** min(attempt - 1, 30)), MAX_RETRY_DELAY)
        print(f"yt-dlp exited with status {result.returncode}. Retrying in {delay} seconds.", flush=True)
        time.sleep(delay)


def main() -> int:
    """Run the downloader and turn Ctrl+C into a stop that can be resumed."""
    try:
        return run()
    except KeyboardInterrupt:
        print("\nStopped. Run the same command to resume later.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
