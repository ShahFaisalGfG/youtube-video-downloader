"""Focused command and recovery tests for the playlist runner."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

import download_playlist


PROGRAMS = {
    "yt-dlp": "yt-dlp",
    "ffmpeg": "ffmpeg",
    "ffprobe": "ffprobe",
    "deno": "deno",
}
URL = "https://www.youtube.com/playlist?list=PLtest123"
VIDEO_ID = "jNQXAC9IVRw"
VIDEO_URL = f"https://www.youtube.com/watch?v={VIDEO_ID}"
SHORT_URL = f"https://www.youtube.com/shorts/{VIDEO_ID}"
PLAYLIST = download_playlist.YouTubeSource("playlist", "PLtest123")


def test_default_output_is_in_videos() -> None:
    """Put new playlists in the user's Videos directory by default."""
    args = download_playlist.parse_args([URL])
    assert args.output_dir == Path.home() / "Videos" / "youtube-video-downloader"
    assert args.resolution == 1080
    assert args.concurrent_fragments == 8


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (URL, PLAYLIST),
        (f"{VIDEO_URL}&list=PLtest123", PLAYLIST),
        (VIDEO_URL, download_playlist.YouTubeSource("video", VIDEO_ID)),
        (f"https://youtu.be/{VIDEO_ID}", download_playlist.YouTubeSource("video", VIDEO_ID)),
        (f"https://www.youtube.com/live/{VIDEO_ID}", download_playlist.YouTubeSource("video", VIDEO_ID)),
        (SHORT_URL, download_playlist.YouTubeSource("short", VIDEO_ID)),
    ],
)
def test_classifies_youtube_urls(url: str, expected: download_playlist.YouTubeSource) -> None:
    """Route playlists, single videos, and Shorts to their respective archives."""
    assert download_playlist.source_from_url(url) == expected


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/playlist?list=PLtest123",
        "https://www.youtube.com/watch?v=test",
        "https://www.youtube.com/playlist?list=",
        "https://www.youtube.com/playlist",
        "https://www.youtube.com/shorts/invalid",
    ],
)
def test_rejects_unsupported_urls(url: str) -> None:
    """Reject unsupported hosts and links without a usable video or list ID."""
    with pytest.raises(ValueError):
        download_playlist.source_from_url(url)


def test_build_command_is_resumable_and_mp4(tmp_path: Path) -> None:
    """Keep quality archives separate and require complete MP4 output."""
    args = download_playlist.parse_args(
        [URL, "--resolution", "1080", "--output-dir", str(tmp_path)]
    )
    command = download_playlist.build_command(args, PLAYLIST, PROGRAMS)

    assert command[command.index("--format") + 1] == (
        "bv[width<=1080][aspect_ratio<1]+ba/b[width<=1080][aspect_ratio<1]/"
        "bv[height<=1080]+ba/b[height<=1080]"
    )
    assert command[command.index("--format-sort") + 1] == "res,proto:m3u8,vcodec:h264,acodec:aac"
    assert command[command.index("--merge-output-format") + 1] == "mp4"
    assert command[command.index("--remux-video") + 1] == "mp4"
    assert command[command.index("--http-chunk-size") + 1] == "8M"
    assert command[command.index("--concurrent-fragments") + 1] == "8"
    assert "--throttled-rate" not in command
    assert command[command.index("--progress-delta") + 1] == "10"
    assert "--newline" in command
    assert command[command.index("--download-archive") + 1].startswith(str(tmp_path / ".archives"))
    assert command[command.index("--paths") + 1] == str(tmp_path)
    assert command[command.index("--output") + 1] == (
        "%(playlist).100B/%(title).100B [%(id)s] (requested-1080p).%(ext)s"
    )
    assert "--continue" in command
    assert "--part" in command
    assert "--abort-on-unavailable-fragments" in command
    assert "--no-abort-on-error" in command
    assert "--yes-playlist" in command
    assert "--no-playlist" not in command
    assert command[-1] == URL


@pytest.mark.parametrize(
    ("url", "folder", "archive_name"),
    [
        (VIDEO_URL, "Single Videos", "single-videos-720p.txt"),
        (SHORT_URL, "Shorts", "shorts-720p.txt"),
    ],
)
def test_single_video_shortcuts_and_paths(
    url: str, folder: str, archive_name: str, tmp_path: Path
) -> None:
    """Use one short concurrency flag and separate single-video archives."""
    args = download_playlist.parse_args(
        [url, "-r", "720", "-c", "4", "--output-dir", str(tmp_path)]
    )
    source = download_playlist.source_from_url(url)
    command = download_playlist.build_command(args, source, PROGRAMS)

    assert args.resolution == 720
    assert command[command.index("--concurrent-fragments") + 1] == "4"
    assert command[command.index("--output") + 1] == (
        f"{folder}/%(title).100B [%(id)s] (requested-720p).%(ext)s"
    )
    assert Path(command[command.index("--download-archive") + 1]).name == archive_name
    assert "--no-playlist" in command
    assert "--yes-playlist" not in command


@pytest.mark.parametrize("count", ("1", "16"))
def test_fragment_count_reaches_yt_dlp(count: str, tmp_path: Path) -> None:
    """Pass both allowed endpoints to yt-dlp."""
    args = download_playlist.parse_args(
        [URL, "--output-dir", str(tmp_path), "--concurrent-fragments", count]
    )
    command = download_playlist.build_command(args, PLAYLIST, PROGRAMS)
    assert command[command.index("--concurrent-fragments") + 1] == count


@pytest.mark.parametrize("count", ("0", "17", "many"))
def test_fragment_count_rejects_invalid_values(count: str) -> None:
    """Reject values outside the configured range before starting yt-dlp."""
    with pytest.raises(SystemExit) as exc:
        download_playlist.parse_args([URL, "--concurrent-fragments", count])
    assert exc.value.code == 2


def test_normalize_downloads_preserves_same_title_videos(tmp_path: Path) -> None:
    """Use actual quality and preserve videos that share a title."""
    media_dir = tmp_path / "A playlist"
    media_dir.mkdir()
    archive = tmp_path / ".archives" / "list-1080p.txt"
    archive.parent.mkdir()
    archive.write_text(
        "youtube aaaaaaaaaaa\nyoutube bbbbbbbbbbb\nyoutube ccccccccccc\n",
        encoding="utf-8",
    )
    for name in (
        "001 - Episode [Urdu Dubbed] [aaaaaaaaaaa].mp4",
        "Episode [Urdu Dubbed] [bbbbbbbbbbb] (requested-1080p).mp4",
        "Clip [ccccccccccc] (requested-1080p).mp4",
        "Clip (720p).mp4",
        "Unfinished [ddddddddddd] (requested-1080p).mp4",
    ):
        (media_dir / name).write_bytes(b"video")

    def quality(video: Path, ffprobe: str) -> int:
        return 720 if video.name.startswith("Clip ") else 1080

    with patch.object(download_playlist, "video_quality", side_effect=quality):
        renamed = download_playlist.normalize_downloads(tmp_path, archive, "ffprobe")

    assert renamed == 3
    assert {path.name for path in media_dir.iterdir()} == {
        "Episode [Urdu Dubbed] (1080p).mp4",
        "Episode [Urdu Dubbed] (2) (1080p).mp4",
        "Clip (720p).mp4",
        "Clip (2) (720p).mp4",
        "Unfinished [ddddddddddd] (requested-1080p).mp4",
    }


@pytest.mark.parametrize("dimensions", ("720,1280\n", "1280,720\n"))
def test_video_quality_uses_shorter_dimension(dimensions: str, tmp_path: Path) -> None:
    """Label portrait and landscape videos by their shorter dimension."""
    video = tmp_path / "portrait.mp4"
    with patch.object(
        download_playlist.subprocess,
        "run",
        return_value=SimpleNamespace(returncode=0, stdout=dimensions, stderr=""),
    ) as probe:
        assert download_playlist.video_quality(video, "ffprobe") == 720

    assert probe.call_args.args[0][-1] == str(video)


def test_video_quality_rejects_missing_dimensions(tmp_path: Path) -> None:
    """Leave a staged file for retry when ffprobe cannot identify the video."""
    with patch.object(
        download_playlist.subprocess,
        "run",
        return_value=SimpleNamespace(returncode=0, stdout="", stderr=""),
    ):
        with pytest.raises(RuntimeError, match="no video dimensions"):
            download_playlist.video_quality(tmp_path / "bad.mp4", "ffprobe")


def test_short_download_finishes_with_clean_name(tmp_path: Path) -> None:
    """Route a Short through the archive and filename cleanup flow."""
    def fake_download(command: list[str], check: bool) -> SimpleNamespace:
        archive = Path(command[command.index("--download-archive") + 1])
        archive.write_text(f"youtube {VIDEO_ID}\n", encoding="utf-8")
        media_dir = tmp_path / "Shorts"
        media_dir.mkdir()
        (media_dir / f"Short title [{VIDEO_ID}] (requested-1080p).mp4").write_bytes(b"video")
        return SimpleNamespace(returncode=0)

    with (
        patch.object(download_playlist, "find_dependencies", return_value=PROGRAMS),
        patch.object(download_playlist.subprocess, "run", side_effect=fake_download),
        patch.object(download_playlist, "video_quality", return_value=720),
    ):
        status = download_playlist.run([SHORT_URL, "--output-dir", str(tmp_path)])

    assert status == 0
    assert (tmp_path / "Shorts" / "Short title (720p).mp4").exists()


def test_failed_attempt_retries_then_succeeds(tmp_path: Path) -> None:
    """Resume a failed playlist without asking for another command."""
    results = [SimpleNamespace(returncode=1), SimpleNamespace(returncode=0)]
    with (
        patch.object(download_playlist, "find_dependencies", return_value=PROGRAMS),
        patch.object(download_playlist.subprocess, "run", side_effect=results) as execute,
        patch.object(download_playlist.time, "sleep") as sleep,
    ):
        status = download_playlist.run(
            [URL, "--output-dir", str(tmp_path), "--retry-delay", "2"]
        )

    assert status == 0
    assert execute.call_count == 2
    assert execute.call_args_list[0].args == execute.call_args_list[1].args
    sleep.assert_called_once_with(2)


def test_attempt_limit_returns_failure(tmp_path: Path) -> None:
    """Report incomplete playlists to a scheduler after the selected limit."""
    with (
        patch.object(download_playlist, "find_dependencies", return_value=PROGRAMS),
        patch.object(download_playlist.subprocess, "run", return_value=SimpleNamespace(returncode=1)) as execute,
        patch.object(download_playlist.time, "sleep") as sleep,
    ):
        status = download_playlist.run(
            [URL, "--output-dir", str(tmp_path), "--max-attempts", "3"]
        )

    assert status == 1
    assert execute.call_count == 3
    assert [call.args[0] for call in sleep.call_args_list] == [10, 20]
