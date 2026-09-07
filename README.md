# Face ID + Blockchain Verification

Detects and encodes a face from a photo, finds a real matching social media post
via genuine reverse-image search, verifies the match against the original face,
and anchors the result on a blockchain as a tamper-evident record.

**Contract (Base Sepolia):**
[`0xCb138113998a3001D4b01aFA375514DaAe298323`](https://sepolia.basescan.org/address/0xCb138113998a3001D4b01aFA375514DaAe298323)

---

## What it does

```
photo.jpg
  1. detect + encode the face            MTCNN -> InceptionResnetV1, 512-d vector
  2. host the image publicly             imgbb (Lens needs a fetchable URL)
  3. reverse-image search                Google Lens via SerpAPI - live, every run
  4. filter to social media domains      strict allowlist, no blogs or news
  5. re-encode each result's thumbnail   MTCNN + cosine vs. the query face
  6. accept above the threshold          default 0.60
  7. anchor the best match on-chain      Base Sepolia
  8. re-hash locally and confirm         the tamper check
```

Nothing is hardcoded. Every candidate comes back from a live Lens query and
carries a clickable source URL, and the pipeline exits without writing anything
when no match clears the threshold.

### The face encoding is the filter, not decoration

The obvious way to build this is: encode a face, ignore the vector, and write
whatever the search engine ranked first. That would make the task a reverse
*image* lookup with a face-detection step bolted on for show.

Instead the query embedding is what decides. Each Lens result carries a
thumbnail hosted on Google's CDN; the pipeline downloads it, detects the face in
it, embeds it, and takes the cosine similarity against the query face. Only
results above the threshold are eligible to reach the chain. So the on-chain
claim is one the pipeline actually verified, not one it inherited from Google's
ranking.

Using Google's thumbnails also means the pipeline never touches Instagram's or
Facebook's servers. Those sites serve login walls to scrapers; the thumbnail is
already public and already fetched. See *Limitations* for what this costs.

### What "tamper-evident" means here

Two pieces do the work:

1. The record is serialised to **canonical JSON** — sorted keys, no incidental
   whitespace — and hashed with keccak256. Without canonicalisation, the same
   data re-serialised could hash differently and the integrity check would be
   worthless.
2. **Only the 32-byte hash goes into contract storage.** The readable payload
   rides in the event, which is far cheaper in gas and is what a block explorer
   decodes for a human reader.

`run.py --verify` re-hashes the local record and asserts the chain agrees.
Changing any field — even `similarity` from 0.9796 to 0.99 — makes the hash
diverge and verification fail. That was tested, not assumed.

---

## Running it

Requires **Python 3.11**. On 3.13, `facenet-pytorch`'s `numpy<2` pin forces a
source build of numpy that needs an MSVC toolchain and fails.

```bash
py -3.11 -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env
```

Fill in `.env`:

| key | where | free? |
|---|---|---|
| `SERPAPI_KEY` | https://serpapi.com/manage-api-key | yes, 250 searches/mo |
| `IMGBB_KEY` | https://imgbb.com/settings/api | yes |
| `DEPLOYER_PRIVATE_KEY` | `python scripts/day2_wallet.py` generates one | testnet only |
| `CONTRACT_ADDRESS` | written by `day2_deploy.py`, or reuse the one above | — |

Check everything works before spending credits:

```bash
python scripts/day1_check.py     # env + model weights
python scripts/day1_smoke.py     # face matching, no API keys, no credits
python scripts/day1_keys.py      # both keys, costs zero search credits
```

Deploy your own contract (needs Base Sepolia faucet ETH), or reuse the deployed
one:

```bash
python scripts/day2_deploy.py
```

Then:

```bash
python run.py photo.jpg                    # full pipeline, writes on-chain
python run.py photo.jpg --no-chain         # search + verify only
python run.py --verify out/records/x.json  # check an anchored record
```

Exit codes: `0` verified and anchored, `1` error, `2` no match above threshold.

### Other scripts

| script | what it is for |
|---|---|
| `scripts/day1_calibrate.py` | derive the threshold from labelled photos |
| `scripts/day1_scout.py` | measure which subjects reliably return social hits |
| `scripts/day1_probe.py` | one verbose end-to-end search |

---

## Which blockchain, and why

**Base Sepolia testnet.** ~2s blocks, free faucet ETH, and Basescan renders the
decoded event so anyone can read the record without running any code.

This is a testnet, not mainnet. The record is public and permanent as far as
that chain is concerned, but Base Sepolia carries no economic security and could
in principle be reset by its operators. Mainnet would cost a fraction of a cent
on an L2 and the code is unchanged apart from the RPC and chain id. Stating that
plainly rather than implying more permanence than exists.

### The contract

```solidity
event MatchRecorded(
    bytes32 indexed recordHash,   // keccak256 of the canonical record
    address indexed submitter,
    string  sourceUrl,            // the matched social media post
    string  platform,
    uint16  similarityBps,        // cosine similarity, basis points
    uint16  thresholdBps,         // what it was judged against
    bytes32 queryImageHash,       // sha256 of the input image bytes
    bytes32 faceEmbeddingHash,    // sha256 of the query embedding
    uint64  timestamp
);
```

Recording the *threshold* alongside the score matters: a reader can see what
standard the match was held to, not just that it passed.

Duplicates revert rather than overwrite — the first write is the one that
counts. Similarity is clamped to 0..10000 bps before it goes on-chain, because a
negative cosine means "not this person" and would otherwise underflow into a
large positive score that could never be corrected.

---

## Measured results

**Face matching** (`day1_smoke.py`, public-domain portraits):

| pair | cosine |
|---|---|
| Obama 2006 vs Obama 2012 — same person, 6 years apart | **+0.781** |
| Obama vs Pichai | +0.207 |
| Obama vs Merkel | −0.010 |

**Subject scouting** — six subjects, one live Lens query each:

| subject | visual matches | on social domains | verified | best |
|---|---|---|---|---|
| MrBeast | 59 | 26 | 14 | +0.990 |
| Drake | 59 | 16 | 14 | +0.988 |
| Prajakta Koli | 59 | 26 | 12 | +0.986 |
| Bhuvan Bam | 59 | 29 | 11 | +0.979 |
| CarryMinati | 57 | 33 | 15 | +0.977 |
| Virat Kohli | 59 | 25 | 15 | +0.934 |

Across all six, **0 of 90 thumbnails failed face detection**.

---

## Limitations

Stated as found, including the ones that are unflattering.

**It produces false positives against real people.** In the Virat Kohli run, a
LinkedIn profile belonging to an unrelated private individual scored **+0.888** —
well above threshold — and would have been eligible for the chain. Face
embeddings encode pose, lighting, framing and demographic features, not identity
alone. Any deployment that acts on a match without a human in the loop will
eventually make a confident, permanent, public claim about the wrong person.

**Reverse-image search is not reproducible.** The same image queried twice on the
same day returned 4 verified matches once and 6 the next time, and one candidate
moved from **+0.596 (rejected)** to **+0.615 (accepted)** between runs. Google's
ranking is opaque and changes underneath you, so a given run is not a repeatable
experiment.

**The threshold is a tunable guess, and results sit near it.** 0.60 separates the
populations we measured, but genuine matches have landed at 0.596 and false
positives at 0.888. There is no threshold that eliminates both error types; the
recorded value only documents which tradeoff was chosen.

**It only finds people the open web has indexed.** A private individual returns
nothing. This is a property of the search engine, not of the code — the pipeline
correctly reports no match and writes nothing.

**Verification uses thumbnails, not the post's own image.** Google's thumbnails
are lower resolution than the source, so verification runs on degraded input. In
these runs it never prevented detection, but a small or heavily-cropped face
could fail where the full-size image would have succeeded.

**One search engine.** Google Lens only. Yandex has stronger face matching;
adding it would raise recall and is the obvious next step.

**Testnet.** See above.

**External dependencies.** SerpAPI (250 searches/month free) and imgbb. The
record stores the sha256 of the input image, so the claim stays checkable
against the original file even if imgbb drops it — but the hosted URL itself
will rot.

---

## Scope of use

This finds people's social media accounts from their face. It was built to a
task specification and is demonstrated on public figures with large indexed
followings.

Reasonable use: your own face, a consenting subject, or a public figure.
Not reasonable: identifying strangers, bulk enumeration, or any use where a
false positive of the kind documented above would harm someone. Records written
here are public and permanent — an incorrect match cannot be taken back.

---

## Layout

```
run.py                    the pipeline, one command
contracts/
  FaceMatchRegistry.sol   the on-chain record
facepipe/
  faces.py                detection, embedding, cosine, hashing
  imghost.py              imgbb upload + sha256 of local bytes
  lens.py                 SerpAPI Lens, social filter, response cache
  probe.py                stages 1-6
  chain.py                compile, deploy, anchor, verify
scripts/
  day1_*.py               environment, keys, calibration, scouting
  day2_*.py               wallet, deploy
```

Lens responses are cached under `out/lens_cache/` so re-running a script does
not silently consume search credits. The demo path passes `--fresh`.
