"""坐骑驯养与繁殖系统"""
import random
from dataclasses import dataclass, field

MALE_COOLDOWN = 3600.0       # 公坐骑繁殖冷却(秒)
FEMALE_COOLDOWN = 86400.0    # 母坐骑繁殖冷却(秒)
MALE_DAILY_LIMIT = 3         # 公坐骑每日配种上限
DAY_SECONDS = 86400.0
MUTATION_RATE = 0.08         # 属性变异幅度
ENV_FACTOR_RANGE = (0.95, 1.05)  # 环境因子
INBREEDING_STAT_PENALTY = 0.85   # 近亲繁殖属性惩罚
INBREEDING_DEFECT_CHANCE = 0.3   # 近亲繁殖缺陷概率
DEFECTS = ["weak_legs", "timid", "frail"]
# 基因型对属性的加成: 显性纯合 > 杂合 > 隐性纯合
GENOTYPE_BONUS = {"AA": 1.15, "Aa": 1.0, "aa": 0.85}
LINEAGE_GENERATIONS = 3      # 记录三代血统


@dataclass
class Mount:
    mid: str
    name: str
    gender: str = "male"
    speed: float = 10.0
    stamina: float = 10.0
    genes: dict = field(default_factory=dict)   # {"speed": ("A","a"), ...}
    skills: list = field(default_factory=list)
    taming_progress: float = 0.0
    level: int = 1
    lineage: list = field(default_factory=list)  # 三代血统(祖先mid)
    defects: list = field(default_factory=list)


class BreedingSystem:
    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)
        self.male_cooldown: dict[str, float] = {}    # mid -> 可再次繁殖的时间
        self.female_cooldown: dict[str, float] = {}
        self.male_daily_count: dict[str, list[float]] = {}  # mid -> 当天配种时间戳
        self.pairings: list[tuple[str, str, float]] = []    # 配对记录

    # ---------- 繁殖 ----------

    def breed(self, m1: Mount, m2: Mount, current_time: float = 0.0) -> Mount:
        if m1.gender == m2.gender:
            raise ValueError(f"繁殖需要一公一母, 实际: {m1.gender} + {m2.gender}")
        sire, dam = (m1, m2) if m1.gender == "male" else (m2, m1)
        if not self.can_breed_male(sire.mid, current_time):
            raise ValueError(f"公坐骑 {sire.mid} 在冷却中或已达每日配种上限")
        if not self.can_breed_female(dam.mid, current_time):
            raise ValueError(f"母坐骑 {dam.mid} 在繁殖冷却中")

        inbred = self.check_inbreeding(m1, m2)
        child = Mount(f"child_{self.rng.randint(1000, 9999)}", "child")
        child.gender = self.rng.choice(["male", "female"])

        # 属性 = 父母基因遗传 + 随机变异 + 环境因子
        child.genes = self._inherit_genes(sire, dam)
        env = self.rng.uniform(*ENV_FACTOR_RANGE)
        child.speed = self._inherit_stat(sire.speed, dam.speed,
                                         child.genes.get("speed"), env)
        child.stamina = self._inherit_stat(sire.stamina, dam.stamina,
                                           child.genes.get("stamina"), env)
        if inbred:
            child.speed *= INBREEDING_STAT_PENALTY
            child.stamina *= INBREEDING_STAT_PENALTY
            if self.rng.random() < INBREEDING_DEFECT_CHANCE:
                child.defects.append(self.rng.choice(DEFECTS))

        # 技能只从父母技能池按概率继承
        child.skills = self._inherit_skills(sire, dam)
        child.lineage = self._build_lineage(sire, dam)

        self._record_pairing(sire, dam, current_time)
        return child

    def _inherit_genes(self, sire: Mount, dam: Mount) -> dict:
        """每个基因座从父母各取一个等位基因(显性A/隐性a)。"""
        loci = set(sire.genes) | set(dam.genes) | {"speed", "stamina"}
        genes = {}
        for locus in loci:
            s = sire.genes.get(locus, ("A", "a"))
            d = dam.genes.get(locus, ("A", "a"))
            allele_s = self.rng.choice(s)
            allele_d = self.rng.choice(d)
            genes[locus] = tuple(sorted((allele_s, allele_d), reverse=True))
        return genes

    def _inherit_stat(self, s_val: float, d_val: float,
                      genotype: tuple, env: float) -> float:
        base = (s_val + d_val) / 2
        bonus = GENOTYPE_BONUS.get("".join(genotype), 1.0) if genotype else 1.0
        mutation = self.rng.uniform(-MUTATION_RATE, MUTATION_RATE)
        return max(0.1, base * bonus * env * (1 + mutation))

    def _inherit_skills(self, sire: Mount, dam: Mount) -> list:
        """双方都会的技能大概率遗传, 单方会的小概率遗传, 不会凭空出现。"""
        pool = set(sire.skills) | set(dam.skills)
        skills = []
        for skill in sorted(pool):
            prob = 0.75 if skill in sire.skills and skill in dam.skills else 0.4
            if self.rng.random() < prob:
                skills.append(skill)
        return skills

    def _build_lineage(self, sire: Mount, dam: Mount) -> list:
        """记录三代血统: 父母 + 祖父母 + 曾祖父母。"""
        lineage = [sire.mid, dam.mid]
        for parent in (sire, dam):
            lineage.extend(parent.lineage)
        # 父母1代 + 祖辈2代 + 曾祖辈4代, 去重保序
        seen, result = set(), []
        for mid in lineage:
            if mid not in seen:
                seen.add(mid)
                result.append(mid)
        return result[: 2 + 4 + 8]

    def _record_pairing(self, sire: Mount, dam: Mount, current_time: float) -> None:
        self.pairings.append((sire.mid, dam.mid, current_time))
        self.male_cooldown[sire.mid] = current_time + MALE_COOLDOWN
        self.female_cooldown[dam.mid] = current_time + FEMALE_COOLDOWN
        self.male_daily_count.setdefault(sire.mid, []).append(current_time)

    # ---------- 驯养 ----------

    def get_taming_exp(self, level: int) -> float:
        """驯养经验按等级曲线递增。"""
        return 100.0 * level ** 1.5

    # ---------- 血统 ----------

    def check_inbreeding(self, m1: Mount, m2: Mount) -> bool:
        """三代内有共同祖先(含一方是另一方祖先)即为近亲。"""
        kin1 = {m1.mid} | set(m1.lineage)
        kin2 = {m2.mid} | set(m2.lineage)
        return bool(kin1 & kin2)

    # ---------- 冷却 ----------

    def can_breed_male(self, mid: str, current_time: float) -> bool:
        if current_time < self.male_cooldown.get(mid, 0.0):
            return False
        day_start = current_time - DAY_SECONDS
        recent = [t for t in self.male_daily_count.get(mid, []) if t > day_start]
        return len(recent) < MALE_DAILY_LIMIT

    def can_breed_female(self, mid: str, current_time: float) -> bool:
        return current_time >= self.female_cooldown.get(mid, 0.0)
