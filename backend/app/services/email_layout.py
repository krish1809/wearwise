"""How WearWise's emails are put together: the same words as plain text and as simple HTML (no
images, web fonts, or scripts, so they read the same in any mail app), built side by side so the
two can't say different things."""

import html
from dataclasses import dataclass, field

STYLE = "font-family: Arial, sans-serif; font-size: 15px; line-height: 1.5; color: #1F2A44"


@dataclass
class Letter:
    text: list[str] = field(default_factory=list)
    html: list[str] = field(default_factory=list)

    def paragraph(self, words: str) -> None:
        self.text.append(words)
        self.html.append(f"<p>{html.escape(words)}</p>")

    def heading(self, words: str, colour: str | None = None) -> None:
        """A heading, with a dot of colour before it when there's one (decorative: the
        colour's name is always in the words)."""
        self.text.append(words.upper())
        dot = (
            f'<span style="display:inline-block;width:12px;height:12px;border-radius:6px;'
            f'background:{html.escape(colour)};border:1px solid #C9CCD3;margin-right:8px">'
            "</span>"
            if colour
            else ""
        )
        self.html.append(
            f'<h2 style="font-size:17px;margin:24px 0 4px">{dot}{html.escape(words)}</h2>'
        )

    def link(self, label: str, url: str) -> None:
        self.text.append(f"{label}: {url}")
        self.html.append(f'<p><a href="{html.escape(url)}">{html.escape(label)}</a></p>')

    def links(self, lead: str, links: list[tuple[str, str]]) -> None:
        """A line of links after a few words: "Look for it: Myntra · AJIO"."""
        self.text.append(lead + "\n" + "\n".join(f"- {label}: {url}" for label, url in links))
        joined = " · ".join(
            f'<a href="{html.escape(url)}">{html.escape(label)}</a>' for label, url in links
        )
        self.html.append(f"<p>{html.escape(lead)} {joined}</p>")

    def small(self, words: str) -> None:
        self.text.append(words)
        self.html.append(f'<p style="font-size:13px;color:#5B6478">{html.escape(words)}</p>')

    def finish(self) -> tuple[str, str]:
        return (
            "\n\n".join(self.text) + "\n",
            f'<div style="{STYLE}">' + "".join(self.html) + "</div>",
        )
