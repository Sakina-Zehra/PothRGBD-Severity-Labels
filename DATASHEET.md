# Datasheet: PothRGBD Severity Labels

Following the spirit of Gebru et al., *Datasheets for Datasets*.

## Motivation

This dataset adds human severity annotations to the public PothRGBD dataset to support research on pothole **severity ranking** and **repair prioritization**. It extends the original dataset, which supports pothole detection and segmentation, with human judgments of pothole severity.

## Composition

- **1,000 images**, corresponding to the images in PothRGBD: paired RGB and depth images captured using an Intel RealSense D415 at 640 × 480 resolution.
- Each image was independently scored by **four labellers**.
- Each labeller provided a severity score (`1`, `2`, `3`, or `X`) and a confidence score (`1`–`3`).
- A merged target (`target_cont` and `target_class`) is also provided. See **Label merging** below.
- The raw annotations are provided separately in `raw_labels/`.

## Collection process

Labelling was conducted using a custom tool (`code/labelling.py`). The tool generates a combined RGB and colour-mapped depth panel for each image. The panels include the ground-truth pothole outline, scale bars, and a legend explaining the depth visualization.

Labellers primarily used practical, driver-oriented descriptions to judge severity. These descriptions were intended to make the categories easier for humans to interpret than numerical depth measurements alone. The depth images were provided as supporting visual information to help assess the potholes.

The judging guidance was to consider **depth first, then size relative to the lane, and finally edge sharpness** when visual cues conflicted. Image darkness and shadows were to be ignored where possible because they can mislead the perceived depth.

The labelling script generates the blank annotation sheets for labellers A and B. The four completed annotation sheets are included in the raw labels release.

## Label merging

The raw per-labeller annotations are released as provided in `raw_labels/`. The merge script (`code/merge_labels.py`) produces the merged severity targets as follows:

1. Each labeller's numerical severity scores are rank-normalized against that labeller's own score distribution. This reduces the effect of differences in individual scoring strictness.
2. The normalized ranks are averaged across labellers, weighted by their stated confidence.
3. The resulting `target_cont` is a continuous severity estimate on a 1–3 scale.
4. `target_class` is assigned using thresholds selected so that the proportions of the merged classes match the average class proportions used by the four labellers. It is **not** obtained by simply rounding `target_cont`.
5. Images with a normalized rank spread greater than 0.5 are flagged as `high_disagreement = True`. These images are retained in the merged dataset rather than removed.

An annotation of `X` indicates that the image should be excluded from severity scoring by that labeller. It is treated as a missing severity score during merging and is not treated as a fourth severity category.

The merged CSV also retains the individual labellers' scores, confidence values, and normalized ranks. The suffixes `_1`, `_2`, `_3`, and `_4` identify the order in which the annotation sheets were supplied to the merge script. For example, `score_1` belongs to the first sheet passed on the command line.

## Known limitations — inter-rater reliability

Inter-rater reliability was measured across all six pairs of labellers, using raw (non-merged) severity scores. Each pair was compared across 1,000 images.

| Metric | Average across pairs |
|---|---:|
| Weighted kappa | 0.266 |
| Spearman correlation | 0.331 |

These values indicate limited agreement between labellers rather than high agreement. Severity judgment from a single RGB and depth image can be subjective, particularly when potholes have ambiguous depth, size, or boundaries.

A total of **259 out of 1,000 images (25.9%)** are flagged as `high_disagreement`.

The merged class distribution is:

| Class | Number of images | Proportion |
|---|---:|---:|
| 1 — Low | 575 | 57.5% |
| 2 — Medium | 300 | 30.0% |
| 3 — High | 125 | 12.5% |

The average class proportions across individual labellers were approximately `[0.578, 0.296, 0.125]`.

**Implication for users:** `target_class` and `target_cont` should be understood as consensus estimates, not objective ground truth. Users who require higher agreement may choose to filter for `high_disagreement == False`. The four raw per-labeller annotations should also be considered valuable data in their own right, particularly for research on label uncertainty and multi-annotator learning.

## License and attribution

This dataset extends **PothRGBD** (Yurdakul & Taşdemir, 2025). The original PothRGBD dataset is released under the MIT License, and these severity annotations are also released under the MIT License.

If you use this dataset, please cite both the original PothRGBD paper and this repository. See `CITATION.cff` for the repository citation.

## Maintenance

Maintained by Sakina Zehra and Maria Muhammad Aqeel, Habib University.

Contact: sakina.zehra.1512@gmail.com

Versioned releases are intended to be made available through GitHub and Zenodo. See `README.md` for usage instructions.