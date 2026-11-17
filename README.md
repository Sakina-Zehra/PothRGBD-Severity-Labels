# PothRGBD Severity Labels

Human severity annotations for the PothRGBD dataset, intended to support research on pothole severity ranking and repair prioritization.

This repository contains the completed raw annotations from four labellers, the merged severity labels, the mapping between generated image IDs and original dataset filenames, and scripts for preparing additional annotation sheets and merging labeller scores.

**The raw and merged labels are already included in this repository.** If you want to use the dataset as it is, you do not need to download the original PothRGBD images or run the annotation scripts. You can find the four original annotation sheets in `raw_labels/` and our merged results in `merged/severity_labels.csv`. You can use the raw annotations directly or merge them using your own preferred method. To understand how we produced our merged labels, refer to `merged/severity_labels.csv` and the merging methodology described in `DATASHEET.md`.

The instructions for downloading PothRGBD and running the annotation and merging scripts are provided **only for users who want to extend the existing annotations**, for example, by adding more labellers or experimenting with a different merging approach.

## Repository contents

```text
.
├── code/
│   ├── labelling.py
│   ├── merge_labels.py
│   └── mapping.csv
├── raw_labels/
│   ├── labels_A.xlsx
│   ├── labels_B.xlsx
│   ├── labels_C.xlsx
│   └── labels_D.xlsx
├── merged/
│   └── severity_labels.csv
├── rubric.md
├── DATASHEET.md
├── README.md
├── requirements.txt
└── CITATION.cff
```

The `PUBLIC POTHOLE DATASET/` directory is the original dataset and is **not included in this repository**. It only needs to be downloaded separately from the original PothRGBD release if you want to generate additional annotation sheets.

The `mapping.csv` file connects the generated `image_id` values to the original local RGB, depth, and label filenames. Do not rename the original files after generating the mapping unless you also update the mapping.

## Using the existing annotations

If you want to use the dataset in its current form:

- Find the four completed annotation sheets (`labels_A.xlsx`, `labels_B.xlsx`, `labels_C.xlsx`, and `labels_D.xlsx`) in `raw_labels/`.
- Find our merged severity labels in `merged/severity_labels.csv`.
- Use the raw annotations individually, or merge them according to your own requirements.

You do not need to run `labelling.py` or download the original PothRGBD images to use these released annotation files.

If you want to reproduce our merged results, refer to `merged/severity_labels.csv` and the methodology in `DATASHEET.md`. You can also run the merge script using the four supplied annotation sheets, as explained below.

## Extending the annotations

The following steps are only necessary if you want to add more labellers, create additional annotation sheets, or experiment with a different annotation setup or merging approach.

### Dataset setup

Download the original PothRGBD dataset from its official release and arrange the required files as follows:

```text
code/
├── labelling.py
├── merge_labels.py
└── PUBLIC POTHOLE DATASET/
    ├── images/    # RGB images (.jpg)
    ├── depths/    # Depth maps (.npy)
    └── labels/    # Pothole polygon annotations (.txt)
```

The labelling script expects the dataset folder to be beside the script. It pairs RGB images, depth maps, and polygon annotations using their original filenames.

The generated `image_id` values (`image_0001`, `image_0002`, etc.) are assigned by the script. They are not the original PothRGBD filenames. Use `mapping.csv` to connect these IDs to the original filenames.

### Installation

Install the dependencies:

```bash
pip install -r requirements.txt
```

The scripts require the following packages:

- `labelling.py`: `opencv-python`, `numpy`, `openpyxl`
- `merge_labels.py`: `numpy`, `pandas`, `scipy`, `scikit-learn`, `openpyxl`

### Preparing additional annotation sheets

From the repository root, run:

```bash
python code/labelling.py
```

The script generates the following outputs inside `code/`:

- `labelling_images/`: combined RGB and colour-mapped depth panels for annotation.
- `mapping.csv`: mapping between generated image IDs and original local filenames.
- `RUBRIC.txt`: the rubric embedded in the generated annotation workbook.
- `labels_A.xlsx` and `labels_B.xlsx`: blank annotation workbooks for labellers A and B.

**Warning:** Running this script deletes and rebuilds `code/labelling_images/` and overwrites `code/mapping.csv`, `code/RUBRIC.txt`, `code/labels_A.xlsx`, and `code/labels_B.xlsx`. Back up completed annotation sheets and any mapping file you need to preserve before running it again.

The script generates two blank sheets, A and B. You can use these for additional labellers. After they have been completed, place the sheets in `raw_labels/`.

### Merging annotations

The repository already contains four completed annotation sheets. If you want to reproduce our merging process or merge additional sheets, run the following command from the repository root:

```bash
python code/merge_labels.py raw_labels/labels_A.xlsx raw_labels/labels_B.xlsx raw_labels/labels_C.xlsx raw_labels/labels_D.xlsx --mapping code/mapping.csv --out merged/severity_labels.csv
```

For additional labellers, include their completed sheets in the command as well. You can also modify the merging logic in `merge_labels.py` if you want to experiment with a different approach.

The order of the sheets matters: the suffixes `_1`, `_2`, `_3`, and `_4` in the merged CSV correspond to the order in which the sheets are supplied.

The merge script uses `mapping.csv` to check image IDs. It does not require the original RGB images, depth maps, or polygon annotation files to be present when merging.

The output directory (`merged/`) must already exist.

## Output: `severity_labels.csv`

The merged file contains the following columns:

| Column | Description |
|---|---|
| `image_id` | Generated image identifier, such as `image_0001`. Use `mapping.csv` to find the original filenames. |
| `target_cont` | Continuous merged severity estimate on a 1–3 scale, calculated from confidence-weighted, rank-normalized annotations. |
| `target_class` | Merged severity class (1, 2, or 3), assigned using class-proportion-based thresholds. It is not simply `target_cont` rounded to the nearest integer. |
| `normalised_rank_spread` | Spread between the labellers' normalized ranks; used to identify disagreement. |
| `high_disagreement` | Boolean flag indicating whether the normalized rank spread exceeds 0.5. |
| `score_1`–`score_4` | Original severity scores from the four sheets, in command-line input order. `X` annotations are treated as missing severity scores. |
| `conf_1`–`conf_4` | Confidence values supplied by the corresponding labellers. |
| `rank_1`–`rank_4` | Normalized ranks for the corresponding labellers. |

The raw annotations are retained separately in `raw_labels/`. The merged file does not replace them.

## Interpreting the labels

The severity scores represent human judgments guided primarily by practical, driver-oriented descriptions:

- **1 — Low:** A driver would barely notice the pothole.
- **2 — Medium:** A driver would slow down or steer around it.
- **3 — High:** The pothole could damage a tyre or wheel, and a driver would swerve.
- **X — Exclude:** The image is not a pothole or is unsuitable for severity assessment.

Depth visualizations are provided as supporting information. See `rubric.md` for the complete scoring guidance and `DATASHEET.md` for the annotation process, merging method, and inter-rater reliability.

The merged labels are consensus estimates, not objective ground truth. Consider the `high_disagreement` flag when selecting data for model training or evaluation. Retaining the raw per-labeller scores is recommended for uncertainty-aware analysis.

Note: All 1,000 images were judged suitable for severity scoring by all four labellers — the X (exclude) option was available but not used in this release, so no images were excluded from the merged labels.

## License and citation

The severity annotations in this repository are released under the MIT License. The original PothRGBD dataset has its own license and attribution requirements; consult its original release before redistributing or using the source data.

If you use this work, cite both the original PothRGBD paper and this repository. See `CITATION.cff` for the repository citation.