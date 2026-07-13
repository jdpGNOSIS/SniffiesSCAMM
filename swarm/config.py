import os
from dataclasses import dataclass, field


@dataclass
class SwarmConfig:
    max_agents: int = 50
    default_timeout: int = 120
    agent_retry_limit: int = 3
    log_level: str = "INFO"
    results_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(__file__), "..", "swarm_results"
    ))
    task_history_dir: str = field(default_factory=lambda: os.path.join(
        os.path.dirname(__file__), "..", "swarm_history"
    ))

    def ensure_dirs(self):
        os.makedirs(self.results_dir, exist_ok=True)
        os.makedirs(self.task_history_dir, exist_ok=True)
