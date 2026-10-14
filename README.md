# si618-fall2026-project-team8

Research topic: student composition, college density, and nearby used-car markets in the United States.

The current research questions are documented in [research_questions.md](docs/research_questions.md). Downloaded sources are IPEDS 2019 and the winddude automotive dataset. Original downloads, extracted files, and their metadata are under `data/raw/` and excluded from Git.

## Automotive preprocessing and sampling

```powershell
python -m pip install -r requirements.txt
python scripts/sample_automotive.py --sample-size 500000 --seed 6182019
```

See [automotive_sampling.md](docs/automotive_sampling.md) for eligibility filters, deduplication rules, sampling, output files, limitations, and commands for reusing a completed intermediate. The saved script streams the complete JSON, removes unrelated fields, retains eligible US listings posted in 2019, deduplicates them on disk, and creates a reproducible Parquet sample. Original data is never overwritten.

The Parquet sample, IPEDS 2019 data, audit reports, and provisional notebook are included in Git for working on another computer. The original automotive JSON and archives remain local. The large derived SQLite intermediate is distributed through a repository release; its checksum manifest is included in Git.

Run the constructed-input checks with `python -m unittest discover -s tests -v`.

## Earlier prototype scripts

`prepare_ipeds.py` currently supports the previously investigated 2021 IPEDS schema only. `prepare_data.py` expects a canonical college table and the other automotive CSV schema. These prototypes do not yet implement the current IPEDS 2019 / winddude integration. The earlier [data_plan.md](docs/data_plan.md) describes the initial source proposal and is not the current processing contract.

## Submission status

This repository is not yet a completed Milestone 1 submission. IPEDS preparation, university matching, local sample coverage evaluation, and the marimo notebook with descriptive plots and a decision log remain to be completed.

## Continue on another computer

Use Python 3.12 or later:

```powershell
git clone https://github.com/joseph-xuan/si618-fall2026-project-team8.git
cd si618-fall2026-project-team8
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
marimo edit draft/SI618_M1_team8_provisional.py
```

The provisional notebook is preserved as a working draft; it uses an earlier partial sample and should be updated to the completed 500,000-row sample before final analysis. It embeds its inputs and can run without the original automotive JSON.

The completed sample is `data/processed/vehicles_us_2019_sample.parquet`; use `pd.read_parquet(...)` to load it. No large-database restore is needed for normal work with this sample.

To regenerate a larger sample, first restore the intermediate database from the repository release, then reuse it:

```powershell
python scripts/restore_intermediate.py
python scripts/sample_automotive.py --reuse-intermediate --sample-size 1000000 --seed 6182019 --output-dir data/processed/sample_1m --report-dir outputs/sample_1m
```

The restore script verifies each compressed part and the reconstructed database with SHA256. It requires roughly 10 GiB or more of free space. Reusing a completed intermediate works even when the original JSON is absent; its saved source provenance is retained. Full reprocessing from scratch still requires the excluded source JSON.
