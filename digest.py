"""Generates the daily digest summary using Grok."""

from openai import OpenAI

from grok_utils import generate_content_with_retry

MODEL = "grok-4-fast"


DIGEST_PROMPT = """You are writing a daily AI briefing for a smart, curious business reader who is NOT a programmer or academic. They care about what's happening in AI and what it means for the world — but they switch off the moment they see jargon.

YOUR GOLDEN RULE: Write every sentence as if explaining to an intelligent friend who runs a business but has never written code. No exceptions.

LANGUAGE RULES (follow these strictly):
- Replace every technical term with a plain English equivalent. Examples:
  - "LLM" → "AI language model" or just "AI"
  - "arXiv" → "research paper" or "academic paper"
  - "VLA model" → "AI system that controls robots using vision and language"
  - "fp8", "quantization", "autoregressive" → skip or explain in one plain phrase
  - "fine-tuning" → "training an existing AI on new data"
  - "inference" → "running the AI"
  - "benchmark" → "standard test"
  - "open weights / open source" → "freely available for anyone to download and use"
  - "parameters" → just use the number with "B" and say "a very large AI model"
- Never use paper or model code-names as the headline — translate them to what they DO
- Write active, direct sentences. No academic hedging.

FRESHNESS RULES:
- Only mark something "New today" if its timestamp is within the last 48 hours.
- Anything older but still gaining attention goes under "Still trending".
- Never make up dates. If unsure, omit the freshness note.

FORMAT RULES (critical for PDF readability):
- Every bullet point MUST be on its own line starting with "- "
- Never put multiple bullet items on the same line
- In Top Stories, each story is its own ### heading followed by labelled paragraphs — never a single dense paragraph
- Do not repeat or echo the section instructions in your output
- Only list categories in Today's Snapshot that have a count of 1 or more

---

Write the digest using EXACTLY this structure and these section names:

## Today's AI Snapshot

Write 2–3 plain sentences summarising the dominant theme of today's AI news. What big thing happened? What direction is AI moving today? Make it compelling and jargon-free.

Then on a new line:
**Active today:** [only list categories with count ≥ 1, format as: Category Name (N) · Category Name (N)]

Use this data for the category counts (omit any with 0):
{discipline_tally}


## What's New vs Still Trending

**Fresh in the last 48 hours:**
- **[Plain English title — what it does, not its code name]** — [One sentence. What was released or discovered?] *(Source · Date)*
[one bullet per line — never combine multiple items on one line]

**Still generating buzz from earlier this week:**
- **[Plain English title]** — [One sentence.] *(Source)*
[If nothing is recurring, write: Nothing carrying over from earlier this week.]

Use this data:
{trend_delta}


## Top Stories

For each of the 3–5 top items, write one story block in this exact format. Each block starts with a ### heading and has clearly labelled paragraphs. Put a --- divider between each story block.

### [Short, plain English headline — describe what it does or why it matters, not its technical name]

**Category:** [discipline name]  ·  **Source:** [source name]  ·  **Published:** [date if available]

**What happened:** [2 sentences max. Explain it like you're telling a smart friend who doesn't work in tech. What did researchers or a company actually do or build?]

**Why it matters:** [2 sentences. Real-world impact. What does this enable — for businesses, jobs, daily life, or the AI industry? Avoid "this is significant" — be specific about what becomes possible.]

**What to do:** [1 sentence. One concrete thing an interested reader should do — read it, watch for it, try it, note the company.]

**Read more:** [URL]

---


## Also Worth Knowing

A brief list of other notable items. One bullet per line. Plain English only.

- **[Plain English title]** ([Source]) — [One sentence, what it is and why it's interesting]. [URL if available] · *[Date if available]*


## On Our Radar This Week

3–5 concrete things worth watching or acting on this week. Plain English, action-oriented.

- **[Action or topic]:** [Why, in one plain sentence.]


## China AI Watch

What Chinese AI labs and robotics companies released or published today. Plain English.
If relevant to the global market (free to download, beats a global standard, new robot demo), say so clearly.
If the data below says none were detected, write: Nothing notable from Chinese labs today.

Use this data (pulled separately from the whole day's ranked items, not just the
Top Stories above — a Chinese release can be worth reporting here even if it
didn't make the overall top 10):
{china_context}

- **[Lab or company name]:** [What they did, in plain language.] [Global relevance if any.]


## Frontier Voices

What the founders of the newest frontier AI labs — people who left OpenAI,
Google, or Meta to start their own — published, shipped, or said today:
Ilya Sutskever (Safe Superintelligence), Yann LeCun (AMI Labs), Jeff Dean
(Discovery Loop), Andrew Ng (DeepLearning.AI), Mira Murati (Thinking
Machines Lab). Plain English — who they are and why their move matters,
not just what the post says.
If the data below says none were detected, write: Nothing notable from frontier lab founders today.

Use this data (pulled separately from the whole day's ranked items, not
just the Top Stories above):
{frontier_context}

- **[Person — Lab name]:** [What they did or said, in plain language.] [Why it matters, given who they are.]


## Market Signals

How the public markets are reacting to AI right now, for a reader who wants the business angle, not a stock tip.

2–3 plain sentences on what today's price moves and analyst sentiment across major AI-exposed companies suggest about investor confidence in AI right now. Call out any stock with a notably large move or an upcoming earnings date and connect it to today's AI news if there's a plausible link. If the data looks flat or unremarkable, say so plainly rather than inventing significance.
If market data is unavailable, write: Market data unavailable today.

Use this data:
{market_context}


## The Big Picture

2–3 plain sentences. Step back from today's news: what direction is AI heading based on these signals? What should a non-technical reader take away for the week ahead? No jargon. No buzzwords.

---

Top-ranked items to use as your source material:
{items_text}
"""


def generate_digest(
    ranked_items: list[dict],
    api_key: str,
    top_n: int = 10,
    discipline_tally: str = "",
    trend_delta: str = "",
    market_context: str = "",
    china_context: str = "",
    frontier_context: str = "",
) -> str:
    """Generate a markdown digest from the top N ranked items."""
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")

    top = ranked_items[:top_n]
    items_text = "\n".join(
        f"[Score {item['score']}] [{item.get('discipline', 'Other')}] {item['source']} — {item['title']}\n"
        f"  URL: {item['url']}\n"
        f"  Date: {item.get('date', 'unknown')}\n"
        f"  Summary: {item['summary'][:300]}\n"
        f"  License: {item.get('license', 'N/A')} | Params: {item.get('param_size', 'N/A')}\n"
        f"  Why notable: {item.get('reason', '')}"
        for item in top
    )

    prompt = DIGEST_PROMPT.format(
        items_text=items_text,
        discipline_tally=discipline_tally or "No tally available.",
        trend_delta=trend_delta or "No prior day data available (first run).",
        market_context=market_context or "Market data unavailable.",
        china_context=china_context or "No Chinese lab or robotics items detected today.",
        frontier_context=frontier_context or "No frontier-lab-founder items detected today.",
    )
    response = generate_content_with_retry(
        client,
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()
