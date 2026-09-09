import unittest
import os
from game_logic import IdiomGame


class TestIdiomGame(unittest.TestCase):
    def setUp(self):
        self.game = IdiomGame()

    def test_init_state(self):
        """测试初始游戏状态"""
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(self.game.time_limit, 15)
        self.assertEqual(len(self.game.used_idioms), 0)
        self.assertFalse(self.game.is_game_over())
        self.assertGreater(len(self.game.idiom_pool), 0)

    def test_next_question_format(self):
        """测试题目生成格式与字段"""
        q = self.game.next_question()
        self.assertIsNotNone(q)
        self.assertIn("display_word", q)
        self.assertIn("missing_index", q)
        self.assertIn("correct_char", q)
        self.assertIn("full_word", q)
        self.assertIn("time_limit", q)

        # 校验挖空与字符对应关系
        missing_index = q["missing_index"]
        self.assertEqual(q["full_word"][missing_index], q["correct_char"])
        self.assertIn("(?)", q["display_word"])
        self.assertEqual(q["time_limit"], 15)
        self.assertEqual(len(self.game.used_idioms), 1)

    def test_submit_correct_answer(self):
        """测试提交正确答案：加1分，生命不扣"""
        q = self.game.next_question()
        correct_char = q["correct_char"]

        res = self.game.submit_answer(user_input=correct_char, is_timeout=False)
        self.assertTrue(res["correct"])
        self.assertEqual(res["score"], 1)
        self.assertEqual(res["lives"], 3)
        self.assertFalse(res["game_over"])
        self.assertEqual(self.game.score, 1)
        self.assertEqual(self.game.lives, 3)

    def test_submit_wrong_answer(self):
        """测试提交错误答案：扣1滴血，分数不变，返回正确字"""
        q = self.game.next_question()
        correct_char = q["correct_char"]
        wrong_char = "错" if correct_char != "错" else "误"

        res = self.game.submit_answer(user_input=wrong_char, is_timeout=False)
        self.assertFalse(res["correct"])
        self.assertEqual(res["correct_char"], correct_char)
        self.assertEqual(res["score"], 0)
        self.assertEqual(res["lives"], 2)
        self.assertFalse(res["game_over"])
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.lives, 2)

    def test_submit_timeout(self):
        """测试超时情况：扣1滴血，分数不变"""
        q = self.game.next_question()
        correct_char = q["correct_char"]

        res = self.game.submit_answer(user_input="", is_timeout=True)
        self.assertFalse(res["correct"])
        self.assertEqual(res["correct_char"], correct_char)
        self.assertEqual(res["score"], 0)
        self.assertEqual(res["lives"], 2)
        self.assertFalse(res["game_over"])

    def test_game_over_trigger(self):
        """测试生命值耗尽触发游戏结束"""
        for i in range(3):
            self.game.next_question()
            res = self.game.submit_answer(user_input="错")
            expected_lives = 2 - i
            self.assertEqual(res["lives"], expected_lives)
            if i < 2:
                self.assertFalse(res["game_over"])
                self.assertFalse(self.game.is_game_over())
            else:
                self.assertTrue(res["game_over"])
                self.assertTrue(self.game.is_game_over())

    def test_non_repetition(self):
        """测试单局内不重复抽取成语"""
        extracted = []
        for _ in range(50):
            q = self.game.next_question()
            if q is None:
                break
            extracted.append(q["full_word"])
            self.game.submit_answer(q["correct_char"])

        # 检查抽取的成语无重复
        self.assertEqual(len(extracted), len(set(extracted)))
        self.assertEqual(len(self.game.used_idioms), len(extracted))

    def test_reset(self):
        """测试游戏重置恢复状态"""
        q = self.game.next_question()
        self.game.submit_answer("错")
        self.assertEqual(self.game.lives, 2)
        self.assertEqual(len(self.game.used_idioms), 1)

        self.game.reset()
        self.assertEqual(self.game.score, 0)
        self.assertEqual(self.game.lives, 3)
        self.assertEqual(len(self.game.used_idioms), 0)
        self.assertIsNone(self.game.current_question)

    def test_double_submission_prevented(self):
        """测试同一道题不能重复提交作答"""
        self.game.next_question()
        self.game.submit_answer("任何字")
        with self.assertRaises(RuntimeError):
            self.game.submit_answer("任何字")


if __name__ == "__main__":
    unittest.main()
