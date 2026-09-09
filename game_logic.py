import json
import os
import random
from typing import Dict, Any, Optional, List


class IdiomGame:
    """成语单字填空闯关核心游戏逻辑类（Model 层）"""

    def __init__(self, data_path: str = "idioms.json"):
        """初始化游戏数据与状态

        :param data_path: 成语数据文件路径，默认当前目录下的 idioms.json
        """
        self.data_path = data_path
        self.idiom_pool: List[str] = []
        self._load_idioms()

        # 核心游戏状态
        self.score: int = 0
        self.lives: int = 3
        self.time_limit: int = 15
        self.used_idioms: set = set()

        # 当前进行中的题目缓存
        self.current_question: Optional[Dict[str, Any]] = None

    def _load_idioms(self) -> None:
        """从 JSON 文件加载成语库，支持 list of dict 或 list of str"""
        # 兼容当前目录及脚本所在目录
        candidates = [
            self.data_path,
            os.path.join(os.path.dirname(__file__), self.data_path),
            os.path.join(os.path.dirname(__file__), "idiomso.json")
        ]

        loaded_data = None
        for path in candidates:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        loaded_data = json.load(f)
                    break
                except Exception:
                    continue

        if not loaded_data:
            raise FileNotFoundError(f"未能找到或读取有效的成语库文件，请确认 {self.data_path} 是否存在。")

        # 数据清洗提取纯正成语词条
        self.idiom_pool = []
        seen = set()
        for item in loaded_data:
            word = ""
            if isinstance(item, dict) and "word" in item:
                word = str(item["word"]).strip()
            elif isinstance(item, str):
                word = item.strip()

            if word and word not in seen:
                # 确保是规范成语（全汉字且长度 >= 4）
                if len(word) >= 4 and all('\u4e00' <= c <= '\u9fa5' for c in word):
                    seen.add(word)
                    self.idiom_pool.append(word)

        if not self.idiom_pool:
            raise ValueError("加载到的有效成语词库为空，请检查数据文件。")

    def reset(self) -> None:
        """重置游戏状态（单局重新开始）"""
        self.score = 0
        self.lives = 3
        self.time_limit = 15
        self.used_idioms.clear()
        self.current_question = None

    def is_game_over(self) -> bool:
        """检查游戏是否已结束"""
        return self.lives <= 0

    def next_question(self) -> Optional[Dict[str, Any]]:
        """生成下一道题目

        从未使用过的成语中随机抽取一个，并在随机位置挖空一个汉字。
        :return: 题目字典信息，若词库耗尽则返回 None
        """
        if self.is_game_over():
            raise RuntimeError("游戏已结束，请先调用 reset() 重新开始。")

        # 筛选未出现的成语
        available_idioms = [w for w in self.idiom_pool if w not in self.used_idioms]
        if not available_idioms:
            # 题库在单局内被全部答完的情况
            return None

        # 随机抽取一个成语
        word = random.choice(available_idioms)
        self.used_idioms.add(word)

        # 随机挑选一个字挖空 (0 ~ len(word)-1)
        word_len = len(word)
        missing_index = random.randint(0, word_len - 1)
        correct_char = word[missing_index]
        display_word = f"{word[:missing_index]}(?){word[missing_index + 1:]}"

        question = {
            "display_word": display_word,
            "missing_index": missing_index,
            "correct_char": correct_char,
            "full_word": word,
            "time_limit": self.time_limit
        }
        self.current_question = question
        return question

    def submit_answer(self, user_input: Optional[str], is_timeout: bool = False) -> Dict[str, Any]:
        """提交并校验答案

        :param user_input: 用户填写的汉字
        :param is_timeout: 是否超时（默认 False）
        :return: 校验结果字典
        """
        if self.current_question is None:
            raise RuntimeError("当前没有正在进行中的题目，请先调用 next_question()。")

        correct_char = self.current_question["correct_char"]
        # 清空当前题目缓存，防止同一题重复作答
        self.current_question = None

        # 去除前后空白字符（若传入非空字符串）
        cleaned_input = user_input.strip() if isinstance(user_input, str) else ""

        # 判定答案正误
        if is_timeout or cleaned_input != correct_char:
            self.lives -= 1
            game_over = self.lives <= 0
            return {
                "correct": False,
                "correct_char": correct_char,
                "lives": self.lives,
                "score": self.score,
                "game_over": game_over
            }
        else:
            self.score += 1
            return {
                "correct": True,
                "lives": self.lives,
                "score": self.score,
                "game_over": False
            }

    def get_state(self) -> Dict[str, Any]:
        """获取当前游戏状态摘要"""
        return {
            "score": self.score,
            "lives": self.lives,
            "time_limit": self.time_limit,
            "used_count": len(self.used_idioms),
            "game_over": self.is_game_over()
        }


if __name__ == "__main__":
    print("=" * 40)
    print(" 🎯 成语单字填空 - 核心逻辑试玩 Demo")
    print("=" * 40)

    game = IdiomGame()
    print(f"成语库加载成功，共有 {len(game.idiom_pool)} 条有效成语。")
    print("游戏规则：每题 15 秒，共有 3 条生命，回答正确加 1 分，错误或超时扣 1 滴血。\n")

    round_idx = 1
    while not game.is_game_over():
        q = game.next_question()
        if not q:
            print("恭喜！所有成语已经全部通关！")
            break

        print(f"【第 {round_idx} 题】 请填空：{q['display_word']} （限时 {q['time_limit']} 秒）")
        print("直接按回车或输入答案，输入 'timeout' 模拟超时：")
        user_ans = input("请输入缺少的字: ").strip()

        if user_ans == "timeout":
            res = game.submit_answer(user_input="", is_timeout=True)
            print(f"⏰ 超时！正确答案是: 【{res['correct_char']}】 ({q['full_word']})")
        else:
            res = game.submit_answer(user_input=user_ans)
            if res["correct"]:
                print(f"🎉 回答正确！当前得分: {res['score']}")
            else:
                print(f"❌ 回答错误！正确字是: 【{res['correct_char']}】 ({q['full_word']})")

        print(f"剩余生命: {'❤️' * res['lives'] if res['lives'] > 0 else '💀 0'} | 当前总分: {res['score']}\n")
        round_idx += 1

    print("=" * 40)
    print(f"🎮 游戏结束！最终得分: {game.score}")
    print("=" * 40)
