# CLI Command Assistant Project Report

## Project Overview
This project implements CLI assistant using Phi-2 model, fine-tuned for generating shell commands from NLP instructions. The system first progress on base model evaluation and then through fine-tuning with LoRA to a complete agent implementation.

## Dataset Summary

**Data Source**: Custom-built dataset of CLI command Q&A pairs
- **Size**: 500+ instruction-output pairs
- **Format**: JSON with "instruction" and "output" fields
- **Content**: Real-world command-line tasks covering file operations, git commands, system monitoring, package management, and text processing from kaggle(https://www.kaggle.com/datasets/cyberprince/linux-terminal-commands-dataset).
- **Example**: 
  ```json
  {
    "instruction": "How do I list all files (including hidden) in long format?",
    "output": "ls -la"
  }
  ```

## Fine-Tuning Method

**Model**: Microsoft Phi-2 (2B parameters)
**Technique**: LoRA (Low-Rank Adaptation) for parameter-efficient fine-tuning
**Configuration**:
- Rank (r): 16
- Alpha: 32
- Dropout: 0.1
- Target modules: q_proj, v_proj, k_proj, dense
- Learning rate: 2e-4
- Batch size: 4 with gradient accumulation steps: 4
- Epochs: 1

**Training Environment**:
- Platform: Google Colab
- GPU: NVIDIA T4
- Training time: ~17 minutes

## Technical Implementation

### Base Model (Baseline)
- Loaded pretrained Phi-2 from Hugging Face
- Evaluated on 7 test prompts without any fine-tuning
- Served as performance baseline for comparison

### Fine-Tuned Model
- Applied LoRA adapters to Phi-2 base model
- Trained on custom CLI dataset
- Saved only adapter weights for efficiency
- Integrated with base model for inference

### Agent Implementation (agent.py)
**Core Features**:
- CLI NLP interaction
- Model-based plan generation with structured prompts
- Command extraction using regex patterns and heuristics
- Dry-run execution using `echo` for safety
- saved in `logs/trace.jsonl`

**Architecture**:
```
User Input → Phi-2 Fine-tuned Model → Plan Generation → Command Extraction → Dry Execution → Logging
```

## Evaluation Results

### Test Prompts (7 total)
1. "Create a new Git branch and switch to it."
2. "Compress the folder reports into reports.tar.gz."
3. "List all Python files in the current directory recursively."
4. "Set up a virtual environment and install requests."
5. "Fetch only the first ten lines of a file named output.log."
6. "How do I find and replace text in multiple files using command line?" (Edge case)
7. "What command should I use to monitor real-time system processes and memory usage?" (Edge case)

### Metrics Used
- **BLEU Score**: Measures n-gram overlap between generated and reference commands
- **ROUGE-L**: Measures longest common subsequence similarity
- **Command Accuracy**: Custom metric checking if correct command is present
- **Plan Quality**: 0-2 scale evaluating step-by-step guidance quality. To check whether the generated response is not just technically correct, but also: Explains steps clearly (Using step by step structure), Uses relevant tools (using relevant keywords), Mentions commands. 


### Performance Comparison

| Model | BLEU | ROUGE-L | Command Accuracy | Plan Quality |
|-------|------|---------|------------------|--------------|
| Base Phi-2 | 0.005 | 0.148 | 0.000 | 1.286/2.0 |
| Fine-tuned | 0.035 | 0.291 | 0.429 | 1.00/2.0 |

## Key Findings

1. **Base Model Performance**: Phi-2 shows reasonable understanding of CLI tasks but lacks specificity in command generation
2. **Fine-tuning Impact**: LoRA fine-tuning improves command accuracy and reduces hallucination
3. **Agent Effectiveness**: The agent successfully extracts and executes commands from generated plans
4. **Safety**: Dry-run execution prevents accidental system modifications

## Improvements

### 1. Context-Aware Command Generation
- **Current**: Each instruction processed independently.
- **Improvement**: Maintain conversation context and working directory state.
- **Benefit**: More natural interaction and better command chaining and more training.

### 2. Multi-Step Command Execution
- **Current**: Only executes first extracted command
- **Improvement**: Implement sequential execution of multi-step plans
- **Benefit**: Handle complex workflows requiring multiple commands

```
---

**Project Structure**:
├─ agent.py
├─ archive
│  └─ LINUX_TERMINAL_COMMANDS.jsonl
├─ comparison.ipynb
├─ finetune_dataset.json
├─ logs
│  └─ trace.jsonl
├─ model_comparison.md
├─ phi2Base
│  ├─ eval_static.md
│  ├─ logs
│  │  └─ phi2_base_evaluation.json
│  └─ phi2Base.ipynb
├─ phi2fineTuned
│  ├─ logs
│  │  ├─ phi2_finetuned_evaluation.json
│  │  └─ training_log.json
│  ├─ models
│  │  ├─ phi2-lora-cli
│  │  │  ├─ checkpoint-38
│  │  │  │  ├─ adapter_config.json
│  │  │  │  ├─ adapter_model.safetensors
│  │  │  │  ├─ added_tokens.json
│  │  │  │  ├─ merges.txt
│  │  │  │  ├─ optimizer.pt
│  │  │  │  ├─ README.md
│  │  │  │  ├─ rng_state.pth
│  │  │  │  ├─ scaler.pt
│  │  │  │  ├─ scheduler.pt
│  │  │  │  ├─ special_tokens_map.json
│  │  │  │  ├─ tokenizer.json
│  │  │  │  ├─ tokenizer_config.json
│  │  │  │  ├─ trainer_state.json
│  │  │  │  ├─ training_args.bin
│  │  │  │  └─ vocab.json
│  │  │  └─ runs
│  │  │     └─ Jun18_07-08-05_bac43f96867c
│  │  │        └─ events.out.tfevents.1750230489.bac43f96867c.377.0
│  │  └─ phi2-lora-cli-final
│  │     ├─ adapter_config.json
│  │     ├─ adapter_model.safetensors
│  │     ├─ added_tokens.json
│  │     ├─ merges.txt
│  │     ├─ README.md
│  │     ├─ special_tokens_map.json
│  │     ├─ tokenizer.json
│  │     ├─ tokenizer_config.json
│  │     ├─ training_args.bin
│  │     └─ vocab.json
│  └─ phi2FineTuning.ipynb
├─ preprocessed.ipynb
├─ readme.md
└─ Technical Task Instructions - AI_ML Intern.pdf
```
