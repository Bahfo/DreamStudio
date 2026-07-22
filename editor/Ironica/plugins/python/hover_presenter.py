"""
Presenter layer for formatting hover data into human-readable representations.

Provides three output formats:

- ``to_markdown`` -- Markdown text (for plain-text consumers).
- ``to_html`` -- Rich HTML suitable for ``QLabel`` with rich-text support
  (used by the ``DocumentationFlyout``).
- ``to_qt_tooltip`` -- Minimal HTML4 subset that ``QToolTip.showText()``
  can render.  Only uses ``<b>``, ``<i>``, ``<font>``, ``<br>``, ``<p>``,
  and ``<table>`` tags with inline CSS.
"""

import html as _html
from typing import Optional
from .domain_models import HoverDetails


class HoverPresenter:
    """Converts ``HoverDetails`` domain models into display-ready text."""

    # ------------------------------------------------------------------
    # Markdown
    # ------------------------------------------------------------------

    @staticmethod
    def to_markdown(details: Optional[HoverDetails]) -> str:
        """Return a Markdown representation of *details*."""
        if not details:
            return ""

        lines = []

        kind_label = details.kind.upper() if details.kind else "SYMBOL"
        lines.append(f"### {details.name} ({kind_label})")
        lines.append("---")

        lines.append("```python")
        lines.append(details.signature)
        lines.append("```")

        if details.parameters:
            lines.append("\n**Parameters:**\n")
            for param in details.parameters:
                s = f"* **`{param.name}`**"
                if param.type_hint:
                    s += f": *{param.type_hint}*"
                if param.default_value is not None:
                    s += f" = `{param.default_value}`"
                lines.append(s)

        if details.return_type:
            lines.append(f"\n**Returns:** *{details.return_type}*")

        if details.docstring:
            lines.append("\n---")
            lines.append(HoverPresenter._clean_docstring(details.docstring))

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Qt-compatible tooltip HTML (for QToolTip.showText)
    # ------------------------------------------------------------------

    @staticmethod
    def to_qt_tooltip(details: Optional[HoverDetails]) -> str:
        """Return an HTML string safe for ``QToolTip.showText()``.

        Qt's tooltip renderer only supports a strict subset of HTML 4:
        ``<b>``, ``<i>``, ``<u>``, ``<font>``, ``<br>``, ``<p>``, and
        ``<table>``/``<tr>``/``<td>``.  No ``<pre>``, ``<code>``,
        ``<div>``, ``<h1>``-``<h6>``, ``<ul>``, ``<li>``, or ``<hr>``.
        """
        if not details:
            return ""

        parts = []

        # -- Header: name + kind --
        kind_label = _html.escape(details.kind.upper() if details.kind else "SYMBOL")
        name_esc = _html.escape(details.name)
        parts.append(
            f'<b style="color:#569CD6;">{name_esc}</b>'
            f' <font style="color:#888888;">({kind_label})</font>'
        )

        # -- Signature code block (rendered as a table with bg colour) --
        sig_esc = _html.escape(details.signature)
        parts.append(
            '<table style="margin-top:4px;" cellspacing="0" cellpadding="4">'
            "<tr>"
            f'<td style="background-color:#1E1E1E; color:#D4D4D4; '
            f'font-family:monospace; font-size:12px;">'
            f'<pre style="margin:0; white-space:pre-wrap;">{sig_esc}</pre>'
            "</td>"
            "</tr>"
            "</table>"
        )

        # -- Parameters --
        if details.parameters:
            parts.append("<br/><b>Parameters:</b>")
            for param in details.parameters:
                p_name = _html.escape(param.name)
                line = f"<br/>&nbsp;&nbsp;&#8226;&nbsp;<b>{p_name}</b>"
                if param.type_hint:
                    line += (
                        f' <font color="#4EC9B0;">'
                        f"{_html.escape(param.type_hint)}</font>"
                    )
                if param.default_value is not None:
                    line += (
                        f' = <font color="#B5CEA8">'
                        f"{_html.escape(param.default_value)}</font>"
                    )
                parts.append(line)

        # -- Return type --
        if details.return_type:
            ret_esc = _html.escape(details.return_type)
            parts.append(
                f'<br/><b>Returns:</b> <font color="#4EC9B0;">{ret_esc}</font>'
            )

        # -- Docstring --
        if details.docstring:
            cleaned = HoverPresenter._clean_docstring(details.docstring)
            doc_esc = _html.escape(cleaned).replace("\n", "<br/>")
            parts.append(f'<hr style="margin:6px 0;"/>')
            parts.append(
                f'<font style="color:#A9A9A9; font-style:italic;">' f"{doc_esc}</font>"
            )

        return "".join(parts)

    # ------------------------------------------------------------------
    # QLabel-compatible HTML (for DocumentationFlyout)
    # ------------------------------------------------------------------

    @staticmethod
    def to_html(details: Optional[HoverDetails]) -> str:
        """Return rich HTML suitable for rendering inside a ``QLabel``.

        Uses ``<pre>``, ``<table>``, ``<b>``, ``<font>``, ``<br>``,
        ``<p>`` -- all supported by Qt's rich-text engine in ``QLabel``.
        """
        if not details:
            return ""

        parts = []

        # -- Header --
        kind_label = _html.escape(details.kind.upper() if details.kind else "SYMBOL")
        name_esc = _html.escape(details.name)
        parts.append(
            f'<p style="margin:0;">'
            f'<b style="color:#569CD6; font-size:14px;">{name_esc}</b>'
            f' <span style="color:#888888; font-size:12px;">({kind_label})</span>'
            f"</p>"
        )

        # -- Signature block --
        sig_esc = _html.escape(details.signature)
        parts.append(
            '<table style="margin:4px 0;" cellspacing="0" cellpadding="6" '
            'width="100%">'
            "<tr>"
            f'<td style="background-color:#1E1E1E; color:#D4D4D4; '
            f'font-family:monospace; font-size:12px; border-radius:4px;">'
            f'<pre style="margin:0; white-space:pre-wrap;">{sig_esc}</pre>'
            "</td>"
            "</tr>"
            "</table>"
        )

        # -- Parameters --
        if details.parameters:
            parts.append('<p style="margin:8px 0 4px 0;"><b>Parameters:</b></p>')
            parts.append('<table style="margin:0;" cellspacing="0" cellpadding="2">')
            for param in details.parameters:
                p_name = _html.escape(param.name)
                cells = f'<td style="padding-right:8px;"><b style="color:#9CDCFE;">{p_name}</b></td>'
                if param.type_hint:
                    cells += (
                        f'<td style="padding-right:8px;">'
                        f'<font color="#4EC9B0;">'
                        f"{_html.escape(param.type_hint)}</font></td>"
                    )
                else:
                    cells += "<td></td>"
                if param.default_value is not None:
                    cells += (
                        f'<td><font color="#B5CEA8">'
                        f"= {_html.escape(param.default_value)}</font></td>"
                    )
                parts.append(f"<tr>{cells}</tr>")
            parts.append("</table>")

        # -- Return type --
        if details.return_type:
            ret_esc = _html.escape(details.return_type)
            parts.append(
                f'<p style="margin:8px 0 4px 0;"><b>Returns:</b> '
                f'<font color="#4EC9B0;">{ret_esc}</font></p>'
            )

        # -- Docstring --
        if details.docstring:
            cleaned = HoverPresenter._clean_docstring(details.docstring)
            doc_esc = _html.escape(cleaned).replace("\n", "<br/>")
            parts.append(
                '<hr style="border:0; border-top:1px solid #444444; ' 'margin:8px 0;"/>'
            )
            parts.append(
                f'<p style="color:#A9A9A9; font-style:italic;">' f"{doc_esc}</p>"
            )

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _clean_docstring(docstring: str) -> str:
        """Strip common leading indentation from a docstring."""
        lines = docstring.expandtabs(4).splitlines()
        if not lines:
            return ""

        margin = 99999
        for line in lines[1:]:
            content = len(line) - len(line.lstrip())
            if line.strip() and content < margin:
                margin = content

        trimmed = [lines[0].strip()]
        if margin < 99999:
            for line in lines[1:]:
                trimmed.append(line[margin:].rstrip())

        while trimmed and not trimmed[0]:
            trimmed.pop(0)
        while trimmed and not trimmed[-1]:
            trimmed.pop()

        return "\n".join(trimmed)
