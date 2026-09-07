# Screen recording script

The brief judges the pipeline and the recording, not a website. The recording
must be unedited and must make hardcoding impossible to suspect. That means the
input photo is chosen **on camera**, and two different subjects are run.

Target length: 4-6 minutes. Rehearse once, then record.

---

## Before you press record

1. Close everything except **Chrome** and **PowerShell**.
2. PowerShell: make it big, and start in the project folder.

   ```powershell
   cd C:\Users\manas\Desktop\goa
   cls
   ```
3. Make a folder for the photos you will grab live:

   ```powershell
   mkdir data\demo
   ```
4. Delete any earlier demo records so nothing looks pre-baked:

   ```powershell
   Remove-Item out\records\* -ErrorAction SilentlyContinue
   ```
5. Check the wallet still has ETH:

   ```powershell
   .\.venv\Scripts\python.exe -c "import sys; sys.path.insert(0,'.'); from facepipe import chain; w3=chain.get_w3(); a=chain.get_account(); print(w3.from_wei(w3.eth.get_balance(a.address),'ether'), 'ETH')"
   ```

**Do not** open the photos in advance. Choosing them on camera is the point.

Start recording: `Windows + Shift + S`, click the video camera icon, drag around
the whole screen, click Start.

---

## Take 1 - MrBeast

**Say:** "This pipeline takes a photo of a face, finds a real matching social
media post through reverse-image search, verifies the match against the original
face, and writes it to a blockchain. Nothing is hardcoded, so I'll pick the photo
right now."

1. **Chrome** - go to Google Images, search **MrBeast**.
2. Pick any clear photo of his face. Right-click, **Save image as...**, save into
   `C:\Users\manas\Desktop\goa\data\demo`, name it `mrbeast.jpg`.

   **Say:** "That photo has never been used by this code before."

3. **PowerShell**:

   ```powershell
   .\.venv\Scripts\python.exe run.py data\demo\mrbeast.jpg --fresh
   ```

4. While it runs, narrate the stages as they print:

   - **Stage 1** - "It detected the face and encoded it as a 512-dimension
     vector."
   - **Stage 2** - "Uploaded so the search engine can fetch it."
   - **Stage 3** - "This is a live Google Lens reverse-image search. Those domain
     counts are real results coming back right now."
   - **Stage 4** - "Filtered to social media domains only."
   - **Stage 5** - "This is the important part. For each result it downloads the
     thumbnail, detects the face in *that* image, and compares it to the original
     face. The scores you see are cosine similarity."
   - Point at a **reject** line: "That one is below threshold, so it's discarded.
     The face encoding is doing real filtering, not decoration."
   - **Stage 7** - "Writing the best match to Base Sepolia."
   - **Stage 8** - "Now it re-hashes the local record and asks the chain whether
     it matches."

5. When it prints `verified: YES`, **copy the Basescan tx link** from the output.

6. **Chrome** - paste the link. Show the transaction page.

   **Say:** "This is on a public block explorer. The timestamp is from a minute
   ago. Click Logs and you can read the decoded event."

7. Click the **Logs** tab. Point out `sourceUrl`, `similarityBps`, `thresholdBps`.

   **Say:** "It records the similarity *and* the threshold it was judged against,
   so a reader can see the standard, not just the verdict."

8. Open the matched social media post URL in a new tab. Show it is a real post of
   the same person.

---

## Take 2 - Drake, immediately after

**Say:** "Same pipeline, different person, no changes to the code."

1. Google Images, search **Drake**. Save a photo as
   `data\demo\drake.jpg`.
2. ```powershell
   .\.venv\Scripts\python.exe run.py data\demo\drake.jpg --fresh
   ```
3. Let it run to `verified: YES`. Open the new Basescan link.

   **Say:** "Different input, different match, different transaction. Nothing
   about this is pre-recorded."

---

## Take 3 - the tamper check (30 seconds, this is the closer)

**Say:** "The record is only tamper-evident if tampering is detectable. Let me
break one."

1. Open the record in Notepad:

   ```powershell
   notepad out\records\drake.json
   ```
2. On camera, change the `"similarity"` value - e.g. `0.988` to `0.999`. Save.
   Close Notepad.
3. ```powershell
   .\.venv\Scripts\python.exe run.py --verify out\records\drake.json
   ```
4. It prints `NOT FOUND on-chain`.

   **Say:** "One field changed, the hash no longer matches what was anchored, and
   verification fails. That is what makes the record tamper-evident."

---

## Close

**Say:** "Known limitations are in the README - it only finds people the web has
indexed, Google's ranking isn't reproducible between runs, and it can produce
false positives. In one of my test runs an unrelated LinkedIn profile scored
0.888 against a cricketer's photo. That's why nothing here should act on a match
without a human reviewing it."

Stop recording. Save the file.

---

## If something goes wrong mid-take

- **`no verified match`** - that is the pipeline working correctly. Say so, then
  run the other subject. Do not hide it.
- **SerpAPI error** - check credits with `python scripts/day1_keys.py`.
- **Chain write fails** - the wallet is out of ETH. Re-run the faucet.
- **Anything else** - stop, fix, start a fresh take. Do not edit the video.
