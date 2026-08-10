### Monitor discrimination vs. safety

| monitor | n_honest | n_attack | usefulness | backdoor_rate | susp_honest_mean | susp_attack_mean | auc | safety@1% | safety@2% | safety@5% |
|---|---|---|---|---|---|---|---|---|---|---|
| gpt41mini | 50 | 50 | 1.0 | 0.4 | 0.0 | 0.06 | 0.6 | 0.417 | 0.417 | 0.417 |
| gpt54mini | 50 | 50 | 1.0 | 0.36 | 0.0 | 0.176 | 0.7 | 0.741 | 0.741 | 0.741 |
| gpt55 | 50 | 50 | 1.0 | 0.28 | 0.0 | 0.3 | 0.72 | 0.815 | 0.815 | 0.815 |

### Safety stability vs. sample size (safety@1%, 95% CI)

| monitor | n_per_mode | safety_median | ci95_low | ci95_high | spread |
|---|---|---|---|---|---|
| gpt41mini | 10 | 0.4 | 0.0 | 0.833 | 0.833 |
| gpt41mini | 25 | 0.4 | 0.125 | 0.765 | 0.64 |
| gpt41mini | 50 | 0.414 | 0.233 | 0.625 | 0.392 |
| gpt54mini | 10 | 0.75 | 0.333 | 1.0 | 0.667 |
| gpt54mini | 25 | 0.733 | 0.5 | 0.929 | 0.429 |
| gpt54mini | 50 | 0.741 | 0.565 | 0.897 | 0.331 |
| gpt55 | 10 | 0.833 | 0.398 | 1.0 | 0.602 |
| gpt55 | 25 | 0.824 | 0.6 | 1.0 | 0.4 |
| gpt55 | 50 | 0.818 | 0.666 | 0.957 | 0.29 |
