import re
from typing import List

import yaml
from rmscene.scene_items import GlyphRange

from remarks.Document import Document


class ObsidianMarkdownFile:
    def __init__(self):
        self.content = ""
        self.page_content = {}

    def add_document_header(self, document: Document):
        frontmatter = {}
        if document.rm_tags:
            frontmatter["remarkable_tags"] = list(
                map(lambda tag: f"#{tag}", document.rm_tags)
            )

        frontmatter_md = ""
        if len(frontmatter) > 0:
            frontmatter_md = f"""---
{yaml.dump(frontmatter, indent=2)}
---"""

        # the yaml library outputs tags as quoted, we need unquoted for obsidian to be able to parse them.
        # ie, "#obsidian" -> #obsidian
        frontmatter_md = re.sub("- [\"'](#[a-zA-Z0-9]+)[\"']", "- \\1", frontmatter_md)

        self.content += f"""{frontmatter_md}

# {document.name}

## Pages

"""

    def save(self, location: str):
        for page_idx in sorted(self.page_content.keys()):
            self.content += self.page_content[page_idx]

        with open(f"{location} _obsidian.md", "w") as f:
            f.write(self.content)

    def add_highlights(
        self, page_idx: int, highlights: List[GlyphRange], doc: Document
    ):
        highlight_content = ""
        joined_highlights = []
        highlights = sorted(highlights, key=lambda h: h.start)
        if len(highlights) > 0:
            if len(highlights) == 1:
                highlight_content += f"""### [[{doc.name}.pdf#page={page_idx}|{doc.name}, page {page_idx}]]

> {highlights[0].text}

"""
            else:
                # first, highlights may be disjointed. We want to join highlights that belong together
                paired_highlights = [
                    (highlights[i], highlights[i + 1])
                    for i, _ in enumerate(highlights[:-1])
                ]
                assert len(paired_highlights) > 0
                joined_highlight = []
                for current, next in paired_highlights:
                    distance = next.start - (current.start + current.length)
                    joined_highlight.append(current.text)
                    if distance > 2:
                        joined_highlights.append(joined_highlight)
                        joined_highlight = []

                highlight_content += f"### [[{doc.name}.pdf#page={page_idx}|{doc.name}, page {page_idx}]]\n"

                for joined_highlight in joined_highlights:
                    highlight_text = " ".join(joined_highlight)
                    highlight_content += f"\n> {highlight_text}\n"

                highlight_content += "\n"

        if highlight_content:
            self.page_content[page_idx] = highlight_content
