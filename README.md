# XML Config Assembler

Split a big XML configuration into small files and assemble them from a manifest.

A manifest is a skeleton of the final document. Wherever it contains a
`<file file="..."/>` placeholder, the referenced file is plugged in.

## Quick start

```bash
pip install lxml

python xml_assemble.py examples/full/manifest.xml               # print result
python xml_assemble.py examples/full/manifest.xml -o out.xml    # write to file
python xml_assemble.py examples/full/manifest.xml --annotate    # add src="file:line"
```

## How it works

Manifest:

```xml
<root>
    <file file="network/primary.xml"/>
    <services>
        <file file="services/database.xml"/>
    </services>
</root>
```

Each placeholder is replaced by the **root element** of the file it points to.
Fragments can contain placeholders too, so you can nest as deep as you like.

### Rules

| Rule | Behavior |
|------|----------|
| Replacement | The placeholder is replaced by the referenced file's root element |
| `unwrap="true"` | The root is dropped and its **children** are inserted instead, so one file can supply several siblings |
| Paths | Relative to the file that contains the placeholder, not to the manifest |
| Nesting | Fragments may include other fragments |
| Reuse | The same file can be included from multiple places |
| Cycles | Detected and reported with the full include chain |
| Errors | Reported with `file:line` of the offending placeholder |

### `unwrap` example

`listeners.xml`:

```xml
<listeners>
    <listener name="public"/>
    <listener name="internal"/>
</listeners>
```

```xml
<network>
    <file file="listeners.xml" unwrap="true"/>
</network>
```

Result (the `<listeners>` wrapper is gone):

```xml
<network>
    <listener name="public"/>
    <listener name="internal"/>
</network>
```

## Project layout

```
xml_assemble.py        the assembler
config/                small example (start here)
  manifest.xml
  broken/              error-case demos (cycle, missing file)
examples/full/         larger realistic example
  manifest.xml
  network/ security/ services/ features/ logging/ shared/
```

## Try the error cases

```bash
python xml_assemble.py config/broken/cycle_manifest.xml
python xml_assemble.py config/broken/missing_manifest.xml
```

## Configuration

Constants at the top of `xml_assemble.py`:

- `PLACEHOLDER_TAG` is the placeholder element name (default `file`)
- `PATH_ATTR` is the attribute holding the path (default `file`)
- `UNWRAP_ATTR` is the unwrap attribute name (default `unwrap`)

If a real config element could be named `file`, rename the placeholder
(e.g. `include`) or use an XML namespace.

## Notes

- Comments in fragments are stripped. Set `remove_comments=False` in `_parse` to keep them.
- Validation is not included. To add it, call `schema.assertValid(root)` on the
  result of `assemble()`, using your XSD.
- `--annotate` changes the output document. Use it for debugging only.
