# Severity Labelling Rubric

Each pothole image is scored by a human labeller using the severity scale below, alongside a confidence rating.

The severity descriptions are primarily **driver-oriented**. They are intended to help labellers judge the practical seriousness of a pothole without relying on numerical depth measurements alone.

| Score | Severity | What it looks like | Driver-oriented interpretation |
|---|---|---|---|
| **1** | Low | A shallow dip, with smooth or worn edges; generally small to medium in size. | A car would barely notice it. |
| **2** | Medium | A clearly visible hole with defined edges and noticeable depth, or a wide but fairly shallow pothole. | A driver would slow down or steer around it. |
| **3** | High | A deep pothole with steep walls, or a wide and deep pothole, with broken or crumbling edges and possibly the base layer showing. | It could damage a tyre or wheel, and a driver would swerve. |
| **X** | Exclude | Not a pothole (for example, a crack, patch, shadow, or water-covered area that cannot be judged), or the image is unusable. | Exclude from severity scoring. |

## Confidence rating

Alongside the severity score, labellers provide a confidence rating:

| Confidence | Meaning |
|---|---|
| **1** | Unsure — the severity judgment is mostly a guess. |
| **2** | Somewhat sure — the image provides some useful evidence, but the judgment is uncertain. |
| **3** | Sure — the severity is reasonably clear from the available visual information. |

## Judging order

When visual cues conflict, labellers should consider them in the following order:

1. **Depth:** Consider how deep the pothole appears.
2. **Size relative to the lane:** Consider the pothole's size in relation to the road.
3. **Edge sharpness:** Consider whether the edges are smooth, defined, broken, or crumbling.

Image darkness and shadows should be ignored where possible because they can make a pothole appear deeper than it is.

## Using the depth visualizations

Each annotation panel contains an RGB image and a colour-mapped depth image. The depth visualization provides additional information about the pothole's shape and depth.
Labellers should use this visual information to support their judgment, rather than treating numerical depth values or depth-band boundaries as automatic severity scores.

Depth differences under approximately 1 cm, where a depth reading is available, should be treated as measurement noise rather than a meaningful increase in severity.

## Annotation notes

- Each image is labelled independently by four labellers.
- Each labeller provides a severity score and a confidence rating.
- `X` is used when an image is unsuitable for severity assessment or does not show a pothole.
- The four raw annotation sheets are retained so that individual judgments and disagreement can be studied.

See `DATASHEET.md` for details about the merging of the four sets of annotations and the measured inter-rater agreement.