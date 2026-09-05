# ML Evidence Index

This index catalogs usable machine-learning trainer, config, and log artifacts
that exist under `/Users/david/Projects/**`. Every entry was verified on disk
during this session. Digests were computed with `shasum -a 256` on the real
file contents. No metrics are invented; any number quoted below is copied
verbatim from the cited artifact.

Scan date: 2026-09-05. Scan root: `/Users/david/Projects/`. Excluded paths:
`.git`, `.venv`, `node_modules`, `__pycache__`, `.mypy_cache`,
`.pytest_cache`, `.ruff_cache`, `dist`, `.DS_Store`.

## How to read an entry

| Field | Meaning |
| --- | --- |
| path | Absolute filesystem path |
| type | File type / role |
| bytes | Size in bytes (`stat -f %z`) |
| mtime | Last modified date (`stat -f %Sm -t %Y-%m-%d`) |
| sha256 | `shasum -a 256` digest computed this session |

---

## 1. claude-yolo-v4-doc — Qwen2.5-Coder-7B SFT+DPO training docs

Project root: `/Users/david/Projects/claude-yolo-v4-doc`

### 1.1 Model configs (SFT stage)

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/claude-yolo-v4-doc/model-configs/sft/config.json` | HF model config (Qwen2, 28 layers, 3584 hidden, bf16) | 1376 | 2026-08-15 | `de5711ac9de8b14177e8756c77c7e9104ffe0624a159b4e73ff6e3d708b5c695` |
| `/Users/david/Projects/claude-yolo-v4-doc/model-configs/sft/generation_config.json` | HF generation config (temp 0.7, top_p 0.8, rep_penalty 1.1) | 216 | 2026-08-15 | `f70ec8c3fa78df38ed5b3aec64166cd1580827c109de7bedc442cf3d8477b0f4` |
| `/Users/david/Projects/claude-yolo-v4-doc/model-configs/sft/tokenizer_config.json` | HF tokenizer config | 693 | 2026-08-15 | `8b6f658e2435ec8da6866013cb485a1d2a6559bed4bf76ed99ea68b031854b41` |
| `/Users/david/Projects/claude-yolo-v4-doc/model-configs/sft/chat_template.jinja` | ChatML chat template | 2507 | 2026-08-15 | `cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f` |

### 1.2 Model configs (DPO stage)

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/claude-yolo-v4-doc/model-configs/dpo/config.json` | HF model config (identical architecture to SFT) | 1376 | 2026-08-15 | `de5711ac9de8b14177e8756c77c7e9104ffe0624a159b4e73ff6e3d708b5c695` |
| `/Users/david/Projects/claude-yolo-v4-doc/model-configs/dpo/generation_config.json` | HF generation config (same params as SFT) | 216 | 2026-08-15 | `f70ec8c3fa78df38ed5b3aec64166cd1580827c109de7bedc442cf3d8477b0f4` |
| `/Users/david/Projects/claude-yolo-v4-doc/model-configs/dpo/tokenizer_config.json` | HF tokenizer config | 693 | 2026-08-15 | `4d8ad3fe9729e37338fae50bac94ff03cb915071eb886b937077114e874dfa06` |
| `/Users/david/Projects/claude-yolo-v4-doc/model-configs/dpo/chat_template.jinja` | ChatML chat template | 2507 | 2026-08-15 | `cd8e9439f0570856fd70470bf8889ebd8b5d1107207f67a5efb46e342330527f` |

Note: SFT and DPO `config.json` are byte-identical (same sha256). Same for
`generation_config.json` and `chat_template.jinja`. The `tokenizer_config.json`
differs by one byte between stages.

### 1.3 Training and eval results

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/claude-yolo-v4-doc/results/summary.json` | Training summary (SFT 2423 examples, 3 epochs, lr 2e-5, final_loss 1.38; DPO 1031 pairs, 1 epoch, lr 1e-6, beta 0.3, final_loss 0.5579; HumanEval 88.4% pass@1) | 1993 | 2026-08-15 | `85f7671242a727d5b52a4ef7e16a0a808fa2265f4452663b6e2013a2ff24955d` |
| `/Users/david/Projects/claude-yolo-v4-doc/eval-results/Qwen--Qwen2.5-Coder-7B-Instruct_humaneval_results.json` | Base model HumanEval results (baseline) | 83338 | 2026-08-15 | `90401b8e26c663a56de35ac5edea60e21306bebc68844df9ab7d4638e5725c67` |

### 1.4 Training logs

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/claude-yolo-v4-doc/logs/sft_v3_train.log` | SFT v3 training log | 15401 | 2026-08-15 | `7ae8295a0a7758f45c74ab36dda53c34369f904b66e3b5584f5494791cebfc6a` |
| `/Users/david/Projects/claude-yolo-v4-doc/logs/dpo_train.log` | DPO training log | 19981 | 2026-08-15 | `30a2052c7c56d7483c12d128893912e418fa4ea9d5560fcc0661880ea7bf59ca` |
| `/Users/david/Projects/claude-yolo-v4-doc/logs/pipeline_v3.log` | Full pipeline v3 log | 19819 | 2026-08-15 | `e0bb7d8f090bf4ac2632b09c1a11485bf168c511a816e009be5cbbee5c44f733` |

### 1.5 Trainer and eval scripts

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/claude-yolo-v4-doc/scripts/train_sft_v2.py` | SFT v2 trainer (Qwen2.5-Coder-7B, 786K examples, 2 epochs, lr 2e-5) | 5034 | 2026-08-15 | `f9cca770cbb218a94406b068e2d6b0b290b914c9e6395d49106238fbe376b22d` |
| `/Users/david/Projects/claude-yolo-v4-doc/scripts/train_dpo_v2.py` | DPO v2 trainer (beta 0.3, lr 1e-6) | 6591 | 2026-08-15 | `81af423f10194452e28acb8d5a8ed53d5e908ea82c24a3afafd09aed186ee886` |
| `/Users/david/Projects/claude-yolo-v4-doc/scripts/eval_humaneval_v2.py` | HumanEval evaluator (chat template, self-contained scripts) | 6963 | 2026-08-15 | `4b4f3c1b32c50a38d4b5cc008889eb4ad52a240fd49f86a429d0b1327f0f2be2` |
| `/Users/david/Projects/claude-yolo-v4-doc/scripts/export_to_mlx.py` | MLX 4-bit export script | 4404 | 2026-08-15 | `6e61731e3d12f02ba44182762f330c60f16d4fce0e78b5163d4e092c7fee5df8` |

### 1.6 Methodology and data docs

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/claude-yolo-v4-doc/METHODOLOGY.md` | Training methodology | 12338 | 2026-08-15 | `c276f9feec3cfae0681ccc5117049079441eb8edb5132645b28ee99769961cc2` |
| `/Users/david/Projects/claude-yolo-v4-doc/EVALUATION.md` | Evaluation methodology | 6889 | 2026-08-15 | `71b6b57edb00c8e41a9a155fd5d32376a0dc9a67d8e08666900b7c019b030cbe` |
| `/Users/david/Projects/claude-yolo-v4-doc/DATA.md` | Dataset documentation | 13468 | 2026-08-15 | `421f24489aae387c65bdc4aa94e8e33e45151dac49d4b11d8e88975f6e1f5227` |

---

## 2. claude-yolo-train — Training scripts and datasets

Project root: `/Users/david/Projects/claude-yolo-train`

### 2.1 Dataset artifacts

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/claude-yolo-train/data/dataset_summary.json` | Dataset summary (696 total: 274 coding, 128 tools, 94 build, 200 vibe) | 483 | 2026-08-14 | `bd8643fb07bcdf046d3528d96b7d6561645f6293b8546a846d37f23eb54e7b66` |
| `/Users/david/Projects/claude-yolo-train/data/eval_results.json` | HumanEval eval results (v2 model, 53.66% pass@1, 88/164 passed) | 22165 | 2026-08-14 | `bb00dab3b2ca942f4b04327d64e7ca852c355141941c1f821f45aad69ace3e00` |
| `/Users/david/Projects/claude-yolo-train/data/combined_train.jsonl` | Combined training data (JSONL) | 5157649 | 2026-08-14 | `dc87904dc255837d85e07954fcfc18d75559141bb21ed2f08fd99aaa63896d01` |
| `/Users/david/Projects/claude-yolo-train/data/sft_agent_mix.jsonl` | SFT agent mix (JSONL) | 10304869 | 2026-08-15 | `53d1c944f9b42ea9e3061cbc0ea00cabbf003962f3e896065f6bbc6c2efe3845` |

### 2.2 Trainer scripts

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/claude-yolo-train/train.py` | SFT trainer (Qwen2.5-Coder-1.5B, gradient checkpointing, 8-bit Adam, LoRA option) | 8477 | 2026-08-14 | `89d5c137876b178e1deeb95a1dbb4d3410e4310b1816f85dc62067ebf8046e17` |
| `/Users/david/Projects/claude-yolo-train/eval_humaneval_v2.py` | HumanEval evaluator (identical to v4-doc copy) | 6963 | 2026-08-15 | `4b4f3c1b32c50a38d4b5cc008889eb4ad52a240fd49f86a429d0b1327f0f2be2` |
| `/Users/david/Projects/claude-yolo-train/export_to_mlx.py` | MLX export script (identical to v4-doc copy) | 4404 | 2026-08-15 | `6e61731e3d12f02ba44182762f330c60f16d4fce0e78b5163d4e092c7fee5df8` |
| `/Users/david/Projects/claude-yolo-train/feature_list.json` | Feature list with pass/fail status | 2332 | 2026-08-15 | `9f12d1d0f894efbca2e6cb57ae69a727942c37fbabe789503a520f511a305ece` |

### 2.3 YOLO OBB model weights (computer vision)

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/claude-yolo-train/models/yolo11n-obb.pt` | YOLO11n oriented bounding box weights (PyTorch) | 5795654 | 2026-07-30 | `b62898ebf38940ca4df323863e45ee9d84a1a46d5d11ebdde529fb33aa9f3a32` |
| `/Users/david/Projects/claude-yolo-train/models/yolo26n-obb.pt` | YOLO26n OBB weights (PyTorch) | 5907357 | 2026-07-30 | `6f51c78197aacda4a33be77294065a9001675fb893f56227a179731b53dbd2b0` |
| `/Users/david/Projects/claude-yolo-train/models/yolo26n-obb.onnx` | YOLO26n OBB weights (ONNX export) | 9997857 | 2026-07-30 | `6b75ac8cb45536a953175f2881cbbb22c55c53ea049268570e6127d14d4f7ca4` |

---

## 3. claude-yolo-vibes — Deployment manifests and system prompts

Project root: `/Users/david/Projects/claude-yolo-vibes`

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/claude-yolo-vibes/models/Modelfile.yolo-vibes-v4` | Ollama Modelfile (FROM qwen2.5-coder:7b-instruct-q4_k_m, temp 0.2, top_p 0.95, ctx 32768) | 1744 | 2026-08-17 | `d33014ced03ce87429a307a6c309b860534cd3b44c28d54a34422121fe6fc7ca` |
| `/Users/david/Projects/claude-yolo-vibes/system-prompts/yolo-vibes-v5.md` | System prompt (vibes mode + code mode switching) | 1620 | 2026-08-17 | `c8d8a21d784b9be08942f1af93c85636a953a9dadf95686d087d89f5b2575fbf` |
| `/Users/david/Projects/claude-yolo-vibes/README.md` | Deployment README (MLX 4-bit, Apple Silicon, ~11.5 tok/s) | 9041 | 2026-08-17 | `c510bd5a322c162989e77cf379123a148136855ab22efc941eb07ad1807533fa` |

---

## 4. apple-quality-recognition-engine — YOLO apple defect detector

Project root: `/Users/david/Projects/apple-quality-recognition-engine`

### 4.1 Training configs

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/apple-quality-recognition-engine/data.yaml` | YOLO dataset config (4 classes: apple, stem_calyx, defect_surface, defect_critical) | 818 | 2026-09-03 | `75cce0430a40f640de1ce577fefe24cba9a2584735b13f9367bfd7b95467dede` |
| `/Users/david/Projects/apple-quality-recognition-engine/grading_policy.yaml` | Grading policy (G1/G2/G3/CIDER/DISCARD, surface ratio thresholds 2/10/25%) | 886 | 2026-09-03 | `4455c84dc6545ad429fc0f8ef73e5866f3defceda75ad67762345c6bb16de2b6` |
| `/Users/david/Projects/apple-quality-recognition-engine/wb_calibration.json` | White balance calibration (gray_world + daylight_blue_boost, 5600K target) | 210 | 2026-09-03 | `63e0b1658e4ab26d2ecfec7d9ac9729a20a7dd38231dabfdcd1bc507f2a0278d` |

### 4.2 Training run artifacts

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/apple-quality-recognition-engine/runs/detect/runs/detect/plant_yolo26n/args.yaml` | YOLO train args (yolo11n.pt base, 50 epochs, batch 16, imgsz 640, device mps, seed 0) | 1751 | 2026-08-31 | `5cdb4370480d7e9c291a183777c563cfd353f955a94697759454bbea06a85c7f` |
| `/Users/david/Projects/apple-quality-recognition-engine/runs/detect/runs/detect/plant_yolo26n_checkpoint/args.yaml` | YOLO checkpoint run args | 1772 | 2026-08-31 | `4c70769800b16a89550dbf080ee185713e8b56db607fc18839dce42a36d887e6` |
| `/Users/david/Projects/apple-quality-recognition-engine/runs/detect/runs/detect/plant_yolo26n_checkpoint/results.csv` | Checkpoint training results CSV | 404 | 2026-08-31 | `b8faf038aac7cdd94d19922bf027865257a90a5eb4e8380787b93234c3438ce6` |
| `/Users/david/Projects/apple-quality-recognition-engine/training_results.csv` | Full training results CSV (50 epochs, box/cls/dfl loss, mAP50, mAP50-95) | 11840 | 2026-08-31 | `10a3fe00fd13fcfd985b764a4a262194acefa6e753d1801a885df4c81b91a97d` |

### 4.3 Training visualizations

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/apple-quality-recognition-engine/confusion_matrix.png` | Confusion matrix (PNG, 3000x2250, RGBA) | 135593 | 2026-08-31 | `0324aaa7f9802de65d8ee06c9932b8fb1e4f49fc71fe92c8fee72de68a6d6073` |
| `/Users/david/Projects/apple-quality-recognition-engine/training_results.png` | Training results plot (PNG, 2400x1200, RGBA) | 281398 | 2026-08-31 | `669e97119c20613393dd599ae52a66da137c5a3c0a2a0ef08618fc1ed0a139d9` |

### 4.4 Model weights

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/apple-quality-recognition-engine/plant_yolo26n_best.pt` | Best YOLO26n plant detector weights (PyTorch) | 5479315 | 2026-08-31 | `8b4593d53714cc3bdfde7fcd5d808cbc794d0b1c27c4d7fdcf8ba4fa148d1798` |
| `/Users/david/Projects/apple-quality-recognition-engine/yolo11n.pt` | YOLO11n base weights (PyTorch) | 5613764 | 2026-08-31 | `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1` |

### 4.5 CoreML export manifest

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/apple-quality-recognition-engine/plant_yolo26n_best.mlpackage/Manifest.json` | CoreML model package manifest | 617 | 2026-08-31 | `bf42303ec58661be42b039495f567e7d6957d7a9ca8b0b31da7058a682d49047` |

---

## 5. ml_backend_lab — Backend precision and provenance experiments

Project root: `/Users/david/Projects/ml_backend_lab`

### 5.1 Run metadata and experiment results

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/ml_backend_lab/results/run_metadata.json` | Run metadata (ResNet18 ONNX, ONNX-GPU, fp32, Tesla T4, torch 2.11.0+cu128, CUDA 12.8) | 1477 | 2026-07-25 | `c5869248b88a22589b6b1c241ecbc56cd4404eee3381b4a028142fe2cbc2abc7` |
| `/Users/david/Projects/ml_backend_lab/results/exp001_summary.json` | Experiment 001 summary (3 runs: resnet CPU, resnet GPU, yolo GPU) | 445 | 2026-07-25 | `f4f9726e7ac5614937e3fb8e2905c6b07f85637c38956e006c4afffbdb78000a` |
| `/Users/david/Projects/ml_backend_lab/results/exp001_resnet_pt_vs_ort_cpu.json` | ResNet18 PyTorch vs ONNX CPU results | 1960 | 2026-07-25 | `371925f265654c075780e1f0eca494e345e51d428698864d59d4ff7e2c2d5187` |
| `/Users/david/Projects/ml_backend_lab/results/exp001_resnet_pt_vs_ort_gpu.json` | ResNet18 PyTorch vs ONNX GPU results | 1955 | 2026-07-25 | `fa5aee505ef67fe3af9516202cca6f989bf11f05daa36eaa3975039e74c64da1` |
| `/Users/david/Projects/ml_backend_lab/results/exp001_yolo_pt_vs_ort_gpu.json` | YOLO PyTorch vs ONNX GPU results | 1818 | 2026-07-25 | `ca6a34070839a491e3a33a7c29ab33036e78834fa6736b0851868aee316ba003` |

### 5.2 Backend truth and provenance reports

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/ml_backend_lab/results/backend_truth_report.json` | Backend truth audit (TensorRT requested → CUDA fallback; false confidence detected) | 1975 | 2026-07-25 | `4b92ec97b379fc4497d46497d04bc5633d981aa668011ef3002b29458c42ec9d` |
| `/Users/david/Projects/ml_backend_lab/results/determinism_report.json` | Determinism report | 25211 | 2026-07-25 | `09e3eba478cd1461aea313a3f5152967b38ecb114f04335d8d46ccece45ac5d8` |
| `/Users/david/Projects/ml_backend_lab/results/provenance_adversarial_report.json` | Provenance adversarial test report | 9367 | 2026-07-25 | `01d918fec417527240eeec0d2a11e776f98e66a3bddc390495e3f7e1c62b16f7` |

---

## 6. model-diagnostic-tool — LLM weight diagnostic and training config generation

Project root: `/Users/david/Projects/model-diagnostic-tool`

### 6.1 Diagnostic report (claude-yolo-vibes-v4-dpo)

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/model-diagnostic-tool/reports/yolo-v4-dpo/report.json` | Full diagnostic report (7.6B params, 28 layers, overall capability 0.81; importance + representational phases OOM'd on 15GB GPU) | 63376 | 2026-08-19 | `8b5905ddb577031144c1b52a5a0279d65de4291cc23226ec88185dfb883c7b7f` |

### 6.2 Generated training configs (LoRA-SFT regime recommendation)

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/model-diagnostic-tool/reports/yolo-v4-dpo/axolotl_config.yml` | Axolotl YAML (LoRA r=16, alpha=32, lr=2e-4, 3 epochs, layers 9-27) | 1587 | 2026-08-19 | `c1fc7dd975cc44655d6c70346cab8145ef6152f4dbba00c924f9bd9981890550` |
| `/Users/david/Projects/model-diagnostic-tool/reports/yolo-v4-dpo/peft_config.json` | PEFT LoraConfig JSON (r=16, alpha=32, target q/k/v/o_proj, layers_to_transform 9-27) | 2685 | 2026-08-19 | `899145d11d8637f8f4088e6547d93d3c1634e6cf8a07cb49348786a10a5d9e9d` |
| `/Users/david/Projects/model-diagnostic-tool/reports/yolo-v4-dpo/unsloth_train.py` | Unsloth training script (generated) | 2294 | 2026-08-19 | `5f96805ff846af3698e04119ffaeabc51e1aa1dbd00824c663a417e377655f1b` |

### 6.3 Research synthesis

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/model-diagnostic-tool/research/RESEARCH_SYNTHESIS.md` | Literature review (CKA, ROME/MEMIT, EWC, LoRA Learns Less, DoRA, rsLoRA, HELM, DPO) | 12900 | 2026-08-18 | `54e7ae881e20f891a02b0525c234b324127948c9ad06d8b0094ac8bb3ce7474f` |

---

## 7. speculator-research — Speculative decoding benchmark (Phase 3)

Project root: `/Users/david/Projects/speculator-research`

### 7.1 Phase 3 grid results (PROXY-3090-24G)

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/speculator-research/phase3/a1_grid_results.json` | S-inflection grid results (5x5 batch/ISL, spec on/off, 50 prompts/cell, vLLM 0.10.2, Qwen2.5-7B FP16) | 20116 | 2026-09-05 | `88f3a2fb840a4776d47296b6fca3f565d7f161f8caa75ecbaf77c8673896fc3a` |
| `/Users/david/Projects/speculator-research/phase3/S_INFLECTION_3090.md` | S-inflection summary (peak speedup 1.258x at B=1 ISL=2048; disable spec when B>=8) | 1456 | 2026-09-05 | `8fe2ef733cbab697a54c2049828751923a91571827194c5f5eac4c5953b4b59f` |
| `/Users/david/Projects/speculator-research/PHASE3_RESULTS.md` | Phase 3 results narrative | 11462 | 2026-09-05 | `ce57917e976b061cdb05c63202fac13d3875f3536b151fa15dc3848daf1b6a38` |
| `/Users/david/Projects/speculator-research/phase3/LOG.md` | Phase 3 execution log | 83435 | 2026-09-05 | `9d5cebfca9099cf8a3c5ab1bffb164ea69d7d2bac35bd6ddac6cef27698f1789` |

---

## 8. claude-yolo-v5-doc — Nemotron-Nano-9B-v2 training docs (GB10)

Project root: `/Users/david/Projects/claude-yolo-v5-doc`

### 8.1 Results and docs

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/claude-yolo-v5-doc/results/summary.json` | Results summary (base 76.2% pass@1, 125/164; SFT null — checkpoint lost to /dev/shm; DPO pending) | 1099 | 2026-08-16 | `19b3b8827d328e5efa5a16456ea9dce157f66622c381d81eeba463d6d8eef4ab` |
| `/Users/david/Projects/claude-yolo-v5-doc/TRAINING.md` | Training documentation (GB10, transformers 5.16.0.dev0) | 4006 | 2026-08-16 | `26f370b0952e1e683f391fe5bf722672058975dd09a23c4caab96083aff95a2d` |
| `/Users/david/Projects/claude-yolo-v5-doc/EVALUATION.md` | Evaluation methodology | 6527 | 2026-08-17 | `ac28f450919382c4a1e59ea78272863ee9f6d7353485acc738d7d9bf3a10edc9` |

### 8.2 Trainer and eval scripts

| path | type | bytes | mtime | sha256 |
| --- | --- | --- | --- | --- |
| `/Users/david/Projects/claude-yolo-v5-doc/scripts/train_sft_9b_v2.py` | SFT v2 trainer (Nemotron-Nano-9B-v2, BF16, HF push) | 3716 | 2026-08-16 | `ca12d960b2918b9f9b5df47114a45a6b425cee743182c6c67f21746fd5bc58e0` |
| `/Users/david/Projects/claude-yolo-v5-doc/scripts/train_dpo_9b.py` | DPO trainer (9B) | 5589 | 2026-08-16 | `e87b235fcbfb4ce48379a3b55682a5365d76b1ea7ae1530a0db2824c7ff570cb` |
| `/Users/david/Projects/claude-yolo-v5-doc/scripts/eval_9b.py` | HumanEval evaluator (9B, 2048 tokens, batch_size=2) | 5410 | 2026-08-16 | `b57d169397e4982a83be8529c453b7ae46c643ebbeb8517cc84727857549660a` |

### 8.3 Negative findings for v5-doc

The following v5-doc directories exist but are empty (no artifacts):
- `/Users/david/Projects/claude-yolo-v5-doc/eval-results/` — empty
- `/Users/david/Projects/claude-yolo-v5-doc/model-configs/` — empty
- `/Users/david/Projects/claude-yolo-v5-doc/logs/` — empty

The SFT checkpoint was lost to `/dev/shm` clearing on the GB10 host; no
local weights or configs survive in this tree. This is recorded in
`results/summary.json` as `"sft": {"pass_at_1": null, "notes": "First SFT
run completed but checkpoint lost due to /dev/shm clearing"}`.

---

## 9. Negative findings — projects scanned with no usable ML artifacts

The following projects under `/Users/david/Projects/` were scanned but
contained no usable trainer/config/log artifacts:

| Project | Reason |
| --- | --- |
| `peft` | Upstream fork of `huggingface/peft`. No local artifacts. |
| `trl` | Upstream clone of `huggingface/trl`. No local artifacts. |
| `transformers` | Upstream fork of `huggingface/transformers`. No local artifacts (only `tests/fixtures/config.json` test fixture). |
| `roboflow-inference` | Upstream fork of `roboflow/inference`. No local artifacts. |
| `roboflow-inference-manager` | PR/research tracking project. No ML artifacts. |
| `mcp-inference-gateway` | MCP gateway server. No ML artifacts. |
| `learning-machine` | Setup scripts only (`first-boot.sh`, `setup.sh`, `update-models.sh`). No trainer/config/log artifacts. |
| `heartland-factory` | Trust/security documentation. No ML artifacts. |
| `jarvis-word` | Cognitive graph tooling. No ML artifacts. |
| `mcfamily` | Python package + client. No ML artifacts. |
| `mcfamily-server` | Server logs only. No ML artifacts. |
| `infoscanner` | Code analyzer. No ML artifacts. |
| `parallax` | No ML artifacts. |
| `claude-local` | Local model replica. No trainer/config artifacts. |
| `grokhack` | GrokHack wrapper. No ML artifacts. |
| `local-operator` | Agent operator. No ML artifacts (only `benchmark/reports/baseline_full_run.log` which is an agent benchmark, not ML training). |
| `trajectory-os` | No ML artifacts. |
| `trustcard` | MCP security tooling. No ML artifacts. |
| `hermes-agent` | Agent framework. No ML artifacts. |
| `repo-archaeologist` | No ML artifacts. |
| `cvconform` | Pre-commit config only. No ML artifacts. |
| `dependency-intelligence` | Config only. No ML artifacts. |
| `nevernote` | RAG index. No ML artifacts. |
| `gdrive-sync` | Sync tooling. No ML artifacts. |
| `lan-vault` | Blockchain archive. No ML artifacts. |
| `freespace-reborn` | No ML artifacts. |
| `test-vectors` | No ML artifacts. |
| `go` / `go-workspace` | Go workspace. No ML artifacts. |
| `X-MaC` | macOS tools. No ML artifacts. |
| `aafp` / `aafp-go` / `AAFP-research` | AAFP transport/research. No ML artifacts. |
| `ironclad` | Signing library. No ML artifacts. |
| `aa-coding-index` | No ML artifacts. |
| `Snippets` | No ML artifacts. |
| `OpenHands` | No ML artifacts. |
| `claude-code` | No ML artifacts. |
| `devin-router` | No ML artifacts. |
| `slack_recon` / `wf_recon` / `webfuzz` | Recon/fuzzing. No ML artifacts. |
| `nuclei-templates` | Security templates. No ML artifacts. |
| `p350-bios-hack` | BIOS hack. No ML artifacts. |
| `mcfamily-windows.zip` | Archive. Not scanned (zip file, not a project tree). |

---

## Commands used to build this index

```bash
# 1. Discover candidate artifacts (trainer configs, logs, results)
find /Users/david/Projects -maxdepth 4 \
  \( -name "trainer_state.json" -o -name "training_args.json" \
     -o -name "adapter_config.json" -o -name "generation_config.json" \
     -o -name "config.json" -o -name "training_config.yaml" \
     -o -name "train_config.json" \) \
  -not -path "*/node_modules/*" -not -path "*/.venv/*" \
  -not -path "*/.git/*" -not -path "*/.mypy_cache/*" \
  -not -path "*/.pytest_cache/*" -not -path "*/.ruff_cache/*" \
  -not -path "*/__pycache__/*"

# 2. Discover training logs
find /Users/david/Projects -maxdepth 4 -name "*.log" \
  -not -path "*/.venv/*" -not -path "*/.git/*" \
  | grep -iE "train|epoch|loss|step|log"

# 3. Compute sha256 digests (this session)
cd /Users/david/Projects && shasum -a 256 <path> ...

# 4. Record byte sizes and mtimes
stat -f "%z" -t "%Y-%m-%d" <path> ...
stat -f "%Sm" -t "%Y-%m-%d" <path> ...

# 5. Identify upstream forks (exclude from index)
cd <project> && git remote -v
```

No training was run. No weights were downloaded. No network access was used.
No GPU or Vast operations were performed. No dependencies were added.
