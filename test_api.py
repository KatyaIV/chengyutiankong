import unittest
import json
import os
from app import app, HIGHSCORE_FILE, HighscoreManager


class TestIdiomGameAPI(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        # 备份并在测试中重置最高分
        self.original_high_score = HighscoreManager.load_high_score()
        HighscoreManager.save_high_score(0)

    def tearDown(self):
        # 恢复初始最高分
        HighscoreManager.save_high_score(self.original_high_score)

    def test_get_info(self):
        """测试 GET /api/info 获取最高分和基本配置"""
        res = self.client.get("/api/info")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["high_score"], 0)
        self.assertEqual(data["time_limit"], 15)
        self.assertEqual(data["initial_lives"], 3)

    def test_start_game(self):
        """测试 POST /api/start 重置并获取第1题"""
        res = self.client.post("/api/start")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["score"], 0)
        self.assertEqual(data["lives"], 3)
        self.assertFalse(data["game_over"])
        self.assertIn("question", data)
        self.assertIn("display_word", data["question"])
        self.assertIn("correct_char", data["question"])
        self.assertIn("(?)", data["question"]["display_word"])

    def test_submit_correct_answer(self):
        """测试提交正确答案：得分增加、生命不扣，并下发下一题"""
        start_res = self.client.post("/api/start")
        q = start_res.get_json()["question"]
        correct_char = q["correct_char"]

        sub_res = self.client.post(
            "/api/submit",
            data=json.dumps({"answer": correct_char, "timeout": False}),
            content_type="application/json"
        )
        self.assertEqual(sub_res.status_code, 200)
        data = sub_res.get_json()
        self.assertTrue(data["correct"])
        self.assertEqual(data["score"], 1)
        self.assertEqual(data["lives"], 3)
        self.assertFalse(data["game_over"])
        self.assertTrue(data["new_high_score"])  # 从 0 变成 1，刷新最高分
        self.assertEqual(data["high_score"], 1)
        self.assertIsNotNone(data["question"])

    def test_submit_wrong_answer(self):
        """测试提交错误答案：生命扣1，分数不变，返回正确字及下一题"""
        start_res = self.client.post("/api/start")
        q = start_res.get_json()["question"]
        correct_char = q["correct_char"]
        wrong_char = "错" if correct_char != "错" else "误"

        sub_res = self.client.post(
            "/api/submit",
            data=json.dumps({"answer": wrong_char, "timeout": False}),
            content_type="application/json"
        )
        self.assertEqual(sub_res.status_code, 200)
        data = sub_res.get_json()
        self.assertFalse(data["correct"])
        self.assertEqual(data["correct_char"], correct_char)
        self.assertEqual(data["score"], 0)
        self.assertEqual(data["lives"], 2)
        self.assertFalse(data["game_over"])
        self.assertIsNotNone(data["question"])

    def test_submit_timeout(self):
        """测试超时情况：生命扣1，分数不变"""
        self.client.post("/api/start")
        sub_res = self.client.post(
            "/api/submit",
            data=json.dumps({"answer": "", "timeout": True}),
            content_type="application/json"
        )
        self.assertEqual(sub_res.status_code, 200)
        data = sub_res.get_json()
        self.assertFalse(data["correct"])
        self.assertEqual(data["lives"], 2)
        self.assertEqual(data["score"], 0)

    def test_game_over_flow(self):
        """测试扣完3点生命后触发游戏结束，且不再下发下一题"""
        self.client.post("/api/start")

        # 连续错 3 次
        for i in range(3):
            sub_res = self.client.post(
                "/api/submit",
                data=json.dumps({"answer": "错", "timeout": False}),
                content_type="application/json"
            )
            data = sub_res.get_json()
            if i < 2:
                self.assertFalse(data["game_over"])
                self.assertIsNotNone(data["question"])
            else:
                self.assertTrue(data["game_over"])
                self.assertEqual(data["lives"], 0)
                self.assertIsNone(data["question"])

    def test_highscore_persistence(self):
        """测试最高分持久化写入 highscore.json 文件"""
        HighscoreManager.save_high_score(5)
        self.assertEqual(HighscoreManager.load_high_score(), 5)

        # 验证文件真实存在且内容匹配
        self.assertTrue(os.path.exists(HIGHSCORE_FILE))
        with open(HIGHSCORE_FILE, "r", encoding="utf-8") as f:
            disk_data = json.load(f)
            self.assertEqual(disk_data.get("high_score"), 5)

    def test_submit_without_active_question(self):
        """测试未开局直接提交报错 400"""
        self.client.post("/api/start")
        # 正常提交一次
        self.client.post(
            "/api/submit",
            data=json.dumps({"answer": "错"}),
            content_type="application/json"
        )
        # 此时已经自动下发新题目，现在强行让 current_question 置空
        from app import game
        game.current_question = None

        res = self.client.post(
            "/api/submit",
            data=json.dumps({"answer": "字"}),
            content_type="application/json"
        )
        self.assertEqual(res.status_code, 400)
        self.assertEqual(res.get_json()["status"], "error")

    def test_static_index_route(self):
        """测试根路径 / 成功返回 index.html 网页"""
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"\xe6\x88\x90\xe8\xaf\xad\xe5\xa4\xa7\xe9\x97\xaf\xe5\x85\xb3", res.data)  # '成语大闯关'

    def test_static_assets_available(self):
        """测试静态资源 style.css 与 main.js 可访问"""
        res_css = self.client.get("/static/style.css")
        self.assertEqual(res_css.status_code, 200)
        res_js = self.client.get("/static/main.js")
        self.assertEqual(res_js.status_code, 200)


if __name__ == "__main__":
    unittest.main()
