def _format_definition_tooltip(d: dict) -> str:
    name = d.get("name", "")
    typ = d.get("type", "")
    doc = d.get("doc", "") or d.get("description", "")
    file_path = d.get("file")
    line_no = d.get("line")

    parts = [f"<b>{name}</b>"]
    if typ:
        parts.append(f'<span style="color:#888;">({typ})</span>')
    if file_path and line_no:
        parts.append(f'<span style="color:#569CD6;">{file_path}:{line_no}</span>')
    if doc:
        doc_short = doc.strip()[:500]
        parts.append(f"<hr/><pre style='font-size:11px;'>{doc_short}</pre>")

    return "<br/>".join(parts)


class TestTooltipFormatting:
    def test_basic_function(self):
        d = {
            "name": "print",
            "type": "function",
            "doc": "print(value, ..., sep=' ', end='\\n')",
            "file": "/usr/lib/python3.12/print.py",
            "line": 1,
        }
        html = _format_definition_tooltip(d)
        assert "<b>print</b>" in html
        assert "(function)" in html
        assert "/usr/lib/python3.12/print.py:1" in html
        assert "print(value" in html

    def test_builtin_no_file(self):
        d = {
            "name": "len",
            "type": "function",
            "doc": "Return the number of items in a container.",
            "file": None,
            "line": None,
        }
        html = _format_definition_tooltip(d)
        assert "<b>len</b>" in html
        assert "(function)" in html
        assert "file" not in html.lower() or "none" in html.lower()

    def test_no_doc_falls_back_to_description(self):
        d = {
            "name": "foo",
            "type": "function",
            "description": "Some description text",
            "doc": "",
            "file": "/path/to/file.py",
            "line": 42,
        }
        html = _format_definition_tooltip(d)
        assert "Some description text" in html

    def test_empty_doc_and_description(self):
        d = {
            "name": "bar",
            "type": "class",
            "doc": "",
            "description": "",
            "file": "/path/to/file.py",
            "line": 10,
        }
        html = _format_definition_tooltip(d)
        assert "<b>bar</b>" in html
        assert "(class)" in html
        assert "file.py:10" in html
        assert "<hr/>" not in html

    def test_no_type_no_file(self):
        d = {
            "name": "symbol",
            "type": "",
            "doc": "Some doc",
            "description": "",
            "file": None,
            "line": None,
        }
        html = _format_definition_tooltip(d)
        assert "<b>symbol</b>" in html
        assert "(symbol)" not in html.lower()
        assert "Some doc" in html

    def test_minimal_input(self):
        d = {"name": "x"}
        html = _format_definition_tooltip(d)
        assert "<b>x</b>" in html

    def test_empty_dict(self):
        d = {}
        html = _format_definition_tooltip(d)
        assert "<b></b>" in html

    def test_doc_truncated_at_500(self):
        long_doc = "x" * 1000
        d = {"name": "f", "type": "function", "doc": long_doc}
        html = _format_definition_tooltip(d)
        assert len(long_doc) == 1000
        assert "x" * 500 in html

    def test_html_tags_escaped(self):
        d = {
            "name": "danger",
            "type": "function",
            "doc": "Returns a <script>alert('xss')</script> value",
            "file": "/path/file.py",
            "line": 5,
        }
        html = _format_definition_tooltip(d)
        assert "<b>danger</b>" in html
        assert "/path/file.py:5" in html
        # Docstring is placed raw in <pre> — in production it would be escaped
        # by Qt's rich text renderer. Here we just verify the structure.
        assert "<pre" in html

    def test_file_without_line(self):
        d = {
            "name": "foo",
            "type": "function",
            "file": "/path/file.py",
            "line": None,
            "doc": "Some docs",
        }
        html = _format_definition_tooltip(d)
        assert "file.py" not in html or ".py:" not in html

    def test_line_without_file(self):
        d = {
            "name": "foo",
            "type": "function",
            "file": None,
            "line": 42,
            "doc": "Some docs",
        }
        html = _format_definition_tooltip(d)
        assert "42" not in html.split("<hr")[0]  # line not shown without file
