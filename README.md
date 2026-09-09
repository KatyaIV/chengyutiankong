# 成语大闯关 🀄

> 一款具有浓郁新中式水墨风的成语单字填空闯关游戏，完美兼容移动端浏览器与微信。

---

## 🎮 游戏特色

- **新中式水墨美学**：宣纸质感背景、朱砂红印章、书法米字格字块
- **成语单字填空**：每题挖空一个汉字，考验成语记忆
- **15 秒限时闯关**：答对得 1 分，3 次失误即结束
- **历史最高分持久化**：打破纪录即时保存
- **微信/手机全兼容**：深度适配 IME 输入法与移动端软键盘

---

## 🚀 一键部署到 Render（免费 HTTPS）

### 第一步：将代码推送到 GitHub

```bash
# 在项目目录中初始化 Git（如已有则跳过）
git init
git add .
git commit -m "feat: 成语大闯关游戏完整版"

# 在 GitHub 上新建一个仓库（例如 chengyudaguanguan）
# 然后关联并推送
git remote add origin https://github.com/<你的用户名>/chengyudaguanguan.git
git branch -M main
git push -u origin main
```

### 第二步：注册并登录 Render

1. 打开 [https://render.com](https://render.com)，使用 GitHub 账号一键注册/登录。

### 第三步：创建 Web Service

1. 登录后点击右上角 **"New +"** → 选择 **"Web Service"**。
2. 在 **"Connect a repository"** 页面，选择你刚推送的 GitHub 仓库，点击 **"Connect"**。

### 第四步：配置并一键部署

填写以下关键配置（其余保持默认）：

| 配置项 | 填写内容 |
|--------|----------|
| **Name** | `chengyudaguanguan`（或任意英文名） |
| **Environment** | `Python 3` |
| **Region** | `Singapore`（亚洲延迟最低） |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn app:app` |
| **Instance Type** | `Free`（免费套餐） |

填写完成后点击底部 **"Create Web Service"** 按钮，等待约 2~3 分钟自动构建完成。

### 第五步：获取 HTTPS 链接并在微信分享

1. 部署成功后，Render 会自动生成形如 `https://chengyudaguanguan.onrender.com` 的 **HTTPS 链接**。
2. 复制该链接，在微信聊天窗口中直接粘贴发送，即可由对方点击直接在微信内置浏览器打开游戏。

> **💡 提示**：Render 免费套餐在无流量时会自动休眠（约 15 分钟后），首次打开可能需要等待约 30 秒唤醒。可升级至 Starter 套餐（\$7/月）以保持常驻在线。

---

## 🛠 本地开发运行

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 生成成语词库（如 idioms.json 不存在时）
python3 generate_idioms.py

# 3. 启动开发服务
python3 app.py

# 4. 在浏览器打开
open http://127.0.0.1:5001
```

---

## 📁 项目结构

```
成语填空/
├── app.py               # Flask 后端 API 服务（入口文件）
├── game_logic.py        # 核心游戏逻辑层（Model）
├── generate_idioms.py   # 成语词库生成脚本
├── idioms.json          # 2000 条均衡成语词库
├── highscore.json       # 历史最高分持久化文件
├── requirements.txt     # Python 依赖（Flask + gunicorn）
├── Procfile             # Render/Heroku 启动配置
└── static/
    ├── index.html       # 游戏前端主页面
    ├── style.css        # 新中式水墨风样式
    └── main.js          # 游戏交互逻辑
```

---

## 📜 开源协议

MIT License
