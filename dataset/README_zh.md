# X-Cultural Translation Benchmark 公开种子数据

本发布包包含一个多语言文学翻译基准的可重建种子元数据。它**不包含**受版权保护的完整源句或目标句。用户需要自行准备合法获得的对应书籍文本，才能重建基准文本。

## 内容

```text
data/
  en2es.jsonl
  en2ja.jsonl
  en2zh.jsonl
  es2en.jsonl
  es2zh.jsonl
  ja2en.jsonl
  ja2zh.jsonl
  ru2zh.jsonl
  zh2en.jsonl
  zh2es.jsonl
  zh2ja.jsonl
  zh2ru.jsonl
manifest.json
README.md
README_zh.md
```

本发布包包含 12 个翻译方向，共 1,470 条记录。

## JSONL 字段

每一行是一个 JSON 对象，字段如下：

- `id`：原始方向文件中的样本 id。
- `src_lang`, `tgt_lang`：源语言和目标语言代码。
- `src_identifier`, `tgt_identifier`：书籍版本标识符，例如 ISBN-13、ISBN-10 或 ASIN。
- `chapter_id`：预处理书籍 JSON 中的章节编号，从 1 开始。
- `src_prefix`, `src_suffix`：源句的紧凑规范化前缀/后缀锚点。
- `src_anchor_chars`：源句每侧锚点使用的紧凑字符数。
- `src_compact_chars`：可选字段。只有当最大 20 字符前缀 + 20 字符后缀仍有多个候选时，才给出源句的紧凑字符长度。
- `tgt_prefix`, `tgt_suffix`：目标句的紧凑规范化前缀/后缀锚点。
- `tgt_anchor_chars`：目标句每侧锚点使用的紧凑字符数。
- `tgt_compact_chars`：可选字段。只有当最大 20 字符前缀 + 20 字符后缀仍有多个候选时，才给出目标句的紧凑字符长度。
- `csi`：该样本标注的文化特定项。

## 规范化

锚点由以下规范化流程生成：

1. 去掉句子首尾的引号字符。
2. 应用 Unicode NFKC 规范化。
3. 删除所有 Unicode 标点字符。
4. 删除所有空白字符。

锚点长度按上述紧凑规范化后的字符数计算。`*_prefix` 和 `*_suffix` 中不包含标点或空格。

参考实现：

```python
import unicodedata

QUOTE_CHARS = "\"'“”‘’«»‹›「」『』《》〈〉"
SPACE_TRANSLATION = str.maketrans({
    "\u00a0": " ",
    "\u1680": " ",
    "\u2000": " ",
    "\u2001": " ",
    "\u2002": " ",
    "\u2003": " ",
    "\u2004": " ",
    "\u2005": " ",
    "\u2006": " ",
    "\u2007": " ",
    "\u2008": " ",
    "\u2009": " ",
    "\u200a": " ",
    "\u202f": " ",
    "\u205f": " ",
    "\u3000": " ",
})

def strip_edge_quotes(text: str) -> str:
    stripped = str(text).strip()
    while True:
        next_stripped = stripped.strip(QUOTE_CHARS).strip()
        if next_stripped == stripped:
            return stripped
        stripped = next_stripped

def compact_normalize(text: str) -> str:
    text = strip_edge_quotes(text)
    text = unicodedata.normalize("NFKC", text).translate(SPACE_TRANSLATION)
    return "".join(
        ch for ch in text
        if not ch.isspace()
        and not unicodedata.category(ch).startswith("P")
    )
```

在这个定义中，引号字符严格等于 `QUOTE_CHARS` 中列出的字符。Unicode 标点指 Unicode category 以 `P` 开头的字符；连字符和破折号也会按此规则删除。空白字符使用 Python 的 `str.isspace()` 判断，包括制表符、换行符、不间断空格和全角空格等。符号和 emoji 会被保留，除非它们属于标点或空白字符。日语长音符 `ー` 不属于 Unicode 标点，因此会被保留。

## 章节编号

`chapter_id` 是从内部预处理书籍 JSON 中复制出来的 1-based 章节编号。书籍 JSON 的记录格式如下：

```json
{
  "chapter_id": 1,
  "chapter_title": "CHAPTERI",
  "paragraph_id": 3,
  "text": "..."
}
```

对每个 `book_id`/语言/章节，用于重建的章节文本定义为：

```python
" ".join(item["text"] for item in records if item["chapter_id"] == chapter_id)
```

也就是按照原始 JSON 顺序，将同一 `chapter_id` 下的所有 `text` 用一个空格连接。`chapter_title` 只是元数据，不会额外加入章节文本；只有当标题本身也作为普通 `text` 记录出现时，它才会参与重建。序章、前言、后记、附录，以及 part/chapter/section 等多级结构，只有在预处理 JSON 中被赋予 1-based `chapter_id` 时，才按章节处理。

`manifest.json` 包含 `book_versions`，每个书籍版本列出：

- `book_id`, `lang`, `identifier`, `identifier_type`。
- 从元数据备注中找到的所有候选 identifier。
- `chapter_count`。

## 重建流程

对每一侧文本，即 `src` 或 `tgt`：

1. 使用 `*_identifier` 定位书籍版本。
2. 选择 `chapter_id`。
3. 按上面的规则规范化整个章节文本。
4. 寻找以 `*_prefix` 开始、以 `*_suffix` 结束的候选 span。
5. 如果存在 `*_compact_chars`，只保留紧凑字符长度等于该值的候选。
6. 剩下的候选应该唯一。

锚点从每侧 5 个紧凑字符开始；如果句子本身短于 5 个字符，则使用完整紧凑句子。必要时会自动增加前缀/后缀长度，最大为每侧 20 个紧凑字符。

候选 span 是在紧凑规范化后的完整章节文本中定义的，不需要先做句子切分。参考搜索过程如下：

```python
def recover_candidates(chapter_text: str, prefix: str, suffix: str) -> list[str]:
    candidates = []
    seen = set()
    start = chapter_text.find(prefix)
    while start != -1:
        suffix_start = chapter_text.find(suffix, start)
        if suffix_start != -1:
            candidate = chapter_text[start : suffix_start + len(suffix)]
            if candidate not in seen:
                seen.add(candidate)
                candidates.append(candidate)
        start = chapter_text.find(prefix, start + 1)
    return candidates
```

这个过程恢复的是紧凑句子文本。如果需要带标点和空格的原始样式文本，可以在重建后将紧凑字符偏移映射回本地章节文本。由于锚点构造时会去掉首尾引号，相邻的开引号/闭引号可能需要手动向外扩展。

## 版权说明

本发布包只提供书籍标识符和短规范化锚点，不分发完整小说片段或完整译文。用户需要自行获得合法的对应版本书籍，并确保自己的使用方式符合相关法律和许可条款。
