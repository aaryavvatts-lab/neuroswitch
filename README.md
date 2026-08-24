# neuroswitch

When long-term nerve damage takes your right hand out of action, you end up doing
everything with the left. Does the brain's wiring change to match?

This is a student reanalysis of
[OpenNeuro ds008162](https://doi.org/10.18112/openneuro.ds008162.v1.0.3), a public
CC0 dataset of 71 adults tracing shapes inside a 3T scanner with each hand. 25 of
them had long-term peripheral nerve injury to the right hand.

The site is the output. It reports the graph neural network the idea calls for, the
simpler models that might beat it, and the control tests that decide whether any of
it means anything.

## What is in here

Raw scans go in. Signals from 241 brain regions come out, get turned into a network
per person, and go to a set of classifiers. Then four control tests:

1. **Left minus right.** Everyone drew with both hands, so each person's right-hand
   network is subtracted from their own left-hand network. Anything fixed about that
   person cancels out.
2. **Drawing quality.** Patients draw worse and the dataset measures it. A brain
   model can score well by picking up effort instead of rewiring, so drawing quality
   is tested on its own, taken out of the brain features, and matched on.
3. **Severity.** Inside the patient group only, does the pattern track how much
   trouble the hand gives them, how long ago the injury was, or whether their hand
   preference has actually shifted?
4. **Rest versus task.** If the same model works on scans where people lie still,
   the difference is something they carry around, not something drawing brings out.

## Things worth knowing about the build

- **No fMRIPrep, FSL, FreeSurfer, AFNI or Docker.** Preprocessing runs on ANTs
  through `antspyx`, plus numpy, nibabel and nilearn.
- **The region map moves into the data, not the other way round.** Pushing 488
  images per run into template space is the slow part of a normal pipeline. Instead
  the atlas is warped into each run's own space. Confound removal and filtering work
  along time, region averaging works across space, so doing them in either order
  gives the same answer. Cleaning 241 signals is exact and much cheaper than
  cleaning 150,000 voxels.
- **It runs on a full disk.** Someone's raw scans are deleted only after their
  signals pass a check, so free space goes up as the analysis runs. Before deleting
  anything the code confirms the same file can still be downloaded from OpenNeuro at
  the same byte size.
- **Leak control.** The stored files hold time signals rather than finished
  connectivity matrices, which forces anything that learns a group average to be
  fitted inside the training split. Splits are grouped by person. One test checks
  that shuffled labels score near 0.50, which is what catches a leak.

## Run it

```bash
uv sync
uv run python -m neuroswitch.atlas 200
uv run python -m neuroswitch.acquire --top-level
./drive.sh 1 3 subjects.txt drawLH,drawRH
uv run python -m neuroswitch.run_analysis --stages cohort,main,controls
uv run python -m neuroswitch.run_importance --condition LH
uv run python -m neuroswitch.site_build
uv run pytest
```

Lining up head movement is the slow step at about two minutes a run, and it already
uses every core, so running several people at once does not speed anything up.
Budget roughly twenty minutes a person.

## Tests

`uv run pytest` covers slice timing against a known shift, head movement against a
hand-worked example, region averaging on a made-up brain, a full dry run of the
model chain on data where the answer is known, and a style check on the built pages.

## Credit

The data was collected by Kapil, Kim, McAvoy and Philip at Washington University in
St. Louis, paid for by NINDS grant R01 NS114046, and released under CC0. This
repository is a student reanalysis. It is not connected to that group and they have
not reviewed it.

Not a clinical study. Nothing here diagnoses anything.

Code is MIT licensed. See LICENSE.
