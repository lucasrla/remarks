# remarks

Extract your marks (highlights, scribbles, annotations) and convert them to `Markdown`, `PDF`, `PNG`, and `SVG`. 

`remarks` works with PDFs annotated on [reMarkable™ paper tablets](https://remarkable.com), both 1st and 2nd generation.

Please note that `remarks` is still highly experimental software. In any case, pull requests are warmly welcome!


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

And then use `remarks` to export annotated pages to `Markdown`, `PDF`, `PNG`, or `SVG` on your computer.

`PDF`:

- The `--targets pdf` flag outputs a directory with single-page `PDF` files for each annotated page.
- The `--combined_pdf` flag outputs an all-in-one `PDF` file (the original `PDF` with all annotated pages).
- The `--modified_pdf` flag outputs an `PDF` file with just the annotated pages.

`PNG`:

> <img width="300" alt="demo-remarks-png.png" src="https://user-images.githubusercontent.com/1920195/88480249-410aed80-cf2b-11ea-919b-22fb550ed9d7.png">

`Markdown`:

> <mark>WHAT IS LIFE?</mark>
> 
> Based on lectures delivered under the auspices of the <mark>Dublin Institute for</mark> <mark>Advanced Studies at Trinity College,</mark> Dublin, in February 1943
> 
> <mark>To</mark>
> <mark>the memory of My</mark> <mark>Parents</mark>

`SVG`:

- Please note that the `SVG` image file includes only the annotations, not the original PDF content.


# Compatibility and dependencies

Because `remarks` depends only on [PyMuPDF](https://github.com/pymupdf/PyMuPDF) and [Shapely](https://github.com/Toblerity/Shapely), there is no need to install `imagemagick`, `opencv`, or any additional image library. Both PyMuPDF and Shapely have pre-built wheels [[1](https://pypi.org/project/PyMuPDF/1.18.4/#files), [2](https://pypi.org/project/Shapely/1.7.1/#files)] for several platforms (macOS, Linux, Windows) and recent Python versions, so their installation should be easy and smooth for most setups.

I use `remarks` with a [reMarkable 1](https://remarkable.com/store/remarkable) tablet running software version `2.5.0.27` on macOS Catalina (`10.15.x`) with CPython `3.8.x`. I don't have other devices to test it thoroughly, but I expect `remarks` to work just fine in all common setups, including with [remarkable 2](https://remarkable.com/store/remarkable-2/).

Incidentally, please help me keep track of `remarks` compatibility across different setups:

- If it is working well for you, [make a quick comment with your setup](https://github.com/lucasrla/remarks/discussions/8)
- If you run into any problems, [raise an issue](https://github.com/lucasrla/remarks/issues/new/choose)

If [OCRmyPDF](https://github.com/jbarlow83/OCRmyPDF) is available on your computer, `remarks` may (optionally) use it to OCR PDFs before extracting their highlighted text.

# Setup

To get `remarks` up and running on your local machine, follow the instructions below:

## 1. Copy reMarkable's files to your computer

In order to reconstruct your highlights and annotations, `remarks` relies on specific files that are created by the reMarkable device as you use it. Because these specific files are internal to the reMarkable device, first we need to transfer them to your computer.

There are, broadly speaking, four options for getting them to your computer. Choose the one that fits you the best:

- **Copy from reMarkable's official desktop application**  
  If you have a [reMarkable's official desktop app](https://support.remarkable.com/hc/en-us/articles/360002665378-Desktop-app) installed, the files we need are already easily available on your computer. For macOS users, the files are located at `~/Library/Application\ Support/remarkable/desktop`. To avoid interfering with reMarkable's own app, all we need to do is copy and paste all the contents of `~/Library/Application\ Support/remarkable/desktop` to another directory you can safely interact with (for instance, a new one called `~/Documents/remarkable/docs`).

- **Use `rsync` ([about](https://en.wikipedia.org/wiki/Rsync))**  
  Check out the repository [@lucasrla/remarkable-utils](https://github.com/lucasrla/remarkable-utils) for the SSH & `rsync` setup I use (which includes automatic backups based on `cron`). 

- **Use `scp` ([about](https://en.wikipedia.org/wiki/Secure_copy_protocol))**  
  On your reMarkable tablet, go to `Menu > Settings > Help > About`, then tap on `Copyrights and licenses`. In `General information`, right after the section titled "GPLv3 Compliance", there will be the username (`root`), password and IP addresses needed for `SSH`. Using these credentials, `scp` the contents of `/home/root/.local/share/remarkable/xochitl` from your reMarkable to a directory on your computer. (Copying may take a while depending on the size of your document collection and the quality of your WiFi network.) To prevent any unintented interruptions, you can (optionally) switch off the `Auto sleep` feature in `Menu > Settings > Battery` before transferring your files.

- **Use [@juruen/rmapi](https://github.com/juruen/rmapi) or [@subutux/rmapy](https://github.com/subutux/rmapy)**  
  Both are free and open source software that allow you to access your reMarkable tablet files through the reMarkable's cloud service.

## 2. Clone this repository and install the dependencies

> **⚠️ Users on macOS Big Sur:**  
> - If you use `pip`, upgrade it to `>=20.3` via `pip install --upgrade pip`. [[#988](https://github.com/pypa/pip/issues/988#issuecomment-735451004)]
> - If you use `poetry`, it seems a fix is still pending. Follow [[#3458](https://github.com/python-poetry/poetry/issues/3458)] for updates
> - For more information on the impact of this issue to installing `remarks`, see [[#7](https://github.com/lucasrla/remarks/issues/7)]

```sh
### 2.1 Clone
git clone https://github.com/lucasrla/remarks.git && cd remarks


### 2.2 Create a virtual environment

# I like pyenv [https://github.com/pyenv/pyenv] 
# and pyenv-virtualenv [https://github.com/pyenv/pyenv-virtualenv]:
pyenv virtualenv remarks && pyenv local remarks

# But of course you are free to use any of the many alternatives
# e.g. virtualenv, virtualenvwrapper


### 2.3 Install the dependencies

# Personally, I prefer using poetry [http://python-poetry.org] for managing dependencies:
poetry install

# But pip works fine as well:
pip install -r requirements.txt
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

python -m remarks demo/on-computable-numbers/xochitl demo/on-computable-numbers --targets png md pdf --combined_pdf
```

A few other examples:

```sh
# Assuming your `xochitl` files are at `~/backups/remarkable/xochitl/`

python -m remarks ~/backups/remarkable/xochitl/ example_1/ --ann_type highlights --targets md --combined_pdf

python -m remarks ~/backups/remarkable/xochitl/ example_2/ --targets png
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
