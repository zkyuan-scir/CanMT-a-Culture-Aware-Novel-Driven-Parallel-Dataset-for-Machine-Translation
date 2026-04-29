# X-Cultural Evaluation Scripts

This directory contains a cleaned, flat, open-source version of the five LLM-based evaluation scripts:

- `contextual_accuracy.py`
- `cultural_adaptation.py`
- `fidelity.py`
- `functional_equivalence.py`
- `naturalness.py`

The shared LLM calling code is in `call_llms.py`. No API keys, personal paths, or local experiment directories are included.

## Input Format

Each input row should contain:

- `src`: source sentence
- `tgt`: reference translation
- `csi`: cultural-specific item annotations
- one model translation field, such as `translation`, `model_output`, `output`, `hypothesis`, or any key ending with `_output`

Inputs are JSONL files.

## Run Evaluation

Run one dimension at a time. Example:

```bash
export OPENAI_API_KEY=...

python contextual_accuracy.py \
  --input /path/to/en2zh.jsonl \
  --output-dir /path/to/contextual_accuracy_results \
  --lang-pair en2zh \
  --model gpt-5-nano \
  --concurrency 10 \
  --resume
```

The other four dimensions use the same arguments:

```bash
python cultural_adaptation.py --input /path/to/en2zh.jsonl --output-dir /path/to/results --lang-pair en2zh
python fidelity.py --input /path/to/en2zh.jsonl --output-dir /path/to/results --lang-pair en2zh
python functional_equivalence.py --input /path/to/en2zh.jsonl --output-dir /path/to/results --lang-pair en2zh
python naturalness.py --input /path/to/en2zh.jsonl --output-dir /path/to/results --lang-pair en2zh
```

For an OpenAI-compatible endpoint:

```bash
python contextual_accuracy.py \
  --input /path/to/en2zh.jsonl \
  --output-dir /path/to/results \
  --lang-pair en2zh \
  --base-url "https://your-provider.example/v1"
```
If your model output field is not auto-detected, pass `--translation-field`.
