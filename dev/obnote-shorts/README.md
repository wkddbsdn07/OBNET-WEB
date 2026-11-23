# OBNOTE Shorts — VPS development snapshot

This is an **offline prototype**, not the production renderer or an upload service. It preserves the Python components developed for the VPS: media-review record validation, fixture job state and locking, local completion and restart inspection, and narration cache keys, lookup, storage, and WAV validation. Media-review records still require a trusted reviewer; validation does not establish a license. The fixture helpers are not a delivery pipeline.

## Local checks

From this directory on Linux, with Python 3.11+:

```sh
python3 -B -m unittest discover -s tests -q
```

Only self-contained tests are included. Tests depending on retained VPS video fixtures or the pinned upstream checkout are not included. These checks do not require provider credentials or network access.

## Not included

No real-product end-to-end render, live TTS integration or quality verification, automatic publication, or remote synchronization. Source and standalone tests only; no generated media, databases, credential files, or internal logs. No changes to the website or workflows.
