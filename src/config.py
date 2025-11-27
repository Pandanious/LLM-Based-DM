from pathlib import Path


project_root = Path(__file__).resolve().parents[1]
model_dir = project_root / "model"
#model_path = model_dir / "model.gguf" Google Gemma Model not very good
#model_path = model_dir / "qwen2.5-coder-7b-instruct-q6_k.gguf"
model_path = model_dir / "Meta-Llama-3.1-8B-Instruct-Q6_K_L.gguf"
SAVES_DIR = project_root / "saves"
SAVES_DIR.mkdir(exist_ok=True)



max_CTX = 4096  ## max memory -> ~3000 words.
cpu_threads = 12 
gpu_layers = 24
default_temp = 0.7 ## I guess how bohemiean it is?
default_max_tokens = 600
