# Generated results — Delta, n=196

Agent model: `openai/gpt-oss-120b` · Judge model: `qwen/qwen3.8-27b`
 · runtime 1.8s

## Headline

| system | intent acc | 95% CI | macro F1 | esc. recall | esc. precision | judged sendable |
|---|---|---|---|---|---|---|
| trivial | 0.245 | ±0.060 | 0.036 | 1.000 | 0.393 | 0.475 |
| simple | 0.357 | ±0.067 | 0.248 | 1.000 | 0.393 | 0.350 |
| agent | 0.495 | ±0.070 | 0.415 | 0.169 | 0.500 | 0.800 |

## Escalation confusion (positive class = escalate)

| system | true pos | false pos | true neg | **missed escalations** | auto rate |
|---|---|---|---|---|---|
| trivial | 77 | 119 | 0 | **0** | 0.000 |
| simple | 77 | 119 | 0 | **0** | 0.000 |
| agent | 13 | 13 | 106 | **64** | 0.867 |

## Judge sub-scores (1–5)

| system | n judged | grounded | tone | resolution | sendable |
|---|---|---|---|---|---|
| trivial | 40 | 3.4 | 2.525 | 2.825 | 0.475 |
| simple | 40 | 3.725 | 2.65 | 2.625 | 0.350 |
| agent | 40 | 4.525 | 4.15 | 4.175 | 0.800 |

## Agent per-class intent scores

| intent | n in golden | precision | recall | f1 |
|---|---|---|---|---|
| praise | 48 | 0.85 | 0.69 | 0.76 |
| service_complaint | 34 | 0.41 | 0.44 | 0.42 |
| inflight_experience | 21 | 0.58 | 0.33 | 0.42 |
| general_question | 21 | 0.57 | 0.62 | 0.59 |
| rebooking_change | 19 | 0.40 | 0.32 | 0.35 |
| social_chitchat | 14 | 0.41 | 0.50 | 0.45 |
| website_app_issue | 12 | 0.70 | 0.58 | 0.64 |
| other | 10 | 0.09 | 0.10 | 0.10 |
| delay_cancellation | 8 | 0.19 | 0.38 | 0.25 |
| baggage | 8 | 0.56 | 0.62 | 0.59 |
| loyalty_refund_compensation | 1 | 0.00 | 0.00 | 0.00 |
