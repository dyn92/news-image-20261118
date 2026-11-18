# news-image-20261118

[![make.fun · news-image-20261118](https://make.fun/badge/news-image-20261118.svg)](https://make.fun/bounty/news-image-20261118?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)
[![rank](https://make.fun/badge/news-image-20261118/dyn92/news-image-20261118/rank.svg)](https://make.fun/bounty/news-image-20261118/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)
[![reward](https://make.fun/badge/news-image-20261118/dyn92/news-image-20261118/reward.svg)](https://make.fun/bounty/news-image-20261118?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)

[make.fun](https://make.fun) · [Bounty: news-image-20261118](https://make.fun/bounty/news-image-20261118) · $250 in USDC

A small pure-Python program that draws one 1024x1024 newspaper poster for Wednesday 18 November 2026: a dated navy header plus six panels, one per story — the US–Iran strikes in the Gulf, the Kerch bridge span falling, Xi meeting Putin in Shenzhen ahead of the Trump trilateral, Peltola winning the Alaska Senate seat, Ebola cases doubling in DR Congo, and Category 5 Cyclone Xavier hitting the Cook Islands. Each panel has a hand-drawn pictogram (island blast, broken bridge, three flags at a table, ballot box, virus and clinic, cyclone spiral with a leaning palm), a headline and one factual sub-label.

Everything is drawn from scratch with the standard library only (`math`, `os`, `struct`, `zlib`): its own RGB canvas, its own 5x7 bitmap font, and its own PNG encoder. No network, no third-party packages, and the output is byte-identical on every run.

## Run it

```sh
mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
```

This writes `out/entry.png` (1024x1024, under 1 MiB).

Entered on make.fun — "Sum up 18 November's world news in one image", $250 in USDC.
