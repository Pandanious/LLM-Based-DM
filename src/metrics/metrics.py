from __future__ import annotations
import os
import threading
from datetime import datetime
import psutil
import atexit
import time 
from contextlib import contextmanager
from dataclasses import asdict,dataclass
from typing import Dict,Optional
import json
from pathlib import Path


@dataclass
class llm_gen_stat():
    count = 0
    errors = 0
    total_time_seconds = 0.0
    max_time_seconds = 0.0
    last_time_seconds = 0.0
    peak_memory_GB = None
    last_memory_GB = None
    last_delta_memory_GB = None


class metricsreg():
    # metrics registry to store items from llm_gen_stat dataclass

    def __init__(self):
        self.lock = threading.Lock()                        
        self.generations: Dict[str, llm_gen_stat] = {}
        self.counters: Dict[str,int] = {}
    
    def recording(self,name,duration_s,success,memory_gb,mem_delta_gb):
        with self.lock:
            stats = self.generations.setdefault(name,llm_gen_stat())
            stats.count += 1
            if not success:
                stats.errors += 1
            stats.last_time_seconds = duration_s
            stats.total_time_seconds += duration_s
            stats.max_time_seconds = max(stats.max_time_seconds,duration_s)
            if memory_gb is not None:
                stats.last_memory_GB = memory_gb
                if stats.peak_memory_GB is None or memory_gb > stats.peak_memory_GB:
                    stats.peak_memory_GB = memory_gb
            if mem_delta_gb is not None:
                stats.last_delta_memory_GB = mem_delta_gb   
    
    def increment(self,name,amount=1,):
        with self.lock:
            self.counters[name] = self.counters.get(name,0)+amount

    def snapshot(self):
        with self.lock:
            gen = {k: asdict(v) for k,v in self.generations.items()}
            counters = dict(self.counters)
        return {"Generations":gen,"Counters":counters,"Process Memory in GB": read_process_memory()}
    ########## THIS BIT IS NOT WORKING !! WHY ?? ###############     
    def write_snapshot(self, path=None):
        base_dir = Path(path) if path else Path(__file__).resolve().parent
        base_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        target = base_dir / f"metric_snapshot_{ts}.json"
        target.write_text(json.dumps(self.snapshot(), indent=2))
        return target

    def exit_writer(self, path=None):
        def _save_on_exit():
            self.write_snapshot(path)
        atexit.register(_save_on_exit)
        

    
def read_process_memory():
    rss_bytes = psutil.Process(os.getpid()).memory_info().rss
    mem_gb = rss_bytes / (1024**3)
    return round(mem_gb,3)




@contextmanager
def track_gen(name):
    # Time for gen, memory before and after.
    start_time = time.perf_counter()
    start_mem = read_process_memory()
    success = True
    try:
        yield
    except Exception:
        success = False
        raise
    finally:
        duration = time.perf_counter() - start_time
        end_mem = read_process_memory()
        mem_delta = None

        if start_mem is not None and end_mem is not None:
            mem_delta = round(end_mem - start_mem,3)

        metrics.recording(name=name, duration_s=round(duration,4),success=success,memory_gb=end_mem,mem_delta_gb=mem_delta)

metrics = metricsreg()


    





 
