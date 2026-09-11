# canitrunlocal-ds

A structured, validated dataset of GPU hardware specs — memory
size/bandwidth, architecture — for projects that need to look up known
hardware rather than trust free-text user input.

This is the data source behind [CanItRunLocal](https://canitrunlocal.com)'s
hardware catalog: its `sync-hardware-specs` job pulls `gpus/*.json` from
this repo's `main` branch on a schedule and upserts the entries into
`GpuSpec`, which is what lets CanItRunLocal match a user's GPU or Apple
chip to a known VRAM/bandwidth spec instead of trusting free-text input.
Adding or correcting an entry here (see [Contributing](#contributing))
is the way to fix or expand what CanItRunLocal — or any other consumer —
knows about a piece of hardware; it is not tied to CanItRunLocal's own
codebase or release process.

**Status:** schema and validation pipeline only. No real hardware data
has been populated yet beyond a few illustrative examples proving the
pipeline works — see [Contributing](#contributing) if you want to help
change that.

## Schema

Each record lives in `gpus/<vendor>.json` as a JSON array, validated
against `schema/gpu.schema.json` — that schema file is the source of
truth for field names, types, and constraints; this README doesn't
duplicate it.

A few notes that aren't obvious from the schema alone:

- `id` is a stable slug (`<manufacturer-slug>-<model-slug>`) that, once
  assigned, is never renamed — `name` can be corrected freely, `id`
  cannot, since consumers may key off it.
- Every entry's `manufacturer` must match the vendor file it lives in
  (`gpus/nvidia.json` entries must all be `"manufacturer": "NVIDIA"`).
- Apple Silicon SoCs are modeled as GPUs, one entry per chip *and*
  unified-memory configuration it actually ships in (e.g. an M4 Pro
  ships in 24GB and 48GB configs, so it gets two `gpus/apple.json`
  entries — `apple-m4-pro-24gb` and `apple-m4-pro-48gb`) — unified
  memory is the same kind of fact as a GPU's VRAM (a named compute
  unit with a fixed amount of fast memory), it's just shared with the
  CPU instead of dedicated. `vramGb` is that configuration's unified
  memory size, and `memoryBandwidthGbps` covers both CPU and GPU
  traffic since they share the one pool.

## Contributing

1. Add your entry to the right `gpus/<vendor>.json` file.
2. Run the validator locally before opening a PR:
   ```sh
   pip install -r requirements.txt
   python3 scripts/validate.py
   pytest tests/
   ```
3. Open a PR. CI runs the same checks.

The validator checks schema conformance, that your entry's
`manufacturer` matches its file, and that you haven't introduced a
duplicate `id` or an exact duplicate `(manufacturer, name)` pair.

## License

Code, schemas, and scripts in this repo are MIT-licensed (see
`LICENSE`). No third-party data has been incorporated yet; a future
data-population effort sourcing from a share-alike-licensed dataset
(e.g. Wikipedia, CC-BY-SA 4.0) will need to document that data's
license separately when it lands, since MIT alone wouldn't cover it.
