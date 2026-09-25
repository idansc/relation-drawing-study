#!/usr/bin/env python3
"""Collect and analyze the answers of the relation study (index.html).

The page posts every submission to an ntfy.sh topic, which keeps messages for 12 hours only.
Run this script at least every 12 hours while the study is open (or subscribe to the topic in the
ntfy app). Each run appends new messages to responses.jsonl and reports the results over everything
collected so far.

    python3 analyze.py                 # collect new answers, then analyze
    python3 analyze.py --no-fetch      # analyze responses.jsonl only
    python3 analyze.py --min-ms 800    # drop raters whose median answer time (question 1) is below 800 ms

Models are coded x = Self-Flow and y = SSF (key.json).
"""
import argparse, collections, json, os, random, statistics, urllib.request

TOPIC = 'ssf-heval-tj83te0syl33o0we7f'
# submissions that are not real raters
EXCLUDE = {'1uwpvq7': 'automated test run of the page (answers about 0.1 s after each round appeared), sent by a local copy on 2026-09-25'}
HERE = os.path.dirname(os.path.abspath(__file__))


def collect(path, topic):
    seen = set()
    if os.path.exists(path):
        for line in open(path):
            if line.strip():
                seen.add(json.loads(line)['id'])
    url = f'https://ntfy.sh/{topic}/json?poll=1&since=all'
    lines = urllib.request.urlopen(url, timeout=30).read().decode().splitlines()
    new = [e for e in (json.loads(l) for l in lines if l.strip()) if e.get('event') == 'message' and e['id'] not in seen]
    with open(path, 'a') as f:
        for e in new:
            f.write(json.dumps(e) + '\n')
    print(f'collected {len(new)} new messages ({len(seen) + len(new)} in {os.path.basename(path)})')


def raters(path):
    """Keep the most complete submission of every rater (final preferred)."""
    best = {}
    for line in open(path):
        if not line.strip():
            continue
        try:
            p = json.loads(json.loads(line)['message'])
        except (ValueError, KeyError):
            continue
        if p.get('v') != 4 or not p.get('pid') or p['pid'] in EXCLUDE:
            continue
        score = (len(p.get('trials', [])), bool(p.get('final')))
        if p['pid'] not in best or score > best[p['pid']][0]:
            best[p['pid']] = (score, p)
    return [p for _, p in best.values()]


def matches(t, m):
    """Did the rater judge the image of model m as showing the caption?"""
    right = 'y' if t['left'] == 'x' else 'x'
    return t['c'] == 'both' or (t['c'] == 'A' and t['left'] == m) or (t['c'] == 'B' and right == m)


def boot(per_rater, n=5000, seed=0):
    """95% bootstrap interval of the pooled mean, resampling raters."""
    rng = random.Random(seed)
    means = []
    for _ in range(n):
        s = [per_rater[rng.randrange(len(per_rater))] for _ in per_rater]
        num, den = sum(a for a, _ in s), sum(b for _, b in s)
        means.append(num / den if den else 0)
    means.sort()
    return means[int(.025 * n)], means[int(.975 * n)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--file', default=os.path.join(HERE, 'responses.jsonl'))
    ap.add_argument('--no-fetch', action='store_true')
    ap.add_argument('--min-ms', type=int, default=0, help='drop raters whose median relation answer time is below this')
    a = ap.parse_args()
    if not a.no_fetch:
        collect(a.file, TOPIC)
    if not os.path.exists(a.file):
        print('no responses yet'); return
    key = json.load(open(os.path.join(HERE, 'key.json')))
    R = raters(a.file)
    for p in R:
        p['rel'] = [t for t in p.get('trials', []) if t.get('c')]
        p['qual'] = [t for t in p.get('trials', []) if t.get('q')]
    R = [p for p in R if p['rel'] and statistics.median(t['ms'] for t in p['rel']) >= a.min_ms]
    done = [p for p in R if p.get('final')]
    print(f'{len(R)} raters ({len(done)} finished), {sum(len(p["rel"]) for p in R)} relation and {sum(len(p["qual"]) for p in R)} quality answers')
    if not R:
        return

    print('\nQuestion 1: does the image show the caption? (share of images judged as matching)')
    for m in 'xy':
        per = [(sum(matches(t, m) for t in p['rel']), len(p['rel'])) for p in R]
        acc = sum(x for x, _ in per) / sum(n for _, n in per)
        lo, hi = boot(per)
        byv = {v: [matches(t, m) for p in R for t in p['rel'] if t['v'] == v] for v in 'of'}
        print(f'  {key["models"][m]:12s} {100 * acc:5.1f}%  [95% CI {100 * lo:.1f}, {100 * hi:.1f}]'
              f'   original {100 * sum(byv["o"]) / max(1, len(byv["o"])):.1f}%, flipped {100 * sum(byv["f"]) / max(1, len(byv["f"])):.1f}%')

    # majority vote per image, then "both" per prompt (original and flipped rated by different raters)
    votes = collections.defaultdict(list)
    for p in R:
        for t in p['rel']:
            for m in 'xy':
                votes[(t['id'], t['v'], m)].append(matches(t, m))
    maj = {k: sum(v) / len(v) > .5 for k, v in votes.items()}
    ids = sorted({k[0] for k in votes if (k[0], 'o', 'x') in maj and (k[0], 'f', 'x') in maj})
    print(f'\n  Both layouts correct (majority vote per image, {len(ids)} prompts rated in both variants):')
    for m in 'xy':
        print(f'  {key["models"][m]:12s} {sum(maj[(i, "o", m)] and maj[(i, "f", m)] for i in ids)}/{len(ids)}')
    agree = [maj[k] == bool(key['auto'][str(k[0])][k[1]][k[2]]) for k in maj]
    print(f'  Agreement of the majority vote with the automatic OWLv2 check: {100 * sum(agree) / len(agree):.1f}% of {len(agree)} images')

    Q = [t for p in R for t in p.get('qual', [])]
    if Q:
        print('\nQuestion 2: which picture looks better?')
        pref = collections.Counter()
        for t in Q:
            right = 'y' if t['left'] == 'x' else 'x'
            pref[t['left'] if t['q'] == 'A' else right if t['q'] == 'B' else 'same'] += 1
        per = [(sum(1 for t in p.get('qual', []) if (t['q'] == 'A' and t['left'] == 'y') or (t['q'] == 'B' and t['left'] == 'x')),
                len(p.get('qual', []))) for p in R if p.get('qual')]
        lo, hi = boot(per)
        n = len(Q)
        print(f'  prefer {key["models"]["y"]}: {100 * pref["y"] / n:.1f}% [95% CI {100 * lo:.1f}, {100 * hi:.1f}]   '
              f'prefer {key["models"]["x"]}: {100 * pref["x"] / n:.1f}%   about the same: {100 * pref["same"] / n:.1f}%   ({n} answers)')


if __name__ == '__main__':
    main()
