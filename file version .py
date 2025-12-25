# you should go down and change the last lines where you need to choose your download folder to download cars to
# %%
import warnings
import zipfile
import random
import os
import requests
import shutil
from justhtml import JustHTML
from shutil import unpack_archive
from tempfile import TemporaryDirectory

def load_page(url):
    r = requests.get(url)
    r.raise_for_status()
    return r.text

def download_file(url, dir: str | os.PathLike, ext_blacklist=None):
    r = requests.get(url, stream=True)
    r.raise_for_status()

    fname = r.headers.get("Content-Disposition")
    if fname is None: fname = str(random.random())

    if ext_blacklist is not None:
        if isinstance(ext_blacklist, str): ext_blacklist = (ext_blacklist, )
        if fname.strip().lower().endswith(tuple(ext_blacklist)):
            return None

    with open(os.path.join(dir, fname), 'wb') as f:
        shutil.copyfileobj(r.raw, f) # type:ignore

    return os.path.join(dir, fname)

def get_topics(html: JustHTML) -> set[str]:
    topics = set()
    for el in html.query("div > a"):
        if "href" in el.attrs:
            href = el.attrs["href"]
            if href.startswith("./viewtopic.php?t="):
                topics.add(f"https://forum.generally-racers.com/{href[2:]}")
    return topics

def get_download_links(html: JustHTML):
    links = set()
    for el in html.query("dt > a"):
        if "href" in el.attrs:
            href = el.attrs["href"]
            if href.startswith("./download"):
                links.add(f"https://forum.generally-racers.com/{href[2:]}")
    return links

def get_current_page_number(html: JustHTML):
    for el in html.query("ul > li"):
        if el.attrs.get("class",  None) == "active":
            return int(el.children[0].to_text())
    return 1

def get_next_page_url(html: JustHTML):
    page_number = get_current_page_number(html)

    for el in html.query("ul > li > a"):
        if (el.attrs.get("class",  None) == "button") and ("href" in el.attrs):
            try:
                n = int(el.to_text())
            except (ValueError, TypeError):
                continue

            if n == page_number + 1:
                href = el.attrs["href"]
                return f"https://forum.generally-racers.com/{href[2:]}"

    return None


def unpack(file, dir):
    try:
        shutil.unpack_archive(file, dir)
    except Exception:
        with zipfile.ZipFile(file, "r") as zip_ref:
            zip_ref.extractall(dir)

def get_car_trk_files(file: str | os.PathLike, download_path: str | os.PathLike) -> None:
    if str(file).lower().strip().endswith((".car", ".trk")):
        print(f"saved {os.path.basename(file)}")
        if os.path.basename(file) in os.listdir(download_path):
            print(f"info: {os.path.basename(file)} already exists, skipping")
            return
        shutil.move(file, os.path.join(download_path, os.path.basename(file)))
    else:
        try:
            with TemporaryDirectory() as tmpdir:
                unpack(file, tmpdir)
                for root, dirs, files in os.walk(tmpdir):
                    for f in files:
                        get_car_trk_files(os.path.join(root, f), download_path)
        except Exception:
            pass

_BLACKLIST = (".jpeg", ".jpg", ".png", ".gif", ".mp4", ".mov", ".mp3", ".wav", ".tiff")
class GeneRallyCarDownloader:
    def __init__(self, download_path: str | os.PathLike):
        self.download_urls: set[str] = set()
        self.visited_pages: set[tuple[str, int]] = set()
        self.download_path = download_path

    def scrap_page(self, html: JustHTML):
        """downloads all files and returns url of next page or none"""
        dl_links = get_download_links(html)
        for dl_link in dl_links:
            if "&mode=view" in dl_link: continue
            with TemporaryDirectory() as tmpdir:
                path = download_file(dl_link, tmpdir, _BLACKLIST)
                if path is not None:
                    get_car_trk_files(path, self.download_path)

    def run(self, root = "https://forum.generally-racers.com/viewforum.php?f=7"):
        current_page_url = root
        current_html = JustHTML(load_page(current_page_url))
        page_idx = 1
        while True:
            print(f"# ------------------------ PROCESSING PAGE {page_idx} ------------------------ #")
            topics = get_topics(current_html)
            for topic_url in topics:
                topic_html = JustHTML(load_page(topic_url))
                while True:
                    self.scrap_page(topic_html)
                    next_url = get_next_page_url(topic_html)
                    if next_url is None: break
                    topic_html = JustHTML(load_page(next_url))

            current_page_url = get_next_page_url(current_html)
            if current_page_url is None: break
            current_html = JustHTML(load_page(current_page_url))
            page_idx += 1

if __name__ == "__main__":
  scrapper = GeneRallyCarDownloader("/var/mnt/issd/files 2/programming/experiments/generally scrapper/downloads")
  scrapper.run()


