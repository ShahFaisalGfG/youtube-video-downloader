<div align="center">

# YouTube Video Downloader

**A resumable command-line downloader for YouTube playlists, videos, and Shorts - clean MP4 files, labeled with their quality, that survive dropped connections and restarts.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB.svg?logo=python&logoColor=white)](pyproject.toml)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-0078D4.svg)](#requirements)
[![Status](https://img.shields.io/badge/Status-CLI%20script-orange.svg)](#roadmap)

</div>

---

YouTube Video Downloader saves a whole playlist, a single video, or a Short as MP4 at the best resolution up to the size you choose. It drives [yt-dlp](https://github.com/yt-dlp/yt-dlp), resumes partial downloads, skips what is already done, and keeps retrying until every video is saved. Finished files get readable names such as `Episode 001 (1080p).mp4`. It is a single Python script that uses only the standard library.

> *Start it once. Come back to a finished playlist.*

---

## Table of Contents

- [YouTube Video Downloader](#youtube-video-downloader)
  - [Table of Contents](#table-of-contents)
  - [Who Is This For?](#who-is-this-for)
  - [Features](#features)
  - [Requirements](#requirements)
  - [Download \& Install](#download--install)
  - [Quick Start](#quick-start)
  - [Options](#options)
  - [Where Files Go](#where-files-go)
  - [Quality and Speed](#quality-and-speed)
  - [Resuming and Retries](#resuming-and-retries)
  - [Videos That Need Sign-In](#videos-that-need-sign-in)
  - [Troubleshooting](#troubleshooting)
  - [Development \& Tests](#development--tests)
  - [Versioning \& Releases](#versioning--releases)
  - [Contributing](#contributing)
  - [Roadmap](#roadmap)
  - [Changelog](#changelog)
    - [v1.0.0 - October 2026 *(current)*](#v100---october-2026-current)
  - [Responsible Use](#responsible-use)
  - [License \& Credits](#license--credits)
  - [Support the Project](#support-the-project)

---

## Who Is This For?

- **Learners** saving a course playlist to watch offline
- **Travelers and commuters** with slow or unreliable connections
- **Creators and archivists** keeping copies of their own uploads
- **Anyone** who wants MP4 files that play everywhere, named by title and quality

---

## Features

- 📚 **Playlists, videos, and Shorts** from `youtube.com`, `m.youtube.com`, `music.youtube.com`, and `youtu.be` links
- 🎯 **Best quality up to your limit** - 1080p by default, any limit you choose, for landscape videos and portrait Shorts alike
- 🎞️ **MP4 that plays everywhere** - H.264 video and AAC audio preferred, remuxed to MP4 by FFmpeg
- 🏷️ **Clean names** - `Title (1080p).mp4`, labeled with the quality measured from the finished file, never overwriting a video with the same title
- ⏯️ **Resumable** - partial downloads continue, finished videos are skipped, and the same command picks up after a crash or restart
- 🔁 **Keeps going** - retries network, fragment, and file errors, then the whole URL with growing waits of up to five minutes
- ⚡ **Fast** - eight HLS fragments at a time by default and 8 MB range requests, with no bandwidth limit
- 🍪 **Sign-in support** through a cookies file for videos that need an account
- 🧩 **No pip packages** - Python's standard library plus yt-dlp, FFmpeg, and Deno

---

## Requirements

- Python 3.11 or later
- `yt-dlp`, `ffmpeg`, `ffprobe`, and Deno on `PATH`
- Network access to YouTube

The official Windows `yt-dlp.exe` bundles the YouTube JavaScript challenge scripts, and Deno supplies the runtime for them. On Linux, install the official yt-dlp binary or a package that includes `yt-dlp-ejs`.

On Windows, install the programs with winget:

```powershell
winget install --id yt-dlp.yt-dlp --exact
winget install --id Gyan.FFmpeg --exact
winget install --id DenoLand.Deno --exact
```

Then open a new terminal and check them:

```powershell
python --version
yt-dlp --version
ffmpeg -version
ffprobe -version
deno --version
```

On Linux, install FFmpeg from your distribution and Deno from [deno.com](https://deno.com/).

---

## Download & Install

Clone the repository, or download `download_playlist.py` on its own:

```bash
git clone https://github.com/ShahFaisalGfG/youtube-video-downloader.git
cd youtube-video-downloader
```

The script runs as it is; nothing needs to be installed with pip. To run it as a `youtube-video-downloader` command from any folder instead, install it with [pipx](https://pipx.pypa.io/):

```bash
pipx install git+https://github.com/ShahFaisalGfG/youtube-video-downloader.git
```

---

## Quick Start

Windows PowerShell:

```powershell
python .\download_playlist.py "https://www.youtube.com/playlist?list=PLAYLIST_ID"
python .\download_playlist.py "https://www.youtube.com/watch?v=VIDEO_ID"
python .\download_playlist.py "https://www.youtube.com/shorts/VIDEO_ID" -r 720 -c 4
```

Linux:

```bash
python3 download_playlist.py 'https://www.youtube.com/playlist?list=PLAYLIST_ID'
python3 download_playlist.py 'https://youtu.be/VIDEO_ID' -r 720 -c 4
```

With pipx, replace `python download_playlist.py` with `youtube-video-downloader`. Quote the URL: playlist links contain `&` and `?`, which shells treat as special characters.

---

## Options

| Option | Default | What it does |
| --- | --- | --- |
| `URL` | (required) | A YouTube playlist, video, or Shorts URL. A watch URL with `list=` downloads the whole playlist |
| `-r`, `--resolution HEIGHT` | `1080` | Highest resolution to download, measured on the shorter side of the video |
| `--output-dir PATH` | `~/Videos/youtube-video-downloader` | Root folder for downloads |
| `-c`, `--concurrent-fragments N` | `8` | HLS/DASH fragments downloaded at the same time, 1 to 16 |
| `--max-attempts N` | `0` | Attempts before giving up; `0` retries until it succeeds or you press Ctrl+C |
| `--retry-delay SECONDS` | `10` | First wait between attempts; it doubles each time, up to five minutes |
| `--cookies PATH` | (none) | Netscape-format cookies file for videos that need sign-in |
| `--version` | | Print the version and exit |

---

## Where Files Go

On Windows, the default root is `C:\Users\<name>\Videos\youtube-video-downloader\`. On Linux, it is `~/Videos/youtube-video-downloader/`.

| Download | Folder |
| --- | --- |
| Playlist | `<playlist name>/` |
| Single video | `Single Videos/` |
| Short | `Shorts/` |

Each playlist and each single-video collection has its own archive per requested resolution, kept in `.archives/` under the root, so a later 1080p run does not skip videos previously downloaded at 720p.

Completed MP4s use the video title and measured quality, such as `Episode 001 (1080p).mp4`. If a requested 1080p video is available only at 720p, its filename ends in `(720p)`. For portrait videos, the smaller dimension sets the quality label, so 720x1280 becomes `(720p)`. When multiple videos have the same title and quality, later files receive ` (2)`, ` (3)`, and so on before the quality label.

During the download, yt-dlp uses the video ID and requested resolution in its temporary filename so partial downloads remain distinct. The script uses ffprobe to read the finished MP4 and removes those temporary markers after each download attempt.

---

## Quality and Speed

`-r 720` or `--resolution 720` selects the best available video whose shorter dimension is at most 720 pixels. This covers both landscape videos and portrait Shorts. If only lower resolutions are available, yt-dlp selects the best of those.

At a given resolution, the script prefers H.264 video and AAC audio for wider MP4 player support. yt-dlp can use other codecs when those streams are not available, and FFmpeg remuxes the result into MP4.

For speed, the script prefers HLS streams at the selected resolution and downloads eight fragments concurrently by default. Use `-c N` or `--concurrent-fragments N` to choose 1 through 16. Values above 8 can cause more request errors and may not improve speed. When HLS is unavailable, direct HTTP streams use 8 MB range requests. These settings do not impose a bandwidth limit. Speed still depends on the YouTube server, the connection, and the available network bandwidth.

---

## Resuming and Retries

yt-dlp retries network, fragment, extractor, and file access errors within each attempt. If a download still fails, the script waits and retries the URL with increasing delays up to five minutes. Completed videos are skipped through the archive, and `.part` files are resumed. Re-running the same command after a process or computer restart also resumes the playlist, as long as it uses the same output location.

The script retries indefinitely by default; press Ctrl+C to stop it. To end an automated job with a failure status after a fixed number of attempts, use `--max-attempts 5`. Use `--retry-delay 30` to change the first wait. A missing or private video can keep an unlimited run active until it becomes available or you stop the script.

Failed downloads remain unarchived for the next attempt. If yt-dlp cannot create an MP4 from a particular video's offered streams, that video remains failed and is retried; the script does not silently accept another file type.

---

## Videos That Need Sign-In

For a URL that requires sign-in, export a Netscape-format cookies file from your browser and pass `--cookies PATH`. Protect that file: it grants access to your account. Files named `cookies*.txt` are ignored by Git in this repository.

---

## Troubleshooting

| Message or exit status | Meaning |
| --- | --- |
| `Missing required programs on PATH: ...` | Install the listed programs (see [Requirements](#requirements)) and open a new terminal |
| `Enter a YouTube playlist, video, or Shorts URL beginning with https://` | The link is not a YouTube URL; copy it from the address bar or the Share button |
| `Cookies file does not exist: ...` | Check the path passed to `--cookies` |
| `Download still has errors after N attempts.` (exit status 1) | `--max-attempts` was reached; run the same command again to continue |
| Exit status 2 | The URL, the programs, the cookies file, or the output folder could not be used; nothing was downloaded |
| `Stopped. Run the same command to resume later.` (exit status 130) | You pressed Ctrl+C; partial files are kept |

Still stuck? [Open an issue](https://github.com/ShahFaisalGfG/youtube-video-downloader/issues) with the command you ran (without your cookies file) and the last lines of its output.

---

## Development & Tests

```bash
python -m pip install pytest
python -m pytest tests -q
```

The tests mock yt-dlp, ffprobe, and every other program, so they never contact YouTube. [CI](.github/workflows/tests.yml) runs them on Windows and Linux with Python 3.11 and 3.14 for every push and pull request. Keep the script standard-library only.

---

## Versioning & Releases

The project follows [Semantic Versioning](https://semver.org/): `MAJOR.MINOR.PATCH`. The version lives in one place, `__version__` in `download_playlist.py`; `pyproject.toml` reads it from there, and `--version` prints it. Versions are tagged `v<version>`, and each one gets its notes in `release_notes/release_notes_v<version>.md`.

The script is distributed from the repository for now. Built releases with installers will start with the GUI (see [Roadmap](#roadmap)).

---

## Contributing

1. **Fork** the repository and clone your fork
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Make your changes, add tests, and make sure `python -m pytest tests -q` passes
4. Commit with a clear message and open a **Pull Request** targeting `main`

For significant changes, please [open an issue](https://github.com/ShahFaisalGfG/youtube-video-downloader/issues) first to discuss the approach.

---

## Roadmap

| Target | Plan |
| --- | --- |
| **v1.x** | Command-line script: more testing, speed tuning, and features |
| **v2.0.0** | A PyQt desktop app with a download queue, progress, and settings |
| **With the app** | Windows installers and a portable build, published by a build and release pipeline on GitHub Releases |

Have a feature idea? [Open an issue](https://github.com/ShahFaisalGfG/youtube-video-downloader/issues).

---

## Changelog

### v1.0.0 - October 2026 *(current)*
- 📚 Playlists, single videos, and Shorts as MP4 at the best resolution up to a chosen limit, 1080p by default
- 🏷️ Clean file names with the measured quality, and no overwrites of videos that share a title
- ⏯️ Resumable downloads with per-playlist, per-resolution archives, retries with growing delays, and an optional attempt limit
- ⚡ HLS preferred with eight concurrent fragments by default (1 to 16)
- 🍪 Cookies file support for videos that need sign-in
- 🔖 `--version`, a `pyproject.toml` that installs the `youtube-video-downloader` command, the MIT License, and CI tests on Windows and Linux

[Full release notes →](release_notes/)

---

## Responsible Use

Download only videos you own or have permission to save, and follow YouTube's Terms of Service and the copyright law where you live. This project is not affiliated with or endorsed by YouTube or Google.

---

## License & Credits

Released under the [MIT License](LICENSE) - free to use, modify, and distribute.

Downloads are made by [yt-dlp](https://github.com/yt-dlp/yt-dlp), with [FFmpeg](https://ffmpeg.org/) for merging and probing and [Deno](https://deno.com/) for YouTube's JavaScript challenges. They are separate programs under their own licenses and are not bundled.

Built with ❤️ by **Shah Faisal** · [Portfolio](https://shahfaisalgfg.github.io/) · [shahfaisalgfg@gmail.com](mailto:shahfaisalgfg@gmail.com)

---

## Support the Project

- ⭐ **Star the repo** - it helps others find the project
- 🐛 **Report a bug** - a link that won't download is worth an issue
- 💡 **Suggest a feature** - especially for the coming desktop app
- 🛠️ **Contribute code** - see [Contributing](#contributing)

---

*Start it once. Come back to a finished playlist.* 📥
