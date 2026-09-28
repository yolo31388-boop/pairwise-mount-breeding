"""坐骑驯养与繁殖系统 - 含6个bug"""
import random
from dataclasses import dataclass, field

@dataclass
class Mount:
    mid: str
    name: str
    gender: str = "male"  # bug: 不检查性别
    speed: float = 10.0
    stamina: float = 10.0
    genes: dict = field(default_factory=dict)  # 显性/隐性基因
    skills: list = field(default_factory=list)
    taming_progress: float = 0.0
    level: int = 1
    lineage: list = field(default_factory=list)  # 三代血统

class BreedingSystem:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.male_cooldown: dict[str, float] = {}
        self.female_cooldown: dict[str, float] = {}

    def breed(self, m1: Mount, m2: Mount) -> Mount:
        # bug1: 属性直接平均
        # bug2: 不检查性别
        child = Mount(f"child_{self.rng.randint(1000,9999)}", "child")
        child.speed = (m1.speed + m2.speed) / 2
        child.stamina = (m1.stamina + m2.stamina) / 2
        # bug3: 技能随机遗传
        all_skills = list(set(m1.skills + m2.skills))
        child.skills = random.sample(all_skills, min(2, len(all_skills))) if all_skills else []
        child.lineage = [m1.mid, m2.mid]
        return child

    def get_taming_exp(self, level: int) -> float:
        # bug4: 线性经验
        return 100.0

    def check_inbreeding(self, m1: Mount, m2: Mount) -> bool:
        # bug5: 不检查近亲
        return False

    def can_breed_male(self, mid: str, current_time: float) -> bool:
        # bug6: 公坐骑无冷却
        return True
