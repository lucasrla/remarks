# remarks

Extract annotations (text highlights and scribbles) and convert them to `Markdown`, `PDF`, `PNG`, and `SVG`. 

`remarks` works with documents annotated on [reMarkable™ paper tablets](https://remarkable.com) &mdash; both 1st and 2nd generation &mdash; up to software version `2.15.0.1067`.

Note that `remarks` not only is highly experimental, it is _very likely to break_ after you update the software of your tablet. I might find some spare time to continue to maintain it, but I make no promises.

`remarks` code is fairly straightforward but not elegant at all. It has been put together in a couple of hours. You are free to fork and run with it though ;)

Most of the actual heavy lifting has been done by the open source community and PyMuPDF. See [Credits and Acknowledgements](#credits-and-acknowledgements).


# Some use cases

- **In: PDF highlighted on reMarkable → Out: PDF with parseable highlights**  
Someone who highlights lots of PDFs (e.g., researchers, academics, etc) can export their highlights for processing with a reference management tool, like [Zotero](https://www.zotero.org) [[#2](https://github.com/lucasrla/remarks/issues/2#issuecomment-732166093)].

- **Extract highlighted text from PDF to Markdown**  
Infovores of the world can export highlighted text to [Markdown](https://en.wikipedia.org/wiki/Markdown) and insert them into their preferred "tool for networked thought", like [Obsidian](https://obsidian.md/) or [Roam Research](https://roamresearch.com).

- **Export annotated PDF pages to full-page images**  
Sometimes having just the textual content is not enough, sometimes you need the actual (visual) context around your annotation. To help you in such situations, `remarks` can export each annotated PDF page to a [PNG](https://en.wikipedia.org/wiki/Portable_Network_Graphics) image file. Images can be easily uploaded or embedded anywhere, from personal websites to "tools for networked thought".


# A visual example

Highlight and annotate PDFs with your Marker on your reMarkable tablet: 

<!-- How to host images on GitHub but outside your repository? Open an issue, upload your images, and voila! Trick learned from http://felixhayashi.github.io/ReadmeGalleryCreatorForGitHub/ -->

<img width="300" alt="IMG_0642-low.jpg" src="https://user-images.githubusercontent.com/1920195/88480247-3d776680-cf2b-11ea-9c30-061ec0e5cc60.jpg">

And then use `remarks` to export annotated pages to `Markdown`, `PDF`, `PNG`, or `SVG` on your computer:

<img width="300" alt="demo-remarks-png.png" src="https://user-images.githubusercontent.com/1920195/88480249-410aed80-cf2b-11ea-919b-22fb550ed9d7.png">

> <mark>WHAT IS LIFE?</mark>
> 
> Based on lectures delivered under the auspices of the <mark>Dublin Institute for</mark> <mark>Advanced Studies at Trinity College,</mark> Dublin, in February 1943
> 
> <mark>To</mark>
> <mark>the memory of My</mark> <mark>Parents</mark>


# Compatibility and dependencies

Because `remarks` depends only on [PyMuPDF](https://github.com/pymupdf/PyMuPDF) and [Shapely](https://github.com/shapely/shapely), there is no need to install `imagemagick`, `opencv`, or any additional image library. Both PyMuPDF and Shapely have [pre-built](https://pypi.org/project/PyMuPDF/#files) [wheels](https://pypi.org/project/Shapely/#files) for several platforms (macOS, Linux, Windows) and recent Python 3 versions, so installing them should be smooth and easy for most people.

I currently use `remarks` with [reMarkable 1](https://remarkable.com/store/remarkable) and [reMarkable 2](https://remarkable.com/store/remarkable-2) tablets running software versions `2.14.3.1047` and `2.15.0.1067` on macOS Monterey (`12.6`) with CPython `3.10.x`. I don't have other equipment to test it thoroughly, but I expect `remarks` to work just fine in all common setups.

Incidentally, help the community keeping track of `remarks` compatibility across different setups:

- If it is working well for you, [make a quick comment with your setup](https://github.com/lucasrla/remarks/discussions/8)
- If you run into any problems, [raise an issue](https://github.com/lucasrla/remarks/issues/new/choose)

If [OCRmyPDF](https://github.com/ocrmypdf/OCRmyPDF) is available on your computer, `remarks` may (optionally) use it to OCR PDFs before extracting their highlighted text.


# Setup

To get `remarks` up and running on your local machine, follow the instructions below:

## 1. Copy reMarkable's "raw" document files to your computer

In order to reconstruct your highlights and annotations, `remarks` relies on specific files that are created by the reMarkable device as you use it. Because these specific files are internal to the reMarkable device, first we need to transfer them to your computer.

There are several options for getting them to your computer. Find below some suggestions. Choose whatever fits you:

- **Copy from reMarkable's official desktop application**  
  If you have a [reMarkable's official desktop app](https://support.remarkable.com/s/article/Desktop-app) installed, the files we need are already easily available on your computer. For macOS users, the files are located at `~/Library/Application\ Support/remarkable/desktop`. To avoid interfering with reMarkable's official app, copy and paste all the contents of `~/Library/Application\ Support/remarkable/desktop` to another directory (one that you can safely interact with – say, `~/Documents/remarkable/docs`).

- **Use `rsync`** ([i](https://en.wikipedia.org/wiki/Rsync))  
  Check out the repository [@lucasrla/remarkable-utils](https://github.com/lucasrla/remarkable-utils) for the SSH & `rsync` setup I use (which includes automatic backups based on `cron`). 

- **Use `scp`** ([i](https://en.wikipedia.org/wiki/Secure_copy_protocol))  
  On your reMarkable tablet, go to `Menu > Settings > Help`, then under `About` tap on `Copyrights and licenses`. In `General information`, right after the section titled "GPLv3 Compliance", there will be the username (`root`), password and IP address needed for `SSH`ing into it. Using these credentials, `scp` the contents of `/home/root/.local/share/remarkable/xochitl` from your reMarkable to a directory on your computer. (Copying may take a while depending on the size of your document collection and the quality of your WiFi network.) To prevent any unintented interruptions, you can (optionally) switch off the `Auto sleep` feature in `Menu > Settings > Battery` before transferring your files.

- **Use [@juruen/rmapi](https://github.com/juruen/rmapi) or [@subutux/rmapy](https://github.com/subutux/rmapy)**  
  Both are free and open source software that allow you to access your reMarkable tablet files through reMarkable's cloud service.

## 2. Clone this repository and install the dependencies

> **⚠️ Users on Apple Silicon Macs (M1, M1 Pro, M2, etc):**  
> - You must install `swig` and `freetype` via `brew` before running `poetry install` (see below)

```sh
### 2.1 Clone
git clone https://github.com/lucasrla/remarks.git && cd remarks


### 2.2 Create and activate a virtual environment

# If you're using poetry, a new virtual env should be created automatically (given our `poetry.toml`)
# Any other popular alternative (e.g. virtualenv, virtualenvwrapper, etc) should work too


### 2.3 Install the dependencies

# If you're on an Apple Silicon computer, you must run:
# brew install swig freetype
#
# This is necessary because (as of October 2022) PyMuPDF does not provide pre-built macOS arm64 wheels
# h/t: https://github.com/pymupdf/PyMuPDF/discussions/875#discussioncomment-3423026
#
# In case you don't have `brew` available, install it first: https://brew.sh/

# Install dependencies with:
poetry install
```


# Usage and Demo

Run `remarks` and check out what arguments are available:

```sh
python -m remarks --help
```

Next, for a quick hands-on experience of `remarks`, run the demo:

```sh
# Alan Turing's 1936 foundational paper (with a few highlights and scribbles)

# Original PDF file downloaded from:
# "On Computable Numbers, with an Application to the Entscheidungsproblem"
# https://londmathsoc.onlinelibrary.wiley.com/doi/abs/10.1112/plms/s2-42.1.230

python -m remarks demo/on-computable-numbers/xochitl remarks-example/ --per_page_targets png md pdf --modified_pdf
```

A few other examples:

```sh
# Assuming your `xochitl` files are at `~/backups/remarkable/xochitl/`

python -m remarks ~/backups/remarkable/xochitl/ example_1/ --ann_type highlights --per_page_targets md

python -m remarks ~/backups/remarkable/xochitl/ example_2/ --per_page_targets png
```


# Credits and Acknowledgements

- [@JorjMcKie](https://github.com/JorjMcKie) who wrote and maintains the great [PyMuPDF](https://github.com/pymupdf/PyMuPDF)

- [u/stucule](https://www.reddit.com/user/stucule/) who [posted to r/RemarkableTablet](https://www.reddit.com/r/RemarkableTablet/comments/7c5fh0/work_in_progress_format_of_the_lines_files/) the first account (that I could find online) about reverse engineering `.rm` files

- [@ax3l](https://github.com/ax3l) who wrote [lines-are-rusty](https://github.com/ax3l/lines-are-rusty) / [lines-are-beautiful](https://github.com/ax3l/lines-are-beautiful) and also [contributed to reverse engineering of `.rm` files](https://plasma.ninja/blog/devices/remarkable/binary/format/2017/12/26/reMarkable-lines-file-format.html)

- [@edupont, @Liblor, @florian-wagner, and @jackjackk for their contributions to rM2svg](https://github.com/reHackable/maxio/blob/33cdc1706b29698c15aac647619374e895ed3869/tools/rM2svg)

- [@ericsfraga, @jmiserez](https://github.com/jmiserez/maxio/blob/ee15bcc86e4426acd5fc70e717468862dce29fb8/tmp-rm16-ericsfraga-rm2svg.py), [@peerdavid](https://github.com/peerdavid/rmapi/blob/master/tools/rM2svg), [@phill777](https://github.com/phil777/maxio) and [@lschwetlick](https://github.com/lschwetlick/maxio/blob/master/rm_tools/rM2svg.py) for updating rM2svg to the most recent `.rm` format

- [@lschwetlick](https://github.com/lschwetlick) who wrote [rMsync](https://github.com/lschwetlick/rMsync) and also two blog posts about reMarkable-related software [[1](http://lisaschwetlick.de/blog/2018/03/25/reMarkable/), [2](http://lisaschwetlick.de/blog/2019/06/10/reMarkable-Update/)]

- [@soulisalmed](https://github.com/soulisalmed) who wrote [biff](https://github.com/soulisalmed/biff)

- [@benlongo](https://github.com/benlongo) who wrote [remarkable-highlights](https://github.com/benlongo/remarkable-highlights)

For more reMarkable resources, check out [awesome-reMarkable](https://github.com/reHackable/awesome-reMarkable) and [remarkablewiki.com](https://remarkablewiki.com/).


# License

`remarks` is [Free Software](https://www.gnu.org/philosophy/free-sw.html) distributed under the [GNU General Public License v3.0](https://choosealicense.com/licenses/gpl-3.0/).


# Disclaimers

This is a hobby project of an enthusiastic reMarkable user. There is no warranty whatsoever. Use it at your own risk.

> The author(s) and contributor(s) are not associated with reMarkable AS, Norway. reMarkable is a registered trademark of reMarkable AS in some countries. Please see https://remarkable.com for their products.
