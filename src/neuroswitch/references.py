"""Papers cited on the site.

Every entry was looked up in the live literature index and carries a real DOI.
Nothing here is written from memory.
"""
from __future__ import annotations

REFERENCES = [
    {
        "key": "dataset",
        "authors": "Kapil N, Kim T, McAvoy MP, Philip BA",
        "year": 2026,
        "title": ("Precision drawing during task fMRI in healthy adults and "
                  "individuals with peripheral nerve injury"),
        "venue": "OpenNeuro (dataset)",
        "doi": "10.18112/openneuro.ds008162.v1.0.3",
        "url": "https://doi.org/10.18112/openneuro.ds008162.v1.0.3",
        "note": "The scans used here. Released under CC0.",
    },
    {
        "key": "preprint",
        "authors": "Philip BA and colleagues",
        "year": 2025,
        "title": "Study accompanying the drawing fMRI dataset",
        "venue": "bioRxiv preprint",
        "doi": "10.1101/2025.11.18.689091",
        "url": "https://doi.org/10.1101/2025.11.18.689091",
        "note": "Listed by the dataset authors as the related publication.",
    },
    {
        "key": "makin2015",
        "authors": "Makin TR, Scholz J, Slater D, Johansen-Berg H, Tracey I",
        "year": 2015,
        "title": ("Reassessing cortical reorganization in the primary sensorimotor "
                  "cortex following arm amputation"),
        "venue": "Brain 138(8):2140",
        "doi": "10.1093/brain/awv161",
        "url": "https://doi.org/10.1093/brain/awv161",
        "note": ("Found that the link between cortical remapping and phantom pain did "
                 "not hold up once other factors were measured. A direct warning that "
                 "remapping results need hard controls."),
    },
    {
        "key": "marek2022",
        "authors": "Marek S, Tervo-Clemmens B, Calabro FJ, and 42 others",
        "year": 2022,
        "title": "Reproducible brain-wide association studies require thousands of individuals",
        "venue": "Nature",
        "doi": "10.1038/s41586-022-04492-9",
        "url": "https://doi.org/10.1038/s41586-022-04492-9",
        "note": ("Brain to behaviour effects are smaller than people assumed, and small "
                 "samples give inflated results that do not replicate. The main reason "
                 "this project reports permutation tests and does not lead with accuracy."),
    },
    {
        "key": "turner2018",
        "authors": "Turner BO, Paul EJ, Miller MB, Barbey AK",
        "year": 2018,
        "title": "Small sample sizes reduce the replicability of task-based fMRI studies",
        "venue": "Communications Biology",
        "doi": "10.1038/s42003-018-0073-z",
        "url": "https://doi.org/10.1038/s42003-018-0073-z",
        "note": "Same problem, measured for task fMRI rather than resting state.",
    },
    {
        "key": "parkes2018",
        "authors": "Parkes L, Fulcher B, Yücel M, Fornito A",
        "year": 2018,
        "title": ("An evaluation of the efficacy, reliability, and sensitivity of motion "
                  "correction strategies for resting-state functional MRI"),
        "venue": "NeuroImage",
        "doi": "10.1016/j.neuroimage.2017.12.073",
        "url": "https://doi.org/10.1016/j.neuroimage.2017.12.073",
        "note": ("Compared 19 denoising pipelines. Showed that group differences in "
                 "connectivity depend heavily on how motion is handled, which is why "
                 "the motion-only model is reported here."),
    },
    {
        "key": "eklund2016",
        "authors": "Eklund A, Nichols TE, Knutsson H",
        "year": 2016,
        "title": "Cluster failure: why fMRI inferences for spatial extent have inflated false-positive rates",
        "venue": "PNAS",
        "doi": "10.1073/pnas.1602413113",
        "url": "https://doi.org/10.1073/pnas.1602413113",
        "note": "Showed permutation tests behave correctly where parametric ones did not.",
    },
    {
        "key": "cui2022",
        "authors": "Cui H, Dai W, Zhu Y, and 7 others",
        "year": 2022,
        "title": "BrainGB: a benchmark for brain network analysis with graph neural networks",
        "venue": "IEEE Transactions on Medical Imaging",
        "doi": "10.1109/tmi.2022.3218745",
        "url": "https://doi.org/10.1109/tmi.2022.3218745",
        "note": "Benchmark for graph networks on brain data, and the source of the model design choices used here.",
    },
    {
        "key": "schaefer2018",
        "authors": "Schaefer A, Kong R, Gordon EM, and 5 others",
        "year": 2018,
        "title": ("Local-global parcellation of the human cerebral cortex from intrinsic "
                  "functional connectivity MRI"),
        "venue": "Cerebral Cortex 28(9):3095",
        "doi": "10.1093/cercor/bhx179",
        "url": "https://doi.org/10.1093/cercor/bhx179",
        "note": "The 200 cortical regions used as graph nodes.",
    },
    {
        "key": "aal2002",
        "authors": "Tzourio-Mazoyer N, Landeau B, Papathanassiou D, and 5 others",
        "year": 2002,
        "title": ("Automated anatomical labeling of activations in SPM using a macroscopic "
                  "anatomical parcellation of the MNI MRI single-subject brain"),
        "venue": "NeuroImage",
        "doi": "10.1006/nimg.2001.0978",
        "url": "https://doi.org/10.1006/nimg.2001.0978",
        "note": "Source of the 26 cerebellar regions added to the graph.",
    },
    {
        "key": "elbert2004",
        "authors": "Elbert T, Rockstroh B",
        "year": 2004,
        "title": "Reorganization of human cerebral cortex: the range of changes following use and injury",
        "venue": "The Neuroscientist",
        "doi": "10.1177/1073858403262111",
        "url": "https://doi.org/10.1177/1073858403262111",
        "note": "Review of how use and injury change cortical maps.",
    },
    {
        "key": "chen2021",
        "authors": "Chen YH, Siow TY, Wang JY, and 2 others",
        "year": 2021,
        "title": ("Greater cortical activation and motor recovery following mirror therapy "
                  "immediately after peripheral nerve repair of the forearm"),
        "venue": "Neuroscience",
        "doi": "10.1016/j.neuroscience.2021.11.048",
        "url": "https://doi.org/10.1016/j.neuroscience.2021.11.048",
        "note": "One of the few fMRI studies of peripheral nerve injury in the hand and forearm.",
    },
    {
        "key": "freund2011",
        "authors": "Freund P, Weiskopf N, Ward NS, and 6 others",
        "year": 2011,
        "title": "Disability, atrophy and cortical reorganization following spinal cord injury",
        "venue": "Brain 134(6):1610",
        "doi": "10.1093/brain/awr093",
        "url": "https://doi.org/10.1093/brain/awr093",
        "note": ("Linked the amount of remapping to how disabled someone was. The model "
                 "for the severity analysis used here."),
    },
]

BY_KEY = {r["key"]: r for r in REFERENCES}


def cite(key: str) -> str:
    """Short inline citation with a link."""
    r = BY_KEY[key]
    first = r["authors"].split(",")[0].split()[0]
    tail = "" if r["authors"].count(",") == 0 else " and others"
    return f'<a href="{r["url"]}">{first}{tail}, {r["year"]}</a>'
