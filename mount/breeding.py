"""坐骑驯养与繁殖系统"""
import random
from dataclasses import dataclass, field

MALE_COOLDOWN = 100.0       # 公坐骑繁殖冷却时长（秒）
FEMALE_COOLDOWN = 100.0     # 母坐骑繁殖冷却时长（秒）
MALE_DAILY_LIMIT = 3        # 公坐骑每日配种上限
SECONDS_PER_DAY = 86400.0
LINEAGE_SIZE = 14           # 三代血统：2父母 + 4祖辈 + 8曾祖辈
INBREEDING_PENALTY = 0.9    # 近亲繁殖属性惩罚系数
DEFECT_CHANCE = 0.3         # 近亲繁殖缺陷概率
MUTATION_RATE = 0.05        # 随机变异幅度（相对于基础值）
ENVIRONMENT_RATE = 0.02     # 环境因子幅度（相对于基础值）
SKILL_INHERIT_SOLO = 0.5    # 单方拥有的技能遗传概率
SKILL_INHERIT_BOTH = 0.75   # 双方拥有的技能遗传概率


@dataclass
class Mount:
    mid: str
    name: str
    gender: str = "male"
    speed: float = 10.0
    stamina: float = 10.0
    genes: dict = field(default_factory=dict)  # trait -> (allele1, allele2)，数值大者为显性
    skills: list = field(default_factory=list)
    taming_progress: float = 0.0
    level: int = 1
    lineage: list = field(default_factory=list)  # 三代血统
    defects: list = field(default_factory=list)  # 近亲繁殖缺陷


class BreedingSystem:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.male_cooldown: dict[str, float] = {}    # mid -> 可再次繁殖的时间点
        self.female_cooldown: dict[str, float] = {}
        self.male_daily_count: dict[tuple, int] = {}  # (mid, 天数) -> 当日配种次数
        self.pairings: list = []                     # 配对记录 (公mid, 母mid, 后代mid)

    def breed(self, m1: Mount, m2: Mount, current_time: float = 0.0) -> Mount:
        # 性别检查：必须一公一母
        if m1.gender == m2.gender:
            raise ValueError(f"繁殖需要一公一母，当前性别: {m1.gender}/{m2.gender}")
        male, female = (m1, m2) if m1.gender == "male" else (m2, m1)

        # 公坐骑独立冷却 + 每日配种上限
        if not self.can_breed_male(male.mid, current_time):
            raise ValueError(f"公坐骑 {male.mid} 处于冷却期或已达每日配种上限")
        if current_time < self.female_cooldown.get(female.mid, 0.0):
            raise ValueError(f"母坐骑 {female.mid} 处于繁殖冷却期")

        inbred = self.check_inbreeding(m1, m2)

        child = Mount(f"child_{self.rng.randint(1000, 9999)}", "child")
        child.gender = self.rng.choice(["male", "female"])

        # 属性 = 父母基因遗传 + 随机变异 + 环境因子
        child.speed = self._inherit_attr(m1, m2, "speed", child)
        child.stamina = self._inherit_attr(m1, m2, "stamina", child)

        # 近亲繁殖：属性惩罚 + 缺陷概率
        if inbred:
            child.speed *= INBREEDING_PENALTY
            child.stamina *= INBREEDING_PENALTY
            if self.rng.random() < DEFECT_CHANCE:
                child.defects.append("congenital_weakness")

        # 技能按父母技能池概率继承，不会凭空出现
        child.skills = self._inherit_skills(m1, m2)

        # 记录三代血统
        child.lineage = ([m1.mid, m2.mid] + list(m1.lineage) + list(m2.lineage))[:LINEAGE_SIZE]

        # 记录配对并更新冷却/次数
        self.pairings.append((male.mid, female.mid, child.mid))
        self.male_cooldown[male.mid] = current_time + MALE_COOLDOWN
        self.female_cooldown[female.mid] = current_time + FEMALE_COOLDOWN
        day_key = (male.mid, int(current_time // SECONDS_PER_DAY))
        self.male_daily_count[day_key] = self.male_daily_count.get(day_key, 0) + 1
        return child

    def _inherit_attr(self, m1: Mount, m2: Mount, trait: str, child: Mount) -> float:
        g1 = m1.genes.get(trait)
        g2 = m2.genes.get(trait)
        if g1 and g2:
            # 各从父母随机继承一个等位基因，显性（数值大）基因决定表现型
            allele1 = self.rng.choice(tuple(g1))
            allele2 = self.rng.choice(tuple(g2))
            child.genes[trait] = (allele1, allele2)
            base = max(allele1, allele2)
        else:
            # 无基因记录时以父母表现型均值为基础
            base = (getattr(m1, trait) + getattr(m2, trait)) / 2
        mutation = self.rng.gauss(0.0, MUTATION_RATE * base)
        environment = self.rng.uniform(-ENVIRONMENT_RATE, ENVIRONMENT_RATE) * base
        return max(0.0, base + mutation + environment)

    def _inherit_skills(self, m1: Mount, m2: Mount) -> list:
        skills = []
        for skill in dict.fromkeys(list(m1.skills) + list(m2.skills)):
            prob = SKILL_INHERIT_BOTH if skill in m1.skills and skill in m2.skills else SKILL_INHERIT_SOLO
            if self.rng.random() < prob:
                skills.append(skill)
        return skills

    def get_taming_exp(self, level: int) -> float:
        # 驯养经验按等级曲线递增
        return 100.0 * level ** 1.5

    def check_inbreeding(self, m1: Mount, m2: Mount) -> bool:
        # 三代血统内有共同祖先，或一方是另一方的直系血亲
        if m1.mid == m2.mid:
            return True
        if m1.mid in m2.lineage or m2.mid in m1.lineage:
            return True
        return bool(set(m1.lineage) & set(m2.lineage))

    def can_breed_male(self, mid: str, current_time: float) -> bool:
        # 公坐骑有独立繁殖冷却和每日配种上限
        if current_time < self.male_cooldown.get(mid, 0.0):
            return False
        day_key = (mid, int(current_time // SECONDS_PER_DAY))
        return self.male_daily_count.get(day_key, 0) < MALE_DAILY_LIMIT
