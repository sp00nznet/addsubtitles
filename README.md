# grab_subs

**Automatically find and download subtitles for your entire movie & TV show library.**

Point it at a folder, pick a language, and walk away. It recursively scans for video files, queries multiple subtitle providers, picks the **best matching** subtitle (prioritizing release group, hash, resolution, and source), drops the `.srt` right next to the video, and gives you a clean log of everything it did.

---

## Features

- **Recursive scanning** — handles deeply nested folder structures (`Movies/Action/Title (2024)/...`)
- **Smart matching** — uses file hashes *and* release metadata so a `SPARKS` encode gets `SPARKS` subs, not some random upload
- **Multi-provider** — searches OpenSubtitles, Podnapisi, and Gestdown out of the box
- **Skip existing** — won't re-download subs you already have (unless you tell it to)
- **Built-in caching** — repeated runs are faster thanks to a local provider cache
- **Detailed logs** — generates both a human-readable `.txt` and a machine-parseable `.csv` after every run

## Supported Formats

`.mkv` `.mp4` `.avi` `.mov` `.wmv` `.flv` `.webm` `.m4v` `.mpg` `.mpeg` `.ts` `.vob` `.ogv`

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/sp00nznet/addsubtitles.git
cd addsubtitles
pip install -r requirements.txt
```

### 2. Run

```bash
python grab_subs.py --dir "D:/Movies" --lang eng
```

That's it. Subtitles will appear next to each video file as `.eng.srt`.

---

## Usage

```
python grab_subs.py --dir <path> [options]
```

| Flag | Short | Description | Default |
|------|-------|-------------|---------|
| `--dir` | `-d` | Root directory to scan (required) | — |
| `--lang` | `-l` | Subtitle language ([ISO 639-3](https://en.wikipedia.org/wiki/List_of_ISO_639-3_codes)) | `eng` |
| `--overwrite` | | Re-download even if a subtitle already exists | off |
| `--providers` | `-p` | Space-separated list of providers to use | `opensubtitlescom podnapisi gestdown` |
| `--verbose` | `-v` | Show debug-level output (provider queries, scoring) | off |

### Examples

**English subs for your movie library:**
```bash
python grab_subs.py -d "D:/Movies" -l eng
```

**Spanish subs for TV shows, overwrite any existing:**
```bash
python grab_subs.py -d "E:/TV Shows" -l spa --overwrite
```

**French subs using only OpenSubtitles:**
```bash
python grab_subs.py -d "/media/films" -l fra -p opensubtitlescom
```

**Debug mode to see exactly what's happening:**
```bash
python grab_subs.py -d "D:/Movies" -l eng -v
```

---

## How Matching Works

The script doesn't just grab the first subtitle it finds. Each candidate is **scored** based on:

| Factor | Weight | What it checks |
|--------|--------|----------------|
| **File hash** | Highest | Exact byte-level match to your file |
| **Release group** | High | e.g. your `SPARKS` file prefers `SPARKS` subs |
| **Resolution** | Medium | 1080p file prefers 1080p-tagged subs |
| **Source** | Medium | BluRay file prefers BluRay subs over WEB-DL |
| **Title + Year/Episode** | Baseline | Ensures the subtitle is for the right content |

The highest-scoring subtitle wins. This means you almost always get subs that are **properly synced** to your specific release.

---

## Log Output

After every run, two log files are created in the script directory:

**`subtitle_log_<timestamp>.txt`** — human-readable summary:
```
Subtitle Download Log - 2026-03-17 14:30:00
================================================================================

SUMMARY: 42 downloaded, 3 skipped, 1 failed
Total videos scanned: 46

--------------------------------------------------------------------------------
DOWNLOADED SUBTITLES:
--------------------------------------------------------------------------------
  File:     The.Matrix.1999.1080p.BluRay.x264-SPARKS.mkv
  Source:   opensubtitlescom
  Release:  SPARKS

  File:     Breaking.Bad.S01E01.720p.BluRay.x264-DEMAND.mkv
  Source:   podnapisi
  Release:  DEMAND
  ...
```

**`subtitle_log_<timestamp>.csv`** — for scripting or spreadsheets:
```csv
file,directory,status,subtitle_source,release_match
The.Matrix.1999.1080p.BluRay.x264-SPARKS.mkv,,downloaded,opensubtitlescom,SPARKS
```

---

## Common Language Codes

| Language | Code |
|----------|------|
| English | `eng` |
| Spanish | `spa` |
| French | `fra` |
| German | `deu` |
| Portuguese | `por` |
| Italian | `ita` |
| Dutch | `nld` |
| Japanese | `jpn` |
| Korean | `kor` |
| Chinese | `zho` |
| Arabic | `ara` |
| Russian | `rus` |

Full list: [ISO 639-3 codes](https://en.wikipedia.org/wiki/List_of_ISO_639-3_codes)

---

## Requirements

- Python 3.10+
- Dependencies installed via `pip install -r requirements.txt`
  - [subliminal](https://github.com/Diaoul/subliminal) — subtitle provider framework
  - [babelfish](https://github.com/Diaoul/babelfish) — language code handling

---

## License

MIT
