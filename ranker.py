"""Uses Gemini to score and rank fetched items by novelty and relevance."""

import json
import logging
import re
from google import genai
from google.genai import types

from gemini_utils import generate_content_with_retry

logger = logging.getLogger("ai_digest")

CHUNK_SIZE = 40  # items per Gemini call — keeps responses clean and avoids JSON truncation


RANKING_PROMPT = """You are an expert AI research analyst. Your job is to identify which of the items below represent genuinely novel, early-signal developments in AI and agentic systems — things that are NOT yet mainstream public knowledge.

Score each item 1–10 on:
- **Novelty**: Is this a new idea, technique, or finding? (not a rehash)
- **Relevance**: Does it relate to any of the high-signal topic areas below?
- **Signal value**: Would a serious AI practitioner want to know this today?

High-signal topic areas (score highly if genuinely new):

CORE AGENTIC ENGINEERING
- Agent Frameworks & Orchestration: multi-agent systems, swarms, hierarchical delegation, task routing, agent-to-agent protocols (A2A, MCP)
- MCP & Tool Use: Model Context Protocol ecosystem, function calling, tool schemas, structured API integration patterns
- Memory Systems: episodic, semantic, working memory architectures, retrieval, compression for long-horizon agents
- Loop & Reflection Patterns: OODA loops, self-critique, retry/reflection, iterative refinement, plan-execute-verify cycles
- AI-Native Software Engineering: coding agents, SWE-bench, autonomous debugging, repo-level reasoning, vibe coding frameworks

INTELLIGENCE & REASONING
- Inference-Time Scaling: test-time compute, thinking models (o1/o3-style), search at inference, reasoning chains
- Reasoning & Planning: world models, spatial reasoning, multi-step planning, symbolic + neural hybrids
- Context Engineering: context window management, RAG 2.0, hybrid retrieval, structured context injection, knowledge graphs + LLMs
- Multimodal Agents: vision-language, audio-language, video understanding in agentic pipelines

MODEL LAYER
- Model Release: genuinely novel foundation model releases with clear practitioner impact (not minor variants or fine-tunes)
- Fine-tuning & Alignment: LoRA, QLoRA, RLHF, DPO, GRPO, ORPO, constitutional AI, preference learning, RLAIF
- Model Efficiency & Edge AI: quantization (GGUF, AWQ, GPTQ), speculative decoding, MoE routing, on-device inference, small models

EMERGING / FRONTIER
- Embodied AI & Robotics: physical robots, sim-to-real transfer, dexterous manipulation, locomotion, humanoid robotics, VLAs
- Voice & Audio Agents: real-time speech, voice-to-voice pipelines, audio understanding, spoken dialogue systems
- Agent Security: prompt injection in agentic contexts, jailbreaks, sandboxing, adversarial attacks on LLM systems
- Synthetic Data & Evals: automated data generation, agent benchmarks, red-teaming harnesses, evaluation frameworks

REGIONAL SIGNALS
- Chinese Lab Developments: model releases and research from DeepSeek, Qwen/Alibaba, Kimi/Moonshot, Doubao/ByteDance, Baidu, Zhipu, InternLM
- Chinese Embodied AI & Robotics: humanoid and embodied intelligence from Chinese labs and startups (Unitree, AgiBot, Zhiyuan, CASIA, top Chinese universities)

Return ONLY a JSON array in this exact format (no markdown, no commentary):
[
  {{"index": 0, "novelty": 8, "relevance": 9, "signal": 7, "discipline": "Agent Frameworks & Orchestration", "one_line": "brief reason"}},
  ...
]

For "discipline", pick the single best-matching label from this list (use "Other" if none fit):
Agent Frameworks & Orchestration, MCP & Tool Use, Memory Systems, Loop & Reflection Patterns,
AI-Native Software Engineering, Inference-Time Scaling, Reasoning & Planning, Context Engineering,
Multimodal Agents, Model Release, Fine-tuning & Alignment, Model Efficiency & Edge AI,
Embodied AI & Robotics, Voice & Audio Agents, Agent Security, Synthetic Data & Evals,
Chinese Lab Developments, Chinese Embodied AI & Robotics, Other

Items to evaluate:
{items_text}
"""


def _extract_json(raw: str) -> list:
    """Robustly extract a JSON array from a Gemini response."""
    # Strip markdown fences
    raw = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    # Find the outermost JSON array
    match = re.search(r"\[.*\]", raw, re.DOTALL)
    if match:
        raw = match.group(0)
    # Remove trailing commas before ] or } (common Gemini quirk)
    raw = re.sub(r",\s*([}\]])", r"\1", raw)
    return json.loads(raw)


def _rank_chunk(client, items_chunk: list[dict], offset: int) -> tuple[dict, dict]:
    """Score one chunk of items; returns (score_map, reason_map) with global indices."""
    items_text = "\n".join(
        f"[{offset + i}] SOURCE: {item['source']} | TITLE: {item['title']}"
        f" | DATE: {item.get('date', 'unknown')} | SUMMARY: {item['summary'][:200]}"
        for i, item in enumerate(items_chunk)
    )
    prompt = RANKING_PROMPT.format(items_text=items_text)
    response = generate_content_with_retry(
        client,
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0),
        ),
    )
    scores = _extract_json(response.text.strip())
    score_map      = {s["index"]: s["novelty"] + s["relevance"] + s["signal"] for s in scores}
    reason_map     = {s["index"]: s.get("one_line", "") for s in scores}
    discipline_map = {s["index"]: s.get("discipline", "Other") for s in scores}
    return score_map, reason_map, discipline_map


def rank_items(items: list[dict], api_key: str) -> list[dict]:
    """Score items with Gemini in chunks and return sorted by combined score."""
    client = genai.Client(api_key=api_key)
    score_map:      dict[int, int] = {}
    reason_map:     dict[int, str] = {}
    discipline_map: dict[int, str] = {}

    chunks = [items[i:i + CHUNK_SIZE] for i in range(0, len(items), CHUNK_SIZE)]
    for chunk_idx, chunk in enumerate(chunks):
        offset = chunk_idx * CHUNK_SIZE
        try:
            sm, rm, dm = _rank_chunk(client, chunk, offset)
            score_map.update(sm)
            reason_map.update(rm)
            discipline_map.update(dm)
        except Exception as e:
            print(f"    [warning] ranking chunk {chunk_idx + 1}/{len(chunks)} failed: {e}")
            logger.warning(f"ranking chunk {chunk_idx + 1}/{len(chunks)} failed after retries: {e}")

    for i, item in enumerate(items):
        item["score"]      = score_map.get(i, 0)
        item["reason"]     = reason_map.get(i, "")
        item["discipline"] = discipline_map.get(i, "Other")

    return sorted(items, key=lambda x: x["score"], reverse=True)
