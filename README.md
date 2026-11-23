# news-image-20261122-v5

One image summing up the world news of **Sunday 22 November 2026**.

[![make.fun · news-image-20261122](https://make.fun/badge/news-image-20261122.svg)](https://make.fun/bounty/news-image-20261122?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261122)

[![rank](https://make.fun/badge/news-image-20261122/Misaka450/news-image-20261122-v5/rank.svg)](https://make.fun/bounty/news-image-20261122/leaderboard)
[![reward](https://make.fun/badge/news-image-20261122/Misaka450/news-image-20261122-v5/reward.svg)](https://make.fun/bounty/news-image-20261122)

34 stories across seven regions, every one dated. A six-cell ledger of the day's
numbers, a UTC timeline, nine illustrated lead cards, a pinned world map, two
columns of further dispatches, and a date-check strip that names what was left out
and why.

## Run

```bash
python3 build.py     # writes entry.png and preview-300.png (1024x1024, <=1 MiB)
node main.ts         # copies entry.png to $MAKEFUN_OUTPUT_DIR/entry.png
```

No network, no image models: everything is drawn with Pillow.

## License

MIT
