# Which picture matches? A blind human study of relation following

Live: https://idansc.github.io/relation-drawing-study/

A three-minute blind study that compares **Self-Flow** and **SSF** on ImageNet (SiT-XL/2, 256×256, 1.3M steps, guidance 4×4, the setting of Table 2 in the paper). Each of the 20 rounds shows a caption, e.g., *a cat to the right of a dog*, and two images generated from the same noise, one by each model. Raters answer two questions on the same screen:

1. **Which picture shows the caption?** Tap A or B, or choose *Both* or *Neither*.
2. **Which looks better?** A, B, or *About the same*.

## Design
- Every rater sees each of the 20 prompts once, 10 with the original relation and 10 with the flipped one, and each model is on the left in 10 rounds. The assignment is random per rater and stays fixed after a reload.
- An emoji warm-up round explains the task, and the study starts only after a correct pick.
- Model identity is hidden. Images are coded `x` (Self-Flow) and `y` (SSF), and the key is in `key.json`, which the page does not load.
- Answers are kept in the browser, so raters can pause and resume, and are sent to an ntfy.sh topic (see `index.html`).

## Sharing
- Personal link: `https://idansc.github.io/relation-drawing-study/?p=AW` fills in the rater's initials, so they do not need to type anything.
- Preview without sending answers: add `?dry=1`.

## Results
The page posts every submission to an ntfy.sh topic, which keeps messages for 12 hours only. A scheduled GitHub Action in the private repo [idansc/relation-study-responses](https://github.com/idansc/relation-study-responses) collects new messages every hour and commits them to `responses.jsonl`, so answers are stored permanently. To analyze:

```
git clone git@github.com:idansc/relation-study-responses.git ../relation-study-responses
python3 analyze.py --no-fetch --file ../relation-study-responses/responses.jsonl
```

The script prints the per-model accuracy with 95% bootstrap intervals over raters, the number of prompts where both the original and the flipped layout are correct (majority vote per image), the agreement with the automatic OWLv2 check, and the quality preferences, reported separately for the original and the flipped relation (flipped captions ask for unusual layouts, which a model that follows them has to draw), together with the share of rounds where SSF is judged at least as good. Use `--min-ms 800` to drop raters whose median answer time is below 800 ms. Without `--no-fetch`, it also pulls the last 12 hours from ntfy directly.

## Prompts
20 of the 100 test prompts of the paper. We kept prompts where OWLv2 detects both objects in all four images (both models, original and flipped relation), and then checked all four images of every prompt blind, i.e., shuffled and without model labels, for clearly recognizable and non-overlapping objects. We dropped worn items (e.g., shorts below a t-shirt), overlapping pairs (e.g., a dog on a bench), and objects that are hard to recognize (e.g., a strainer).

This conditions the study on both objects appearing. On these 20 prompts, the automatic check gives both layouts correct for 0/20 prompts with Self-Flow vs. 15/20 with SSF, compared to 2% vs. 32% over all 100 prompts, so the results should be reported as conditional on both objects appearing.

## Files
`index.html` (the study), `trials.json` (prompts and images), `img/`, `key.json` (model key, selection, automatic scores), `analyze.py` (collection and analysis).

Forked from [avivwei96/relation-drawing-study](https://github.com/avivwei96/relation-drawing-study).
