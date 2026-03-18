#!/usr/bin/env python3
"""
grab_subs.py - Automatically find and download subtitles for movies and TV shows.

Scans a directory for video files, identifies them (title, year, release group, etc.),
searches multiple subtitle providers, and downloads the best-matching subtitle.
Release-group matching is prioritized so e.g. a SPARKS release gets SPARKS subs.

Usage:
    python grab_subs.py --dir "D:/Movies" --lang eng
    python grab_subs.py --dir "D:/TV Shows" --lang eng --overwrite
"""

import argparse
import csv
import datetime
import logging
import os
import sys
from pathlib import Path

try:
    import subliminal
    from babelfish import Language
except ImportError:
    print("Missing dependencies. Install them with:")
    print("  pip install -r requirements.txt")
    sys.exit(1)

VIDEO_EXTENSIONS = {
    ".mkv", ".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm",
    ".m4v", ".mpg", ".mpeg", ".ts", ".vob", ".ogv",
}

LOG_DIR = Path(__file__).parent
LOG_TIMESTAMP = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = LOG_DIR / f"subtitle_log_{LOG_TIMESTAMP}.csv"
TEXT_LOG = LOG_DIR / f"subtitle_log_{LOG_TIMESTAMP}.txt"


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    # subliminal is chatty at DEBUG
    if not verbose:
        logging.getLogger("subliminal").setLevel(logging.WARNING)
        logging.getLogger("enzyme").setLevel(logging.WARNING)


def find_videos(directory: str) -> list[Path]:
    """Recursively find all video files under *directory*."""
    videos = []
    for root, _dirs, files in os.walk(directory):
        for fname in files:
            if Path(fname).suffix.lower() in VIDEO_EXTENSIONS:
                videos.append(Path(root) / fname)
    videos.sort()
    return videos


def scan_videos(paths: list[Path]) -> list:
    """Use subliminal to scan video files and extract metadata."""
    scanned = []
    for p in paths:
        try:
            video = subliminal.scan_video(str(p))
            scanned.append(video)
        except Exception as exc:
            logging.warning("Could not scan %s: %s", p, exc)
    return scanned


def download_subtitles(
    videos: list,
    language: Language,
    providers: list[str] | None = None,
    overwrite: bool = False,
) -> list[dict]:
    """Download best-match subtitles for each video. Returns a log list."""

    results = []
    default_providers = ["opensubtitlescom", "podnapisi", "gestdown"]

    active_providers = providers or default_providers

    logging.info("Using subtitle providers: %s", ", ".join(active_providers))
    logging.info("Target language: %s", language)

    with subliminal.core.ProviderPool(providers=active_providers) as pool:
        for video in videos:
            entry = {
                "file": str(video.name),
                "directory": str(Path(video.name).parent) if hasattr(video, "name") else "",
                "status": "",
                "subtitle_source": "",
                "release_match": "",
            }

            # Build the expected .srt path to check for existing subs
            video_path = Path(video.name)
            sub_path = video_path.with_suffix(f".{language.alpha3}.srt")
            if sub_path.exists() and not overwrite:
                logging.info("SKIP (exists): %s", video_path.name)
                entry["status"] = "skipped (subtitle exists)"
                results.append(entry)
                continue

            logging.info("Searching subtitles for: %s", video_path.name)

            try:
                subs = pool.list_subtitles(video, {language})
            except Exception as exc:
                logging.error("Provider error for %s: %s", video_path.name, exc)
                entry["status"] = f"error: {exc}"
                results.append(entry)
                continue

            if not subs:
                logging.warning("NO SUBS FOUND: %s", video_path.name)
                entry["status"] = "no subtitles found"
                results.append(entry)
                continue

            # Score and pick the best subtitle (subliminal scores by hash,
            # release group, resolution, source, etc.)
            scored = subliminal.score.compute_score(subs[0], video)
            best = sorted(
                subs,
                key=lambda s: subliminal.score.compute_score(s, video),
                reverse=True,
            )
            chosen = best[0]
            chosen_score = subliminal.score.compute_score(chosen, video)

            # Download the subtitle content
            try:
                pool.download_subtitle(chosen)
            except Exception as exc:
                logging.error("Download failed for %s: %s", video_path.name, exc)
                entry["status"] = f"download error: {exc}"
                results.append(entry)
                continue

            if not chosen.content:
                logging.warning("Empty subtitle content for %s", video_path.name)
                entry["status"] = "download returned empty content"
                results.append(entry)
                continue

            # Save to disk next to the video
            subliminal.save_subtitles(video, [chosen])

            provider_name = chosen.provider_name if hasattr(chosen, "provider_name") else "unknown"
            release_info = ""
            if hasattr(chosen, "release_info"):
                release_info = chosen.release_info or ""
            elif hasattr(chosen, "releases"):
                release_info = ", ".join(chosen.releases) if chosen.releases else ""

            logging.info(
                "DOWNLOADED: %s | provider=%s score=%d release=%s",
                video_path.name,
                provider_name,
                chosen_score,
                release_info,
            )

            entry["status"] = "downloaded"
            entry["subtitle_source"] = provider_name
            entry["release_match"] = release_info
            results.append(entry)

    return results


def write_log(results: list[dict]) -> None:
    """Write a CSV log and a human-readable text log."""

    # CSV log
    with open(LOG_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["file", "directory", "status", "subtitle_source", "release_match"])
        writer.writeheader()
        writer.writerows(results)

    # Human-readable text log
    downloaded = [r for r in results if r["status"] == "downloaded"]
    skipped = [r for r in results if r["status"].startswith("skipped")]
    failed = [r for r in results if r["status"] not in ("downloaded",) and not r["status"].startswith("skipped")]

    with open(TEXT_LOG, "w", encoding="utf-8") as f:
        f.write(f"Subtitle Download Log - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"SUMMARY: {len(downloaded)} downloaded, {len(skipped)} skipped, {len(failed)} failed\n")
        f.write(f"Total videos scanned: {len(results)}\n\n")

        if downloaded:
            f.write("-" * 80 + "\n")
            f.write("DOWNLOADED SUBTITLES:\n")
            f.write("-" * 80 + "\n")
            for r in downloaded:
                f.write(f"  File:     {r['file']}\n")
                f.write(f"  Source:   {r['subtitle_source']}\n")
                f.write(f"  Release:  {r['release_match']}\n")
                f.write("\n")

        if skipped:
            f.write("-" * 80 + "\n")
            f.write("SKIPPED (subtitle already exists):\n")
            f.write("-" * 80 + "\n")
            for r in skipped:
                f.write(f"  {r['file']}\n")
            f.write("\n")

        if failed:
            f.write("-" * 80 + "\n")
            f.write("FAILED:\n")
            f.write("-" * 80 + "\n")
            for r in failed:
                f.write(f"  File:   {r['file']}\n")
                f.write(f"  Reason: {r['status']}\n")
                f.write("\n")


def print_summary(results: list[dict]) -> None:
    downloaded = [r for r in results if r["status"] == "downloaded"]
    skipped = [r for r in results if r["status"].startswith("skipped")]
    failed = [r for r in results if r["status"] not in ("downloaded",) and not r["status"].startswith("skipped")]

    print("\n" + "=" * 60)
    print("  SUBTITLE DOWNLOAD COMPLETE")
    print("=" * 60)
    print(f"  Downloaded : {len(downloaded)}")
    print(f"  Skipped    : {len(skipped)}")
    print(f"  Failed     : {len(failed)}")
    print(f"  Total      : {len(results)}")
    print("-" * 60)

    if downloaded:
        print("\n  Downloaded subtitles:")
        for r in downloaded:
            rel = f" [{r['release_match']}]" if r["release_match"] else ""
            print(f"    + {r['file']}{rel}")

    if failed:
        print("\n  Failed:")
        for r in failed:
            print(f"    x {r['file']} -- {r['status']}")

    print(f"\n  Log files:")
    print(f"    {TEXT_LOG}")
    print(f"    {LOG_FILE}")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Automatically download subtitles for movies and TV shows.",
    )
    parser.add_argument(
        "--dir", "-d",
        required=True,
        help="Root directory to scan for video files.",
    )
    parser.add_argument(
        "--lang", "-l",
        default="eng",
        help="Subtitle language as a 3-letter ISO 639-3 code (default: eng).",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-download even if a subtitle file already exists.",
    )
    parser.add_argument(
        "--providers", "-p",
        nargs="*",
        help="Subtitle providers to use (default: opensubtitlescom podnapisi gestdown).",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging.",
    )
    args = parser.parse_args()

    setup_logging(args.verbose)

    scan_dir = Path(args.dir)
    if not scan_dir.is_dir():
        print(f"Error: '{scan_dir}' is not a valid directory.")
        sys.exit(1)

    language = Language(args.lang)

    # Configure subliminal cache (speeds up repeated runs)
    cache_file = LOG_DIR / "subliminal_cache.dbm"
    subliminal.region.configure(
        "dogpile.cache.dbm",
        arguments={"filename": str(cache_file)},
    )

    print(f"Scanning: {scan_dir}")
    print(f"Language: {language}")
    print()

    video_paths = find_videos(str(scan_dir))
    if not video_paths:
        print("No video files found.")
        sys.exit(0)

    print(f"Found {len(video_paths)} video file(s). Scanning metadata...")
    videos = scan_videos(video_paths)
    if not videos:
        print("Could not parse any video files.")
        sys.exit(0)

    print(f"Parsed {len(videos)} video(s). Searching for subtitles...\n")
    results = download_subtitles(videos, language, providers=args.providers, overwrite=args.overwrite)

    write_log(results)
    print_summary(results)


if __name__ == "__main__":
    main()
