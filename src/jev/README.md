# Jev


## Jev

## jev-ultrafast

A browser use plugin that uses the jev api to automate browsing

## The Open Jev Sprawl

[vllm pr-57250](https://github.com/vllm-project/vllm/pull/57250) introduces jev-like functionality into vllm for any model. 

Various projects exist:

- `abhishekgahlot2/openjev-server` - Serves the openjev 27B modelon vLLM or MLX  
- `ekzhang/openjev-sglang` — self-hosted, Qwen3.6-35B-A3B on SGLang/B200 (sort of a hack on traditional llm model)
- `razorback16/openjev` — self-hosted, DiffusionGemma on 24GB GPU or Apple silicon
- `openjev.com/SemIf` — in-browser demo, no install, no repo published. Uses wllama to run inference in browser using web GPU
- `NandhaKishorM/laya` - purpose-trained BERT-style encoder (not a repurposed LLM), Jev-compatible API, runs on a T4-class GPU, claims to beat Jev's accuracy

Hugging face models:

- `openjev/openjev` is a generative LLM that generates a single letter token so that its internal state can be used for probabilities
- `convaiinnovations/laya` is a classifier, based on a BERT style encoder 



### Laya

Laya is the only model I can hope to run locally.

Laya uses a model from HF [convaiinnovations/laya](https://huggingface.co/convaiinnovations/laya) and handles downloading model weights. 

```bash
# for my RTX 2070 I need CUDA 12.8
# and because my internet is shocking I need to limit downloads
UV_HTTP_TIMEOUT=600 UV_CONCURRENT_DOWNLOADS=1 \
  uv pip install torch --index-url https://download.pytorch.org/whl/cu128

uv pip install -e .


```