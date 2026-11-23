#!/usr/bin/env python3
"""Download every Piano Jazz with Marian McPartland episode from NPR, one at a time.

Usage:
  ./download_piano_jazz.py [-o OUTDIR] [--delay SECONDS] [--keep-mp3] [--limit N] [--list] [--add-art]

NPR only serves these episodes as mp3 (no native m4a exists), so by default each
mp3 is downloaded and converted to m4a (AAC 256k) with ffmpeg. Use --keep-mp3 to
save the untouched original instead (best possible fidelity).
Already-downloaded files are skipped, so the script is safe to re-run/resume.
"""
import argparse, base64, html, json, os, re, shutil, subprocess, sys, time
import urllib.request

SERIES = "15773266"
SLUG = "marian-mcpartland-s-piano-jazz"
ARCHIVE = f"https://www.npr.org/partials/music/series/{SERIES}/{SLUG}/archive?start={{}}"
FIRST_PAGE = f"https://www.npr.org/series/{SERIES}/{SLUG}"
UA = "Mozilla/5.0 (piano-jazz-archiver; serial downloads)"
DATA_AUDIO = re.compile(r"data-audio='(\{.*?\})'")


def fetch(url, retries=4):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read().decode("utf-8", "replace")
        except Exception as e:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** attempt * 2)


def parse_page(text):
    items = []
    for raw in DATA_AUDIO.findall(text):
        try:
            d = json.loads(html.unescape(raw))
        except json.JSONDecodeError:
            continue
        if not d.get("audioUrl") or not d.get("available", True):
            continue
        enc = d["audioUrl"].strip()
        url = enc if enc.startswith("http") else None
        # Try as-is, then with padding fixed, then dropping a stray trailing char.
        for cand in (() if url else (enc, enc[:-1])):
            try:
                url = base64.b64decode(cand + "=" * (-len(cand) % 4)).decode()
                if url.startswith("http"):
                    break
                url = None
            except Exception:
                url = None
        if not url:
            print(f"  warning: could not decode audio URL for {d.get('title')!r}", file=sys.stderr)
            continue
        m = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", d.get("storyUrl", ""))
        items.append({
            "uid": d["uid"],
            "title": d.get("title", ""),
            "url": url,
            "date": "-".join(m.groups()) if m else "",
            "story": d.get("storyUrl", ""),
        })
    return items


def list_episodes(delay):
    seen, episodes, start = set(), [], 0
    while True:
        text = fetch(FIRST_PAGE if start == 0 else ARCHIVE.format(start))
        new = [i for i in parse_page(text) if i["uid"] not in seen]
        if not new:
            break
        for i in new:
            seen.add(i["uid"])
            episodes.append(i)
        start += len(new)
        print(f"  found {len(episodes)} episodes...", file=sys.stderr)
        time.sleep(delay)
    return episodes


def artist_of(title):
    t = re.sub(r"\s+on\s+piano\s+jazz.*$", "", title, flags=re.I).strip()
    t = re.sub(r"\s+in\s+the\s+studio\s*$", "", t, flags=re.I).strip()
    t = re.sub(r"^(piano jazz( classics)?|listen)\s*[:\-–]\s*", "", t, flags=re.I).strip()
    return t or title


def safe(name):
    return re.sub(r'[\\/:*?"<>|]', "-", name).strip(" .")


OG_IMAGE = re.compile(r'<meta\s+property="og:image"\s+content="([^"]+)"')


def has_art(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries",
         "stream=index", "-of", "csv=p=0", path],
        capture_output=True, text=True)
    return bool(out.stdout.strip())


def download_image(url, dest):
    """Fetch an image; fall back to the unresized original if the CDN rejects the
    resize query (some images 403), and convert anything not JPEG/PNG to JPEG."""
    for u in (url, url.split("?")[0]):
        try:
            req = urllib.request.Request(u, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
                shutil.copyfileobj(r, f)
            break
        except urllib.error.HTTPError:
            if u == url.split("?")[0]:
                raise
    with open(dest, "rb") as f:
        magic = f.read(8)
    if not (magic.startswith(b"\xff\xd8") or magic.startswith(b"\x89PNG")):
        conv = dest + ".conv.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", dest, "-frames:v", "1", conv],
                       check=True)
        os.replace(conv, dest)


def add_art(episodes, outdir, delay):
    """Embed each episode's NPR page image as cover art, without re-encoding audio."""
    seen_images = {}
    todo = [e for e in episodes if os.path.exists(os.path.join(outdir, e["file"]))]
    for n, e in enumerate(todo, 1):
        path = os.path.join(outdir, e["file"])
        if has_art(path):
            print(f"[{n}/{len(todo)}] skip (has art): {e['file']}")
            continue
        print(f"[{n}/{len(todo)}] {e['file']}")
        tmp_img, tmp_out = path + ".art.jpg", path + ".art.m4a"
        try:
            m = OG_IMAGE.search(fetch(e["story"].replace("\\/", "/")))
            if not m:
                print("   no image on episode page, skipped", file=sys.stderr)
                continue
            img = html.unescape(m.group(1))
            if img in seen_images:
                print(f"   warning: same image as {seen_images[img]!r}", file=sys.stderr)
            seen_images.setdefault(img, e["file"])
            download_image(img, tmp_img)
            subprocess.run(
                ["ffmpeg", "-y", "-loglevel", "error", "-i", path, "-i", tmp_img,
                 "-map", "0:a", "-map", "1:v", "-c", "copy", "-map_metadata", "0",
                 "-disposition:v:0", "attached_pic", "-f", "ipod", tmp_out],
                check=True)
            os.replace(tmp_out, path)
        except Exception as ex:
            print(f"   FAILED: {ex}", file=sys.stderr)
        finally:
            for t in (tmp_img, tmp_out):
                if os.path.exists(t):
                    os.remove(t)
        time.sleep(delay)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("-o", "--outdir", default="downloads")
    ap.add_argument("--delay", type=float, default=3.0, help="pause between episodes (s)")
    ap.add_argument("--keep-mp3", action="store_true", help="keep original mp3, no conversion")
    ap.add_argument("--limit", type=int, help="only process first N episodes")
    ap.add_argument("--add-art", action="store_true",
                    help="embed episode cover art into existing m4a files in OUTDIR (no re-encode)")
    ap.add_argument("--list", action="store_true", help="list episodes and exit")
    a = ap.parse_args()

    if not a.keep_mp3 and not shutil.which("ffmpeg"):
        sys.exit("ffmpeg is required for m4a output (brew install ffmpeg), or use --keep-mp3")

    print("Collecting episode list...", file=sys.stderr)
    episodes = list_episodes(min(a.delay, 1.5))
    if a.limit:
        episodes = episodes[: a.limit]

    # Build unique filenames; disambiguate repeat artists with the air date.
    ext = "mp3" if a.keep_mp3 else "m4a"
    counts = {}
    for e in episodes:
        e["artist"] = artist_of(e["title"])
        counts[e["artist"]] = counts.get(e["artist"], 0) + 1
    for e in episodes:
        base = f"Piano Jazz with Marian McPartland - {e['artist']}"
        if counts[e["artist"]] > 1 and e["date"]:
            base += f" ({e['date']})"
        e["file"] = safe(base) + "." + ext

    if a.list:
        for e in episodes:
            print(e["date"], e["file"])
        return

    if a.add_art:
        if a.keep_mp3:
            sys.exit("--add-art only supports m4a files")
        add_art(episodes, a.outdir, a.delay)
        return

    os.makedirs(a.outdir, exist_ok=True)
    total = len(episodes)
    for n, e in enumerate(episodes, 1):
        final = os.path.join(a.outdir, e["file"])
        if os.path.exists(final):
            print(f"[{n}/{total}] skip (exists): {e['file']}")
            continue
        print(f"[{n}/{total}] {e['file']}")
        src = e["url"].split("?")[0]  # drop tracking query string
        tmp = final + ".part.mp3"
        try:
            req = urllib.request.Request(src, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:
                shutil.copyfileobj(r, f)
            if a.keep_mp3:
                os.replace(tmp, final)
            else:
                part = final + ".part.m4a"
                date_tags = []
                if e["date"]:
                    date_tags = ["-metadata", f"date={e['date'][:4]}",
                                 "-metadata", f"comment=Aired on {e['date']}"]
                subprocess.run(
                    ["ffmpeg", "-y", "-loglevel", "error", "-i", tmp, "-vn",
                     "-c:a", "aac", "-b:a", "256k",
                     "-metadata", f"title={e['artist']}",
                     "-metadata", "album=Piano Jazz with Marian McPartland",
                     "-metadata", "artist=Marian McPartland",
                     *date_tags,
                     "-f", "ipod", part],
                    check=True)
                os.replace(part, final)
                os.remove(tmp)
        except Exception as ex:
            print(f"   FAILED: {ex}", file=sys.stderr)
            for p in (tmp, final + ".part.m4a"):
                if os.path.exists(p):
                    os.remove(p)
        time.sleep(a.delay)


if __name__ == "__main__":
    main()
