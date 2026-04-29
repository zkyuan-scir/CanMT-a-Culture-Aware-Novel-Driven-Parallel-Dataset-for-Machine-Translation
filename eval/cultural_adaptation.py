#!/usr/bin/env python3
"""Evaluate Cultural Adaptation for translation outputs."""

import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from call_llms import GPT, parse_llm_response


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

LANGUAGES = {"en": "English", "zh": "Chinese", "ja": "Japanese", "ru": "Russian", "es": "Spanish"}
DIMENSION = "Cultural_Adaptation"


class Agent:
    def __init__(self, system_message: str):
        self.chat_history = [{"role": "system", "content": system_message}]


def prompt_build(query: dict[str, Any]) -> str:
    src_text = query["src_text"]
    tgt_text = query["tgt_text"]
    ref_text = query["ref_text"]
    csis = query["CSIs"]
    src_lang = query["src_lang"]
    tgt_lang = query["tgt_lang"]

    criterion = f"""
### 1. Cultural Adaptation
Assess whether the translation of culture-specific items adapts to the {tgt_lang} culture, improves reader understanding, and avoids potential cultural conflict. Assume the identity of a {tgt_lang} reader.
First identify the translation of the CSI and closely related concepts, then evaluate whether it conveys meaning, retains cultural nuance, conforms to target-culture norms, and avoids conflict.
A standard accepted translation can receive 7 when it already achieves recognition, zero misunderstanding, and seamless cultural integration.
Other parts of the sentence and whole-sentence semantic fidelity are outside this dimension.

### 2. Scoring Rubric (1-7)
1: The CSI translation causes severe cultural conflict, with no effective adaptation or retention.
2: The CSI translation shows poor adaptation, causing significant conflict or poor understanding.
3: The CSI translation includes some adaptation but still has notable cultural issues or incomplete retention.
4: The CSI translation provides basic adaptation and avoids major conflict, but could align better.
5: The CSI translation adapts well to target norms and mostly retains core cultural elements.
6: The CSI translation effectively balances adaptation and retention.
7: The CSI translation masterfully adapts to the target culture, avoids conflict, and preserves/integrates the cultural element. A widely recognized translation can receive 7.

### 3. Critical Rules
- If score < 7, provide a better translation of the CSI or related content in the reason.
- If the CSI is not translated into {tgt_lang}, the score must not exceed 4.
- Focus only on the provided CSI.
- The reason must be written in English.
"""

    return f"""
You are an expert evaluator. Please assess the translation below based on the following instructions.

## PART 1: INPUT DATA
* Source Language: {src_lang}
* Target Language: {tgt_lang}
* CSIs: {csis}
* Source Sentence: {src_text}
* Translation: {tgt_text}
* Reference Translation: {ref_text}

## PART 2: SCORING CRITERIA
{criterion}

## PART 3: OUTPUT REQUIREMENT
Please output strictly valid JSON exactly as follows:
{{
  "{DIMENSION}": {{
    "score": 1,
    "reason": "Your explanation here. If score < 7, provide a better CSI translation."
  }}
}}
"""


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, rows: list[dict[str, Any] | None]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)


def output_key(row: dict[str, Any], explicit_key: str | None) -> str:
    if explicit_key:
        return explicit_key
    for key in ("translation", "model_output", "output", "hypothesis"):
        if key in row:
            return key
    candidates = sorted(key for key in row if key.endswith("_output"))
    if not candidates:
        raise KeyError("No translation field found. Pass --translation-field.")
    return candidates[0]


def make_model(args: argparse.Namespace) -> GPT:
    return GPT(base_url=args.base_url) if args.base_url else GPT()


async def single_model_evaluate(query: dict[str, Any], model: GPT, model_name: str) -> tuple[dict[str, Any] | str, list[str]]:
    agent = Agent(
        "You are a highly rational translation expert with deep expertise in translation theory, "
        "linguistics, and intercultural communication."
    )
    prompt = prompt_build(query)
    agent.chat_history.append({"role": "user", "content": prompt})
    progress = [f"Evaluation Prompt: {prompt}"]

    for retry in range(6):
        response = await model.generate(agent.chat_history, model=model_name)
        response_json = await parse_llm_response("", response)
        if response_json != "":
            progress.append(f"Evaluation Result: {response_json}")
            return response_json, progress
        logging.warning("LLM response parse failed. Retrying %s/5", retry + 1)
    return "", ["LLM call failed."]


async def process_one_item(
    idx: int,
    data: dict[str, Any],
    semaphore: asyncio.Semaphore,
    results: list[dict[str, Any] | None],
    model: GPT,
    model_name: str,
    file_lock: asyncio.Lock,
    output_path: Path,
    src_lang: str,
    tgt_lang: str,
    translation_field: str | None,
) -> None:
    async with semaphore:
        try:
            key = output_key(data, translation_field)
            query = {
                "src_lang": src_lang,
                "tgt_lang": tgt_lang,
                "src_text": data["src"],
                "tgt_text": data[key],
                "ref_text": data["tgt"],
                "CSIs": data.get("csi", []),
            }
            result, progress = await single_model_evaluate(query, model, model_name)
            info = result.get(DIMENSION, {}) if isinstance(result, dict) else {}
            results[idx] = {
                "id": data.get("id", idx),
                "src_text": data["src"],
                "tgt_text": data[key],
                "ref_text": data["tgt"],
                "csi": data.get("csi", []),
                DIMENSION: info,
                "process": progress,
                "raw_response": result,
            }
            async with file_lock:
                await asyncio.to_thread(write_json, output_path, results)
        except Exception as exc:
            logging.exception("Error processing item %s: %s", idx, exc)


async def process_file(path: Path, args: argparse.Namespace) -> None:
    src_code, tgt_code = args.lang_pair.split("2", 1)
    src_lang = LANGUAGES.get(src_code, src_code)
    tgt_lang = LANGUAGES.get(tgt_code, tgt_code)
    output_path = args.output_dir / path.with_suffix(".json").name
    rows = read_jsonl(path)
    results: list[dict[str, Any] | None] = [None] * len(rows)

    if args.resume and output_path.exists():
        try:
            existing = json.loads(output_path.read_text(encoding="utf-8"))
            for idx, item in enumerate(existing[: len(results)]):
                if item:
                    results[idx] = item
        except Exception:
            pass

    model = make_model(args)
    semaphore = asyncio.Semaphore(args.concurrency)
    file_lock = asyncio.Lock()
    tasks = [
        process_one_item(idx, row, semaphore, results, model, args.model, file_lock, output_path, src_lang, tgt_lang, args.translation_field)
        for idx, row in enumerate(rows)
        if results[idx] is None
    ]
    if tasks:
        await asyncio.gather(*tasks)
    write_json(output_path, results)
    logging.info("Wrote %s", output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Input jsonl file or directory containing jsonl files.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--lang-pair", required=True, help="Language pair, e.g. en2zh.")
    parser.add_argument("--translation-field", help="Model output field. Defaults to auto-detection.")
    parser.add_argument("--model", default="gpt-5-nano")
    parser.add_argument("--base-url", default=None)
    parser.add_argument("--concurrency", type=int, default=10)
    parser.add_argument("--resume", action="store_true")
    return parser


async def amain(args: argparse.Namespace) -> None:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    files = [args.input] if args.input.is_file() else sorted(args.input.glob("*.jsonl"))
    for path in files:
        await process_file(path, args)


def main() -> None:
    asyncio.run(amain(build_parser().parse_args()))


if __name__ == "__main__":
    main()
