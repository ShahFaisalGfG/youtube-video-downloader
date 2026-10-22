# YouTube Video Downloader v1.0.0 - Release Notes

**Released:** October 2026 · **Status:** Stable · **Platform:** Windows and Linux, Python 3.11 or later

---

v1.0.0 is the first version: a single Python script that saves YouTube playlists, videos, and Shorts as MP4 files, labeled with their quality, and keeps going through dropped connections and restarts until every video is saved.

---

## Added

- **Playlists, videos, and Shorts.** Playlist links (including watch links with `list=`), watch, `youtu.be`, live, embed, and Shorts links. Playlists go into a folder named after the playlist, single videos into `Single Videos`, and Shorts into `Shorts`.
- **Best quality up to a limit.** `--resolution` (default 1080) caps the shorter side of the video, so the same limit works for landscape videos and portrait Shorts.
- **MP4 that plays everywhere.** H.264 video and AAC audio are preferred, and FFmpeg remuxes the result into MP4. A video that can't become an MP4 stays failed and is retried instead of being saved in another format.
- **Clean names.** Finished files are named `Title (1080p).mp4` after the quality measured with ffprobe, and videos that share a title get ` (2)`, ` (3)` instead of overwriting each other.
- **Resumable.** Partial downloads continue, finished videos are skipped through an archive kept per playlist and per resolution, and the same command resumes after a crash or restart.
- **Retries.** yt-dlp retries network, fragment, extractor, and file errors, then the script retries the whole URL with delays that double up to five minutes. `--max-attempts` ends an automated job with a failure status, and `--retry-delay` sets the first wait.
- **Speed.** HLS streams are preferred with eight concurrent fragments by default (`--concurrent-fragments`, 1 to 16), and direct streams use 8 MB range requests, with no bandwidth limit.
- **Sign-in.** `--cookies` passes a Netscape-format cookies file for videos that need an account.
- **Versioning.** `--version` prints the version, and `pyproject.toml` installs the script as the `youtube-video-downloader` command (for example with pipx).

---

## Requirements

- Python 3.11 or later; the script uses only the standard library.
- `yt-dlp`, `ffmpeg`, `ffprobe`, and Deno on `PATH`.

---

*Start it once. Come back to a finished playlist.* 📥
