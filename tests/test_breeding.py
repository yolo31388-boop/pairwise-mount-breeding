"""坐骑驯养与繁殖系统 - 红态测试"""
import pytest, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from mount.breeding import BreedingSystem, Mount

class TestBreedGender:
    def test_requires_male_and_female(self):
        bs = BreedingSystem()
        m1 = Mount("m1", "A", gender="male")
        m2 = Mount("m2", "B", gender="male")
        # 两只公的不能繁殖
        try:
            child = bs.breed(m1, m2)
            assert False  # bug2: 没报错
        except ValueError:
            assert True

class TestGeneticVariation:
    def test_offspring_not_exact_average(self):
        bs = BreedingSystem(seed=42)
        m1 = Mount("m1", "A", speed=20.0, stamina=20.0)
        m2 = Mount("m2", "B", gender="female", speed=10.0, stamina=10.0)
        child = bs.breed(m1, m2)
        # 应该有变异，不是精确平均
        assert child.speed != 15.0 or child.stamina != 15.0  # bug1: 精确15.0

class TestSkillInheritance:
    def test_skills_only_from_parents(self):
        bs = BreedingSystem(seed=42)
        m1 = Mount("m1", "A", skills=["dash", "jump"])
        m2 = Mount("m2", "B", gender="female", skills=["dash", "swim"])
        child = bs.breed(m1, m2)
        for s in child.skills:
            assert s in ["dash", "jump", "swim"]  # bug3: 可能出现父母都不会的技能

class TestTamingExpCurve:
    def test_taming_exp_increases_with_level(self):
        bs = BreedingSystem()
        e1 = bs.get_taming_exp(1)
        e10 = bs.get_taming_exp(10)
        assert e10 > e1  # bug4: 都是100

class TestInbreeding:
    def test_inbreeding_detected(self):
        bs = BreedingSystem()
        m1 = Mount("m1", "A", lineage=["g1", "g2"])
        m2 = Mount("m2", "B", gender="female", lineage=["g1", "g3"])  # 共享g1
        assert bs.check_inbreeding(m1, m2) == True  # bug5: 返回False

class TestMaleCooldown:
    def test_male_has_breeding_cooldown(self):
        bs = BreedingSystem()
        bs.male_cooldown["m1"] = 100.0
        assert bs.can_breed_male("m1", 50.0) == False  # bug6: 返回True
        assert bs.can_breed_male("m1", 150.0) == True
