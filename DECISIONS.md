# Decision log

A graded deliverable: 10–15 non-obvious decisions and why. Append as you go, while the
reason is still fresh. Keep the "what I gave up" column honest — that is the part that
reads as engineering judgement rather than justification.

| # | Decision | Why | What I gave up |
|---|----------|-----|----------------|
| 1 | Index the 3M-row CSV into sqlite rather than loading it in pandas | Thread reconstruction needs random access by `tweet_id`; an in-memory index plus the frame does not fit comfortably on a laptop, and every experiment would pay a ~60s reload | A one-time ~2 min indexing step, and SQL instead of dataframe ergonomics |
| 2 | The agent handles only the FIRST customer message of a thread | Later customer turns are responses to the brand's reply, so scoring them leaks the answer into the input | Cannot evaluate multi-turn follow-up handling |
| 3 | Cache every LLM response to disk, keyed by (model, temperature, prompt) | Free-tier quota is the binding constraint; caching makes the eval re-runnable at zero cost and makes published numbers reproducible | Cache invalidation is manual when a prompt changes |
| 4 | Choose the brand on reply substance (DM-deflection rate), not volume alone | A brand that answers "DM us" gives the drafter nothing to ground in, so reply-quality scores would measure nothing | Rules out the highest-volume brands |
| 5 | Retrieval defaults to scikit-learn TF-IDF, not sentence-transformers | `sentence-transformers` pulls ~2GB of torch, which alone would blow the 15-minute reproduction budget on a grader's machine. Gemini embeddings sit behind a config flag so the two can be compared in the report | Weaker semantic matching on paraphrases; measured, not assumed |
| 6 | Sample only after filtering, and sort by `thread_id` before sampling | Otherwise the "deterministic" seed still depends on the order `build_threads.py` happened to emit rows, so the committed sample would not be reproducible | Slightly more code than `random.sample` on the raw list |
| 7 | Built the agent for **Delta**, not the highest-volume brand | Delta's replies are self-contained single tweets carrying an actual answer, its intents are naturally bounded (rebooking, delay/cancellation, baggage, website/app, in-flight, loyalty/refund), and it has genuinely high-stakes messages that make the escalation decision worth making. AmazonHelp is bigger but heavily multilingual — an English filter would drop a large, non-random slice — and British_Airways splits replies across "1/2"/"2/2" tweets | ~4x less data than AmazonHelp, and findings may not generalise to brands with a different reply culture |
| 8 | Widened the deflection detector after reading real threads, and re-reported the numbers | The first version matched only "DM", which scored AmazonHelp at 1.2% deflection while its sampled replies were visibly full of "reach us by phone or chat here". The metric was measuring the word, not the behaviour. Brand choice was made on the corrected numbers | The corrected rate is still a keyword heuristic, so it undercounts paraphrased deflection; it is a floor, not a measurement |
