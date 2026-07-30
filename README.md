# CanMT: Culture-Aware Novel-Driven Machine Translation

This repository contains the public release for **CanMT**, a culture-aware, novel-driven parallel dataset and evaluation suite introduced in:

> **Culture-Aware Machine Translation in Large Language Models: Benchmarking and Investigation**  
> Zekun Yuan*, Yangfan Ye*, Xiaocheng Feng, Baohang Li, Qichen Hong, Yunfei Lu, Dandan Tu, and Bing Qin  
> ACL 2026 main long paper

CanMT is designed for evaluating how well machine translation systems and large language models translate culture-specific items (CSIs) in literary contexts. The public dataset release provides reconstructable seed metadata rather than full copyrighted novel sentences or translations.

## What Is Included

```text
.
├── dataset/
│   ├── data/
│   │   ├── en2es.jsonl
│   │   ├── en2ja.jsonl
│   │   ├── en2zh.jsonl
│   │   ├── es2en.jsonl
│   │   ├── es2zh.jsonl
│   │   ├── ja2en.jsonl
│   │   ├── ja2zh.jsonl
│   │   ├── ru2zh.jsonl
│   │   ├── zh2en.jsonl
│   │   ├── zh2es.jsonl
│   │   ├── zh2ja.jsonl
│   │   └── zh2ru.jsonl
│   ├── manifest.json
│   ├── README.md
│   └── README_zh.md
└── eval/
    ├── call_llms.py
    ├── contextual_accuracy.py
    ├── cultural_adaptation.py
    ├── fidelity.py
    ├── functional_equivalence.py
    ├── naturalness.py
    └── README.md
```

The book-version metadata covers six source book groups in `dataset/manifest.json`.

## Dataset Format

Each file in `dataset/data/` is a JSONL file. Each line contains metadata needed to locate and reconstruct one source-target sentence pair from lawful local copies of the corresponding books.

Important fields include:

- `id`: sample id within the direction file.
- `src_lang`, `tgt_lang`: source and target language codes.
- `src_identifier`, `tgt_identifier`: book-version identifiers, such as ISBN-13, ISBN-10, or ASIN.
- `chapter_id`: 1-based chapter number in the prepared book JSON.
- `src_prefix`, `src_suffix`: compact-normalized source-side anchors.
- `tgt_prefix`, `tgt_suffix`: compact-normalized target-side anchors.
- `src_anchor_chars`, `tgt_anchor_chars`: number of compact characters used by each anchor.
- `src_compact_chars`, `tgt_compact_chars`: optional compact sentence length used only when anchors alone are ambiguous.
- `csi`: annotated culture-specific item(s).

See [`dataset/README.md`](dataset/README.md) for the full field definition, normalization rules, and reconstruction algorithm.

## Reconstructing Text

The public release intentionally does **not** include full novel passages or full translations. To reconstruct the benchmark text:

1. Obtain lawful local copies of the referenced book editions.
2. Locate the book version with `src_identifier` or `tgt_identifier`.
3. Select the corresponding `chapter_id`.
4. Apply the compact normalization described in [`dataset/README.md`](dataset/README.md).
5. Recover the unique span that starts with the provided prefix and ends with the provided suffix.
6. If `*_compact_chars` is present, use it to disambiguate candidates with the same anchors.

This design allows the benchmark to be released as reproducible metadata while avoiding redistribution of copyrighted literary text.

## Evaluation

The `eval/` directory contains five LLM-as-a-judge evaluation scripts:

- `contextual_accuracy.py`
- `cultural_adaptation.py`
- `fidelity.py`
- `functional_equivalence.py`
- `naturalness.py`

Install the required Python packages:

```bash
pip install openai httpx
```

Set an API key for an OpenAI-compatible endpoint:

```bash
export OPENAI_API_KEY=YOUR_API_KEY
```

Run one dimension at a time:

```bash
python eval/contextual_accuracy.py \
  --input /path/to/model_outputs/en2zh.jsonl \
  --output-dir /path/to/results/contextual_accuracy \
  --lang-pair en2zh \
  --model gpt-5-nano \
  --concurrency 10 \
  --resume
```

The evaluation input should be an evaluation-ready JSONL file containing:

- `src`: reconstructed source sentence.
- `tgt`: reference translation.
- `csi`: culture-specific item annotations.
- one model translation field, such as `translation`, `model_output`, `output`, `hypothesis`, or a field ending in `_output`.

Use `--translation-field` if the model output field cannot be detected automatically. Use `--base-url` to call another OpenAI-compatible provider.

See [`eval/README.md`](eval/README.md) for more examples.

## Heuristics of evaluation

If you are to view the evaluation system from the perspective of translation, the five aspects entail the entities involved in the process of translation, that is the author, the translator/medium and the reader. 
The **fidelity** and **contextual accuracy** deals with the author part, as they describe how well the meaning of the original sentence is retained as well as how well the CSIs fit into the context. 
The **functional equivalence** deals with the translator, reflecting how well of the function of the author is translated into the destination.
The **naturalness** and **cultural adaptation** deals with the reader part, reflecting how natural the translation sounds as well as how well they would grasp the translated culturally specific items. 

## Copyright and Responsible Use

This repository distributes identifiers, short normalized anchors, CSI annotations, reconstruction metadata, and evaluation code. It does not distribute full copyrighted source sentences, target sentences, novel passages, or full translations.

Users are responsible for obtaining lawful copies of the referenced editions and ensuring that their reconstruction, evaluation, and redistribution practices comply with applicable laws and license terms.
