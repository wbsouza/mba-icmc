# Paired stationary-bootstrap inference (challenger minus baseline, mean daily net return; 999 resamples, seed 42, alpha 0.05)

| comparison | window | n days | block | effect/day | 95% CI | p | reject |
|---|---|---:|---:|---:|---|---:|---|
| PRIMARY news-only-h1-q10 vs price-only h1-candle-vol-off | untouched Nov-Dec 2016 | 60 | 4 | +0.001% | [-0.341%, +0.344%] | 0.996 | no |
| PRIMARY news-only-h1-q10 vs price-only h1-candle-vol-off | untouched Nov-Dec 2016 | 60 | 2 | +0.001% | [-0.358%, +0.361%] | 0.995 | no |
| PRIMARY news-only-h1-q10 vs price-only h1-candle-vol-off | full Mar-Dec 2016 | 304 | 5 | -0.160% | [-0.390%, +0.069%] | 0.179 | no |
| PRIMARY news-only-h1-q10 vs price-only h1-candle-vol-off | full Mar-Dec 2016 | 304 | 3 | -0.160% | [-0.397%, +0.076%] | 0.152 | no |
| exploratory news-rule-h1-minus vs price-only h1-candle-vol-off | untouched Nov-Dec 2016 | 60 | 4 | +0.183% | [-0.133%, +0.499%] | 0.237 | no |
| exploratory news-rule-h1-minus vs price-only h1-candle-vol-off | untouched Nov-Dec 2016 | 60 | 2 | +0.183% | [-0.217%, +0.583%] | 0.350 | no |
| exploratory news-rule-h1-minus vs price-only h1-candle-vol-off | full Mar-Dec 2016 | 304 | 5 | +0.034% | [-0.186%, +0.254%] | 0.731 | no |
| exploratory news-rule-h1-minus vs price-only h1-candle-vol-off | full Mar-Dec 2016 | 304 | 3 | +0.034% | [-0.176%, +0.244%] | 0.767 | no |
| exploratory news-rule-h1-minus vs hybrid h1-hybrid-vol-off | untouched Nov-Dec 2016 | 60 | 4 | +0.183% | [-0.133%, +0.499%] | 0.237 | no |
| exploratory news-rule-h1-minus vs hybrid h1-hybrid-vol-off | untouched Nov-Dec 2016 | 60 | 2 | +0.183% | [-0.217%, +0.583%] | 0.350 | no |
| exploratory news-rule-h1-minus vs hybrid h1-hybrid-vol-off | full Mar-Dec 2016 | 304 | 5 | +0.014% | [-0.203%, +0.230%] | 0.909 | no |
| exploratory news-rule-h1-minus vs hybrid h1-hybrid-vol-off | full Mar-Dec 2016 | 304 | 3 | +0.014% | [-0.200%, +0.227%] | 0.920 | no |
