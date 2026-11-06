#!/usr/bin/env python3
"""Build Neurobagel CLI inputs from an fMRIPrep derivatives folder.

Writes two TSVs:
  1. A BIDS metadata table (sub, ses, suffix, path) for `bagel bids`,
     using fMRIPrep's preprocessed images as evidence of which
     modalities each subject/session has.
  2. A Nipoppy-style processing status file for `bagel derivatives`,
     marking fMRIPrep as SUCCESS when the subject's HTML report exists.

Standard library only, so it runs with any python3 on Sockeye.

Usage:
  python3 fmriprep2bagel.py /path/to/derivatives/fmriprep \
      --bids-table MyDataset_bids.tsv \
      --proc-status MyDataset_proc_status.tsv
"""

import argparse
import csv
import json
import re
from pathlib import Path

# BIDS suffixes fMRIPrep produces that map to Neurobagel imaging modalities
KEEP_SUFFIXES = {"T1w", "T2w", "FLAIR", "bold"}
NIFTI = (".nii.gz", ".nii")


def entities(name):
    """Parse BIDS entities and suffix from a filename."""
    stem = name
    for ext in NIFTI:
        if stem.endswith(ext):
            stem = stem[: -len(ext)]
            break
    parts = stem.split("_")
    ents = dict(p.split("-", 1) for p in parts[:-1] if "-" in p)
    return ents, parts[-1]


def pipeline_version(fmriprep_dir):
    desc = fmriprep_dir / "dataset_description.json"
    try:
        data = json.loads(desc.read_text())
        for gen in data.get("GeneratedBy", []):
            if gen.get("Name", "").lower() == "fmriprep":
                return gen.get("Version", "")
        return data.get("PipelineDescription", {}).get("Version", "")
    except (OSError, json.JSONDecodeError):
        return ""


def build_bids_table(fmriprep_dir):
    rows, seen = [], set()
    for sub_dir in sorted(fmriprep_dir.glob("sub-*")):
        if not sub_dir.is_dir():
            continue
        for f in sorted(sub_dir.rglob("*_desc-preproc_*")):
            if not f.name.endswith(NIFTI):
                continue
            ents, suffix = entities(f.name)
            if suffix not in KEEP_SUFFIXES:
                continue
            # one row per source acquisition, not per output space/resolution
            key_name = re.sub(r"_(space|res|den|cohort)-[^_]+", "", f.name)
            if key_name in seen:
                continue
            seen.add(key_name)
            rows.append({
                "sub": f"sub-{ents['sub']}",
                "ses": f"ses-{ents['ses']}" if "ses" in ents else "",
                "suffix": suffix,
                "path": str(f.resolve()),
            })
    return rows


def build_proc_status(fmriprep_dir, version):
    rows = []
    for sub_dir in sorted(fmriprep_dir.glob("sub-*")):
        if not sub_dir.is_dir():
            continue
        sub = sub_dir.name
        report_ok = (fmriprep_dir / f"{sub}.html").exists()
        status = "SUCCESS" if report_ok else "FAIL"
        sessions = sorted(d.name for d in sub_dir.glob("ses-*") if d.is_dir())
        for ses in sessions or [""]:
            rows.append({
                "participant_id": sub.removeprefix("sub-"),
                "bids_participant_id": sub,
                "session_id": ses.removeprefix("ses-"),
                "bids_session_id": ses,
                "pipeline_name": "fmriprep",
                "pipeline_version": version,
                "pipeline_step": "default",
                "status": status,
            })
    return rows


def write_tsv(path, rows, fields):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, delimiter="\t")
        w.writeheader()
        w.writerows(rows)


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("fmriprep_dir", type=Path)
    p.add_argument("--bids-table", type=Path, default=Path("bids_table.tsv"))
    p.add_argument("--proc-status", type=Path, default=Path("proc_status.tsv"))
    p.add_argument("--version", default=None,
                   help="fMRIPrep version (default: read from dataset_description.json)")
    args = p.parse_args()

    d = args.fmriprep_dir.resolve()
    version = args.version or pipeline_version(d)
    if not version:
        raise SystemExit("Could not read fMRIPrep version; pass --version")

    bids_rows = build_bids_table(d)
    write_tsv(args.bids_table, bids_rows, ["sub", "ses", "suffix", "path"])

    proc_rows = build_proc_status(d, version)
    write_tsv(args.proc_status, proc_rows, [
        "participant_id", "bids_participant_id", "session_id", "bids_session_id",
        "pipeline_name", "pipeline_version", "pipeline_step", "status"])

    n_sub = len({r["sub"] for r in bids_rows})
    n_ok = sum(r["status"] == "SUCCESS" for r in proc_rows)
    print(f"fMRIPrep {version}")
    print(f"BIDS table:  {len(bids_rows)} images, {n_sub} subjects -> {args.bids_table}")
    print(f"Proc status: {n_ok}/{len(proc_rows)} subject-sessions SUCCESS -> {args.proc_status}")


if __name__ == "__main__":
    main()