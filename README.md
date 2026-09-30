# YouTube Video Downloader

Download a YouTube playlist, individual video, or Short as MP4 at the best
available resolution up to a selected size. The Python script runs yt-dlp and
uses its partial downloads and archive to recover from interrupted transfers.

## Requirements

- Python 3.11 or later
- `yt-dlp`, `ffmpeg`, `ffprobe`, and Deno on `PATH`
- Network access to YouTube

The script uses only Python's standard library; no `pip install` is needed. The
official Windows `yt-dlp.exe` bundles the YouTube JavaScript challenge scripts.
Deno supplies the runtime for them. On Linux, install the official yt-dlp binary
or a package that includes `yt-dlp-ejs`.

On Windows, the programs can be checked with:

```powershell
python --version
yt-dlp --version
ffmpeg -version
ffprobe -version
deno --version
```

## Run

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

The default resolution is 1080. `-r 720` or `--resolution 720` selects the best
available video whose shorter dimension is at most 720 pixels. This covers both
landscape videos and portrait Shorts. If only lower resolutions are available,
yt-dlp selects the best of those.

On Windows, the default root is
`C:\Users\<name>\Videos\youtube-video-downloader\`. On Linux, it is
`~/Videos/youtube-video-downloader/`. Playlists go into `<playlist name>/`,
single videos into `Single Videos/`, and Shorts into `Shorts/`. Use
`--output-dir PATH` to choose another root. Each playlist and each single-video
collection has its own archive per requested resolution, so a later 1080p run
does not skip videos previously downloaded at 720p.

Completed MP4s use the video title and measured quality, such as
`Episode 001 (1080p).mp4`. If a requested 1080p video is available only at
720p, its filename ends in `(720p)`. For portrait videos, the smaller dimension
sets the quality label, so 720x1280 becomes `(720p)`. When multiple videos have
the same title and quality, later files receive ` (2)`, ` (3)`, and so on before
the quality label. During the download, yt-dlp uses the video ID and requested
resolution in its temporary filename so partial downloads remain distinct. The
script uses ffprobe to read the finished MP4 and removes those temporary markers
after each download attempt.

At a given resolution, the script prefers H.264 video and AAC audio for wider
MP4 player support. yt-dlp can use other codecs when those streams are not
available, and FFmpeg remuxes the result into MP4.

For speed, the script prefers HLS streams at the selected resolution and
downloads eight fragments concurrently by default. Use
`-c N` or `--concurrent-fragments N` to choose 1 through 16. Values above 8 can cause more request errors and
may not improve speed. When HLS is unavailable, direct HTTP streams use 8 MB
range requests. These settings do not impose a bandwidth
limit. Speed still depends on the YouTube server, connection, and available
network bandwidth. Future interrupted downloads resume their `.part` files when
the same command uses the same output location.

yt-dlp retries network, fragment, extractor, and file access errors within each
attempt. If a download still fails, the script waits and retries the URL with
increasing delays up to five minutes. Completed videos are skipped
through the archive, and `.part` files are resumed. Re-running the same command
after a process or computer restart also resumes the playlist. The script retries
indefinitely by default; press Ctrl+C to stop it. To end an automated job with a
failure status after a fixed number of attempts, use `--max-attempts 5`.
Use `--retry-delay 30` to change the first wait. A missing or private video can
keep an unlimited run active until it becomes available or you stop the script.

For a URL that requires sign-in, export a Netscape-format cookies file and
pass `--cookies PATH`. Protect that file because it grants account access. Failed
downloads remain unarchived for the next attempt. If yt-dlp cannot create an MP4
from a particular video's offered streams, that video remains failed and is
retried; the script does not silently accept another file type.

## Check the script

```powershell
python -m pytest tests -q
```
