# 10. Cost Optimization

## What Is It?

Every dial this module has taught you — instance limits, caching, which model you call — is also, quietly, a cost dial. Cost optimization is the topic that stops treating those as separate concerns and looks at them as one thing: for the same quality of moderation, how do we spend the least money and time?

## Why It Matters for AI Engineers

AI calls are the single most expensive line item in a service like ModeraAI — far more than compute, storage, or networking. A service that "works" but costs 5x what it needs to isn't actually production-ready; billing anxiety is one of the top reasons AI projects get killed after launch. This topic closes the module by tying every earlier topic back to the number that ultimately decides whether a project survives: the bill.

## Key Concepts

| Term | Definition |
|---|---|
| Model tiering | Using a cheaper, faster model (Gemini Flash) instead of a pricier one (Gemini Pro) when quality allows |
| Cost per call | The actual $ cost of one Gemini request, driven by input/output tokens |
| Avoided call | A call that never happened because caching served a saved answer instead |
| Right-sizing | Setting `--max-instances`/`--min-instances` to match real traffic, not guesswork |

## How It Fits Together

```mermaid
flowchart TD
    A[Cost Optimization] --> B["Caching (topic 6):<br/>fewer real Gemini calls"]
    A --> C["Scaling (topic 1):<br/>--max-instances caps runaway spend"]
    A --> D["Model choice:<br/>Flash vs Pro"]
    A --> E["Rate Limiting (topic 9):<br/>caps abuse-driven spend"]
    B --> F[Lower monthly bill]
    C --> F
    D --> F
    E --> F
```

## Hands-On

```bash
# runs the same input through both models, prints token counts and an estimated cost,
# then proves caching with the service's /stats counter
set -a && source .env && set +a
uv run python scripts/cost_comparison_demo.py
```

## How We Test It

Concrete proofs, not estimates:

1. **Model comparison:** the script sends the same request through `gemini-2.5-flash` and `gemini-2.5-pro` and prints each call's real token usage. The prices in the script are illustrative, so read the ratio (Pro costs about 25 times more here), not the dollars.
2. **Caching's real savings:** the script sends 6 requests, 3 of them repeats, and reads the service's `/stats` counter before and after. On our run: **6 requests, 3 real Gemini calls, 3 avoided**. The counter lives in each instance's memory, so this is only exact when one instance answers the whole run.
3. **Hidden "thinking" tokens:** Gemini 2.5 thinks before it answers, and those tokens are billed too. The script's "output tokens" leaves them out; on our run they were most of the total. For a simple yes/no task thinking can be turned off (`thinking_budget=0`), which cut one request's tokens by about 80% in one test. But in a second test it also **changed the verdict**, so check quality on real comments before using it. It is not turned on in `main.py`.

Close by walking through the "which earlier topic is secretly also a cost control" list live: caching (fewer calls), `--max-instances` (spend ceiling), rate limiting (abuse ceiling), model choice (per-call price) — reinforcing that this topic isn't new work, it's a new lens on work already done.

## Common Pitfalls

- Defaulting to the biggest/priciest model "to be safe" without measuring whether the cheaper one is actually good enough for this task
- Treating cost optimization as a one-time exercise instead of something to re-check as usage patterns change
- Optimizing model cost while leaving `--max-instances` unset — a single dial left uncapped can dwarf every other saving

## Quick Recap

1. Name three topics from earlier in this module that double as cost controls, and how each one saves money.
2. Why does this topic measure real token counts and a real call counter instead of just estimating costs on paper?
3. Why might Gemini Pro still be the right choice for some tasks despite costing more than Flash?
