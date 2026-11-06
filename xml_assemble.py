#!/usr/bin/env python3
"""
Assemble a big XML config from a manifest with <file file="..."/> placeholders.

Rules:
  * A placeholder is replaced by the ROOT element of the referenced file.
  * With unwrap="true", it is replaced by the root's CHILDREN instead
    (lets one file contribute several sibling elements).
  * Paths are relative to the file that contains the placeholder.
  * Fragments may contain placeholders themselves (nesting).
  * Circular includes are detected and reported.
  * Errors point at file:line.

Usage:
  python xml_assemble.py config/manifest.xml                 # print result
  python xml_assemble.py config/manifest.xml -o out.xml      # write result
  python xml_assemble.py config/manifest.xml --annotate      # add src="file:line"
"""
import argparse
import os
import sys
from lxml import etree

PLACEHOLDER_TAG = "file"      # name of the placeholder element
PATH_ATTR = "file"            # attribute holding the path
UNWRAP_ATTR = "unwrap"        # optional: unwrap="true"


class AssembleError(Exception):
    pass


def _loc(path, elem):
    return f"{path}:{elem.sourceline}"


def _parse(path, include_site=None):
    try:
        parser = etree.XMLParser(remove_comments=True)
        return etree.parse(path, parser).getroot()
    except OSError:
        where = f" (included from {include_site})" if include_site else ""
        raise AssembleError(f"Cannot read file '{path}'{where}")
    except etree.XMLSyntaxError as e:
        raise AssembleError(f"XML syntax error in {path}: {e}")


def _annotate(elem, path):
    """Record where each element came from (only elements not yet tagged)."""
    for el in elem.iter():
        if isinstance(el.tag, str) and "src" not in el.attrib:
            el.set("src", f"{os.path.basename(path)}:{el.sourceline}")


def _expand(root, path, stack, annotate):
    """Replace every placeholder under `root` (which was loaded from `path`)."""
    # Collect first: we mutate the tree while replacing.
    placeholders = [e for e in root.iter(PLACEHOLDER_TAG) if e is not root]

    for ph in placeholders:
        site = _loc(path, ph)
        rel = ph.get(PATH_ATTR)
        if not rel:
            raise AssembleError(f"{site}: <{PLACEHOLDER_TAG}> is missing '{PATH_ATTR}' attribute")

        target = os.path.normpath(os.path.join(os.path.dirname(path), rel))

        if target in stack:
            chain = " -> ".join(stack + [target])
            raise AssembleError(f"{site}: circular include: {chain}")

        frag = _parse(target, include_site=site)
        if annotate:
            _annotate(frag, target)
        _expand(frag, target, stack + [target], annotate)  # nested placeholders

        replacement = list(frag) if ph.get(UNWRAP_ATTR) == "true" else [frag]
        _replace(ph, replacement)

    return root


def _replace(old, new_nodes):
    """Swap `old` for `new_nodes` in its parent, preserving following text."""
    parent = old.getparent()
    if parent is None:
        raise AssembleError("The manifest root itself cannot be a placeholder")
    idx = parent.index(old)
    tail = old.tail
    parent.remove(old)
    for offset, node in enumerate(new_nodes):
        parent.insert(idx + offset, node)
    if new_nodes:
        new_nodes[-1].tail = tail
    elif tail and tail.strip():
        # keep stray text if the placeholder was replaced by nothing
        prev = parent[idx - 1] if idx > 0 else None
        if prev is not None:
            prev.tail = (prev.tail or "") + tail
        else:
            parent.text = (parent.text or "") + tail


def assemble(manifest_path, annotate=False):
    manifest_path = os.path.normpath(manifest_path)
    root = _parse(manifest_path)
    if annotate:
        _annotate(root, manifest_path)
    _expand(root, manifest_path, [manifest_path], annotate)
    return root


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("manifest")
    ap.add_argument("-o", "--output", help="write result here instead of stdout")
    ap.add_argument("--annotate", action="store_true",
                    help='add src="file:line" to every element (debugging)')
    args = ap.parse_args()

    try:
        root = assemble(args.manifest, annotate=args.annotate)
    except AssembleError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    etree.indent(root, space="    ")
    data = etree.tostring(root, encoding="unicode")
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(data + "\n")
    else:
        print(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
