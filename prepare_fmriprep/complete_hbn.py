#!/usr/bin/env python3
"""Fill in the fMRIPrep-derived participants.tsv with HBN phenotypes (HBN only).

Run this after the generic fmriprep2bagel.py --participants.

The HBN table is a copy of participants.tsv from
https://github.com/ReproBrainChart/HBN_BIDS/. That version uses session_id to
record the site, which is not the case in the fMRIPrep derivatives. So the
subjects and sessions come from the fmriprep2bagel output, the phenotypes come
from the HBN table, and the site stays available in study_site.

Output rows:
  - One per subject/session in the fmriprep2bagel output, so the IDs match the
    tables given to `bagel bids` and `bagel derivatives`.
  - Subjects missing from the HBN table are kept with all phenotypes "n/a".
  - HBN subjects without fMRIPrep outputs are left out.
  - Blank HBN values become "n/a".

Standard library only, so it runs with any python3 on Sockeye.

Usage:
  python3 complete_hbn.py participants.tsv --output participants_hbn.tsv
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

from fmriprep2bagel import write_tsv

DEFAULT_HBN_TABLE = (Path(__file__).resolve().parents[1]
                     / "data" / "hbn" / "study-HBN_desc-participants.tsv")
MISSING = "n/a"


def read_tsv(path):
    with open(path, newline="") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        return list(reader), list(reader.fieldnames or [])


def bids_id(participant_id):
    """HBN IDs have no sub- prefix, fMRIPrep IDs do."""
    return f"sub-{participant_id.removeprefix('sub-')}"


def load_hbn(path):
    rows, fields = read_tsv(path)
    repeated = [k for k, n in Counter(r["participant_id"] for r in rows).items() if n > 1]
    if repeated:
        raise SystemExit(f"Repeated subjects in {path}: {repeated[:5]}")
    pheno_cols = [c for c in fields if c not in ("participant_id", "session_id")]
    return {bids_id(r["participant_id"]): r for r in rows}, pheno_cols


def complete(compiled_rows, has_sessions, hbn, pheno_cols):
    rows = []
    for compiled in compiled_rows:
        source = hbn.get(compiled["participant_id"], {})
        row = {"participant_id": compiled["participant_id"]}
        if has_sessions:
            row["session_id"] = compiled["session_id"]
        for col in pheno_cols:
            row[col] = source.get(col) or MISSING
        rows.append(row)
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("compiled", type=Path,
                   help="participants TSV written by fmriprep2bagel.py --participants")
    p.add_argument("--hbn-table", type=Path, default=DEFAULT_HBN_TABLE,
                   help="HBN participants table (default: %(default)s)")
    p.add_argument("--output", type=Path, default=None,
                   help="Output TSV (default: overwrite the compiled file)")
    args = p.parse_args()

    compiled_rows, compiled_fields = read_tsv(args.compiled)
    has_sessions = "session_id" in compiled_fields
    hbn, pheno_cols = load_hbn(args.hbn_table)

    compiled_subs = {r["participant_id"] for r in compiled_rows}
    matched = compiled_subs & hbn.keys()
    if not matched:
        raise SystemExit(f"No subjects in {args.compiled} are in {args.hbn_table}")

    fields = ["participant_id"] + (["session_id"] if has_sessions else []) + pheno_cols
    rows = complete(compiled_rows, has_sessions, hbn, pheno_cols)
    write_tsv(args.output or args.compiled, rows, fields)

    only_fmriprep = sorted(compiled_subs - hbn.keys())
    n_multi = sum(n > 1 for n in Counter(r["participant_id"] for r in compiled_rows).values())
    print(f"Matched {len(matched)}/{len(compiled_subs)} fMRIPrep subjects to the HBN table")
    print(f"HBN subjects without fMRIPrep outputs (left out): {len(hbn.keys() - compiled_subs)}")
    if only_fmriprep:
        print(f"WARNING: {len(only_fmriprep)} fMRIPrep subjects not in the HBN table "
              f"(phenotypes set to {MISSING}): {', '.join(only_fmriprep[:10])}")
    if n_multi:
        print(f"WARNING: {n_multi} subjects have several sessions; the HBN table has one row "
              "per subject, so each session gets the same values, including age")
    print(f"Wrote {len(rows)} rows -> {args.output or args.compiled}")


if __name__ == "__main__":
    main()
