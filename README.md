# remarks

Extract your marks (highlights, scribbles, annotations) and convert them to `Markdown`, `PDF`, `PNG`, and `SVG`. 

`remarks` works with PDFs annotated on [reMarkable™ paper tablets](https://remarkable.com).

Please note that `remarks` is still highly experimental software. In any case, pull requests are warmly welcome!


# Some use cases

## In: PDF highlighted on reMarkable | Out: PDF with parseable highlights
Someone who highlights lots of PDFs (e.g., academics) can export their highlights and process them in a reference management tool, like [Zotero](https://www.zotero.org) ([#2](https://github.com/lucasrla/remarks/issues/2#issuecomment-732166093)).

## Extract highlighted text to Markdown
Infovores of the world can export highlighted text to [.md](https://en.wikipedia.org/wiki/Markdown) files that can be imported into their preferred "tool for networked thought", like [Obsidian](https://obsidian.md/) or [Roam Research](https://roamresearch.com).

## Export annotated pages to full-page images
Sometimes having just the textual content is not enough, sometimes you need the actual (visual) context around your annotation. To help you in such situations, `remarks` can export each annotated PDF page to a [.png](https://en.wikipedia.org/wiki/Portable_Network_Graphics) file. After that, these images can be, for example, embedded to your "tool for networked thought".


# A visual example

Highlight and annotate PDFs with your Marker on your reMarkable tablet: 

<!-- How to host images on GitHub but outside your repository? Open an issue, upload your images, and voila! Trick learned from http://felixhayashi.github.io/ReadmeGalleryCreatorForGitHub/ -->

<img width="300" alt="IMG_0642-low.jpg" src="https://user-images.githubusercontent.com/1920195/88480247-3d776680-cf2b-11ea-9c30-061ec0e5cc60.jpg">

And then use `remarks` to export annotated pages to `Markdown`, `PDF`, `PNG`, or `SVG` on your computer.

`PDF`:

- The `--combined_pdf` flag outputs an all-in-one `PDF` file (the original `PDF` with all annotated pages).
- The `--targets pdf` flag outputs a directory with single-page `PDF` files for each annotated page.

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


# Setup

Although I expect `remarks` to be easy to install and use on Linux and Windows, so far it has been used only on a macOS Catalina computer and a ([1st generation](https://remarkable.com/store/remarkable)) reMarkable tablet with software versions `2.2.0.48`, `2.3.0.16`, and `2.4.1.30`.

Because `remarks` depends only on [PyMuPDF](https://github.com/pymupdf/PyMuPDF), [Shapely](https://github.com/Toblerity/Shapely), and Python 3.8+, there is no need to install `imagemagick`, `opencv`, or any additional image library. If [OCRmyPDF](https://github.com/jbarlow83/OCRmyPDF) is available on your computer, `remarks` may (optionally) use it.

## 1. Copy files from the `xochitl` directory to your computer

I find using `rsync` the easiest way to copy files from/to your reMarkable tablet. Check out the repository [lucasrla/remarkable-utils](https://github.com/lucasrla/remarkable-utils) for the SSH & `rsync` setup I use (which includes automatic backups based on `cron`). 

Alternatively, you can use the good old `scp` to copy files from the tablet to your computer:

- On your reMarkable tablet, go to `Menu > Settings > Help > About`, then tap on `Copyrights and licenses`. In `General information`, right after the section titled "GPLv3 Compliance", there will be the username (`root`), password and IP addresses needed for `SSH`.

- Using these credentials, `scp` the contents of `/home/root/.local/share/remarkable/xochitl` from your reMarkable to a directory on your computer. (Copying may take a while depending on the size of your document collection and the quality of your wifi network.)

- To prevent any unintented interruptions, you can (optionally) switch off the `Auto sleep` feature in `Menu > Settings > Battery` before transferring your files.

## 2. Clone this repository and install the dependencies

```sh
git clone https://github.com/lucasrla/remarks.git

cd remarks

pyenv virtualenv remarks && pyenv local remarks
# Or your tool of choice for managing environments

poetry install
# Or your tool of choice for managing dependencies (e.g., pip)

# pip install -r requirements.txt
# If you use pip, note that the requirements.txt file was created via:
# poetry export --without-hashes -f requirements.txt -o requirements.txt
```


# Usage & Demo

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

- [u/stuculu](https://www.reddit.com/user/stucule/) who posted to [r/RemarkableTablet](https://www.reddit.com/r/RemarkableTablet/comments/7c5fh0/work_in_progress_format_of_the_lines_files/) the first account (that I could find online) about reverse engineering `.rm` files

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
