# Generated results — Delta, n=196

Agent model: `openai/gpt-oss-120b` · Judge model: `qwen/qwen3.8-27b`
 · runtime 1.3s

## Headline

| system | intent acc | 95% CI | macro F1 | esc. recall | esc. precision | judged sendable |
|---|---|---|---|---|---|---|
| trivial | 0.245 | ±0.060 | 0.036 | 1.000 | 0.393 | 0.475 |
| simple | 0.357 | ±0.067 | 0.248 | 1.000 | 0.393 | 0.350 |
| agent | 0.490 | ±0.070 | 0.408 | 0.156 | 0.500 | 0.800 |

## Escalation confusion (positive class = escalate)

| system | true pos | false pos | true neg | **missed escalations** | auto rate |
|---|---|---|---|---|---|
| trivial | 77 | 119 | 0 | **0** | 0.000 |
| simple | 77 | 119 | 0 | **0** | 0.000 |
| agent | 12 | 12 | 107 | **65** | 0.878 |

## Judge sub-scores (1–5)

| system | n judged | grounded | tone | resolution | sendable |
|---|---|---|---|---|---|
| trivial | 40 | 3.4 | 2.525 | 2.825 | 0.475 |
| simple | 40 | 3.725 | 2.65 | 2.625 | 0.350 |
| agent | 40 | 4.525 | 4.15 | 4.075 | 0.800 |

## Agent per-class intent scores

| intent | n in golden | precision | recall | f1 |
|---|---|---|---|---|
| praise | 48 | 0.85 | 0.73 | 0.79 |
| service_complaint | 34 | 0.39 | 0.41 | 0.40 |
| inflight_experience | 21 | 0.58 | 0.33 | 0.42 |
| general_question | 21 | 0.57 | 0.62 | 0.59 |
| rebooking_change | 19 | 0.38 | 0.26 | 0.31 |
| social_chitchat | 14 | 0.44 | 0.50 | 0.47 |
| website_app_issue | 12 | 0.67 | 0.50 | 0.57 |
| other | 10 | 0.08 | 0.10 | 0.09 |
| delay_cancellation | 8 | 0.22 | 0.50 | 0.31 |
| baggage | 8 | 0.57 | 0.50 | 0.53 |
| loyalty_refund_compensation | 1 | 0.00 | 0.00 | 0.00 |
