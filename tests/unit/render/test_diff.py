"""Tests for render.diff."""

from cc.render.color import C
from cc.render.diff import render_diff


def test_render_diff_empty():
    assert render_diff("") == []
    assert render_diff("   ") == []


def test_render_diff_headers():
    diff = "--- a/test.py\n+++ b/test.py"
    lines = render_diff(diff)
    assert len(lines) == 2
    assert C.GRAY in lines[0]
    assert C.GRAY in lines[1]


def test_render_diff_hunk():
    diff = "@@ -1,3 +1,3 @@"
    lines = render_diff(diff)
    assert len(lines) == 1
    assert C.CYAN in lines[0]


def test_render_diff_additions():
    diff = "+new line"
    lines = render_diff(diff)
    assert C.GREEN in lines[0]


def test_render_diff_deletions():
    diff = "-old line"
    lines = render_diff(diff)
    assert C.RED in lines[0]


def test_render_diff_context():
    diff = " context line"
    lines = render_diff(diff)
    assert lines[0] == " context line"


def test_render_diff_complete():
    diff = """--- a/test.py
+++ b/test.py
@@ -1,2 +1,2 @@
-old
+new
 context"""
    lines = render_diff(diff)
    assert len(lines) == 6
    assert C.GRAY in lines[0]
    assert C.GRAY in lines[1]
    assert C.CYAN in lines[2]
    assert C.RED in lines[3]
    assert C.GREEN in lines[4]
    assert lines[5] == " context"
