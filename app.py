import json
import os
from flask import Flask, jsonify, request, send_from_directory
from game_logic import IdiomGame

app = Flask(__name__, static_folder="static", static_url_path="/static")

# 数据文件路径
HIGHSCORE_FILE = os.path.join(os.path.dirname(__file__), "highscore.json")
IDIOMS_FILE = os.path.join(os.path.dirname(__file__), "idioms.json")

# 初始化成语游戏实例
game = IdiomGame(data_path=IDIOMS_FILE)


@app.route("/")
def index():
    """提供主页面访问"""
    return app.send_static_file("index.html")


class HighscoreManager:
    """负责 highscore.json 的持久化读写管理"""

    @staticmethod
    def load_high_score() -> int:
        if not os.path.exists(HIGHSCORE_FILE):
            HighscoreManager.save_high_score(0)
            return 0
        try:
            with open(HIGHSCORE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return int(data.get("high_score", 0))
        except Exception:
            return 0

    @staticmethod
    def save_high_score(score: int) -> int:
        data = {"high_score": max(0, int(score))}
        try:
            with open(HIGHSCORE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            app.logger.error(f"保存 highscore.json 失败: {e}")
        return data["high_score"]

    @staticmethod
    def update_if_higher(score: int) -> tuple[int, bool]:
        """检查并更新最高分，返回 (当前最高分, 是否刷新纪录)"""
        current_high = HighscoreManager.load_high_score()
        if score > current_high:
            saved_high = HighscoreManager.save_high_score(score)
            return saved_high, True
        return current_high, False


# 跨域 CORS 支持
@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


@app.route("/api/info", methods=["GET"])
def get_info():
    """获取历史最高分及基础游戏配置"""
    high_score = HighscoreManager.load_high_score()
    return jsonify({
        "status": "success",
        "high_score": high_score,
        "time_limit": game.time_limit,
        "initial_lives": 3
    })


@app.route("/api/start", methods=["POST"])
def start_game():
    """开始新游戏，重置分数和生命值，清空已用成语，返回第一道题目"""
    game.reset()
    question = game.next_question()
    high_score = HighscoreManager.load_high_score()

    if not question:
        return jsonify({
            "status": "error",
            "message": "成语词库为空或已全部答完。"
        }), 500

    return jsonify({
        "status": "success",
        "score": game.score,
        "lives": game.lives,
        "high_score": high_score,
        "game_over": False,
        "question": question
    })


@app.route("/api/submit", methods=["POST"])
def submit_answer():
    """接收用户答案或超时标记，校验结果，按需更新最高分并返回下一题"""
    payload = request.get_json(silent=True) or {}
    user_answer = payload.get("answer")
    is_timeout = bool(payload.get("timeout", False))

    if game.current_question is None:
        return jsonify({
            "status": "error",
            "message": "当前没有正在进行中的题目，请先调用 /api/start 开始游戏。"
        }), 400

    # 提交校验
    result = game.submit_answer(user_input=user_answer, is_timeout=is_timeout)

    # 最高分检查与持久化
    high_score, new_record = HighscoreManager.update_if_higher(game.score)

    response_data = {
        "status": "success",
        "correct": result["correct"],
        "lives": result["lives"],
        "score": result["score"],
        "game_over": result["game_over"],
        "high_score": high_score,
        "new_high_score": new_record,
        "question": None
    }

    # 若回答错误，一并返回正确答案汉字
    if not result["correct"]:
        response_data["correct_char"] = result["correct_char"]

    # 若未游戏结束，自动抽取并附带下一道题目
    if not result["game_over"]:
        next_q = game.next_question()
        if next_q is None:
            # 题库全部打通关
            response_data["game_over"] = True
            response_data["all_cleared"] = True
        else:
            response_data["question"] = next_q

    return jsonify(response_data)


if __name__ == "__main__":
    import socket

    def find_available_port(default_port=5000):
        env_port = os.environ.get("PORT")
        if env_port:
            return int(env_port)
        for p in [default_port, 5001, 8080]:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(("0.0.0.0", p))
                    return p
            except OSError:
                continue
        return 5001

    port = find_available_port()
    print(f"🚀 成语填空后端服务已启动: http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)
