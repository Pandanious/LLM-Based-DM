from pathlib import Path


project_root = Path(__file__).resolve().parents[1]
model_dir = project_root / "model"
model_path = model_dir / "model.gguf"
SAVES_DIR = project_root / "saves"
SAVES_DIR.mkdir(exist_ok=True)



max_CTX = 4096  ## max memory -> ~3000 words.
cpu_threads = 8 
gpu_layers = 16
default_temp = 0.7 ## I guess how bohemiean it is?
default_max_tokens = 300
