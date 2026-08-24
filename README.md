# neuroswitch

Do brain networks reorganise when chronic nerve injury forces someone to use
their non-dominant hand? An independent reanalysis of
[OpenNeuro ds008162](https://doi.org/10.18112/openneuro.ds008162.v1.0.3) (CC0) —
71 adults drawing precision shapes in a 3T scanner with each hand, 25 of them
with chronic peripheral nerve injury to the right hand.

**The site is the deliverable.** It reports the graph neural network the premise
calls for, the simpler models that might beat it, and — the part that decides
whether any of it means anything — the control analyses.

## What is here

Raw scans → BOLD signals in 241 brain regions → connectivity graphs → classifiers →
region importances, plus four controls:

1. **Hand-difference graphs.** Everyone drew with both hands, so each person's
   right-hand network is subtracted from their own left-hand network. Every fixed
   subject-level confound cancels.
2. **Drawing performance.** Patients draw much worse, and the dataset measures it.
   A brain model can score well by detecting difficulty instead of reorganisation,
   so performance is tested alone, regressed out, and matched on.
3. **Severity.** Within patients only, does the signature scale with disability,
   time since injury, or a real shift in hand preference?
4. **Rest versus task.** If the classifier also works at rest, it is a trait, not
   task-driven recruitment.

## Notable implementation details

- **No fMRIPrep, FSL, FreeSurfer, AFNI or Docker.** Preprocessing is built directly
  on ANTs via `antspyx`, plus numpy/nibabel/nilearn.
- **The atlas is warped into each run's native space** rather than resampling
  488-volume 4-D series into template space. Confound regression and filtering are
  linear along time, parcel averaging is linear across space, so they commute —
  cleaning 241 signals is exact, not an approximation, and far cheaper.
- **Runs on a nearly-full disk.** Each person's raw scans are deleted only after
  their extracted signals pass verification, so free space grows as the analysis
  runs. Every deleted file is logged with the public URL it came from.
- **Leakage control.** The feature store keeps time series, not connectivity
  matrices, which forces group-level estimators (tangent embedding, scalers) to be
  fit inside training folds. Splits are grouped by person.

## Run it

```bash
uv sync
uv run python -m neuroswitch.atlas 200
uv run python -m neuroswitch.acquire --top-level
./drive.sh 1 3 subjects.txt drawLH,drawRH
uv run python -m neuroswitch.run_analysis --stages cohort,main,controls
uv run python -m neuroswitch.site_build
uv run pytest
```

Motion correction dominates the runtime (~2 min/run) and already uses every core,
so running subjects in parallel does not increase throughput. Budget ~20 min per person.

## Credit

The data were collected by Kapil, Kim, McAvoy and Philip at Washington University in
St. Louis, funded by NINDS R01 NS114046, and released under CC0. This repository is an
independent reanalysis and is not affiliated with or endorsed by them.

Not a clinical study. No diagnostic claims.
