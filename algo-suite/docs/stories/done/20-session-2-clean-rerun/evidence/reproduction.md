## Models (session 2 vs session 1)

| model | sha256 s2 | sha256 s1 | identical bytes | identical after dropping provenance | differing keys (outside provenance) |
|---|---|---|---|---|---|
| h1-baseline | c290399c701c | 80f012b99b79 | no | yes | provenance |
| h1-hybrid | b7e1e5644b04 | 4220696d32cf | no | yes | provenance |
| h4-baseline | 61112712ec6f | a7c4ef2e48ce | no | yes | provenance |
| h4-hybrid | 4ec47a47bbb1 | 52ef933b8a5e | no | yes | provenance |
| m5-baseline | ba7d08e02d77 | b113d79c0c87 | no | yes | provenance |
| m5-hybrid | 1895dcb60811 | 0b504b1387e3 | no | yes | provenance |
| m15-baseline | b1fed676d168 | c7b7f0b7abed | no | yes | provenance |
| m15-hybrid | d77dc8c1b3c7 | e4c6d5aa9c9e | no | yes | provenance |
| m30-baseline | 33395704b991 | 30a3a5a6e5d1 | no | yes | provenance |
| m30-hybrid | b49dc4a06aaf | f8c7ec248d40 | no | yes | provenance |
| news-only-h1 | a2dac1cc7e19 | a243f75e3f37 | no | yes | provenance |
| news-only-h4 | 8ba88a08d702 | 92bd5cb16d83 | no | yes | provenance |

## Cells (session 2 vs session 1)

| session-2 cell | session-1 cell | trades s2 | trades s1 | final equity s2 | final equity s1 | equity.csv identical | trade P/L identical |
|---|---|---:|---:|---:|---:|---|---|
| h1-q05-base | h1-q05-base | 148 | 148 | 8468.74 | 8468.74 | yes | yes |
| h4-q10-base | q10-vol-off | 223 | 223 | 9552.87 | 9552.87 | yes | yes |
| h4-q10-hybrid | q10-hybrid-vol-off | 239 | 239 | 9445.86 | 9445.86 | yes | yes |
| h4-q10-atr-stop | q10-atr-stop | 80 | 80 | 9942.61 | 9942.61 | yes | yes |
| news-only-h1-q10 | news-only-h1-q10 | 252 | 252 | 6158.75 | 6158.75 | yes | yes |
| news-only-h4-q10 | news-only-h4-q10 | 91 | 91 | 7894.46 | 7894.46 | yes | yes |
| news-rule-h1-plus | news-rule-h1-plus | 180 | 180 | 5150.31 | 5150.31 | yes | yes |
| news-rule-h1-minus | news-rule-h1-minus | 39 | 39 | 11220.45 | 11220.45 | yes | yes |
| news-rule-h4-plus | news-rule-h4-plus | 48 | 48 | 7942.40 | 7942.40 | yes | yes |
| news-rule-h4-minus | news-rule-h4-minus | 10 | 10 | 10238.58 | 10238.58 | yes | yes |
| always-short-h1 | always-short-h1 | 298 | 298 | 9220.58 | 9220.58 | yes | yes |
| always-short-h4 | always-short-h4 | 91 | 91 | 10136.96 | 10136.96 | yes | yes |
| h1-fixed-base | h1-candle-vol-off | 44 | 44 | 9877.54 | 9877.54 | yes | yes |
| h1-fixed-hybrid | h1-hybrid-vol-off | 43 | 43 | 9922.19 | 9922.19 | yes | yes |
| h1-fixed-vol-0.8 | h1-vol-0.8 | 29 | 29 | 10173.00 | 10173.00 | yes | yes |
