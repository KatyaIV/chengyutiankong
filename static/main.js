/**
 * 成语大闯关 - 新中式水墨网页交互逻辑 (main.js)
 */

(function () {
  "use strict";

  // ================= 1. 核心状态管理 =================
  const state = {
    score: 0,
    lives: 3,
    highScore: 0,
    timeLimit: 15,
    currentQuestion: null,
    timerId: null,
    timeLeft: 15,
    isProcessing: false,  // 防重复提交锁
    isComposing: false    // 中文输入法 IME 合成锁
  };

  // DOM 元素缓存
  const dom = {
    startScreen: document.getElementById("start-screen"),
    gameScreen: document.getElementById("game-screen"),
    homeHighScore: document.getElementById("home-highscore"),
    gameHighScore: document.getElementById("game-highscore"),
    currentScore: document.getElementById("current-score"),
    livesContainer: document.getElementById("lives-container"),
    timerBar: document.getElementById("timer-bar"),
    timerText: document.getElementById("timer-text"),
    timerWrapper: document.querySelector(".timer-wrapper"),
    feedbackBanner: document.getElementById("feedback-banner"),
    idiomTiles: document.getElementById("idiom-tiles"),
    hiddenInput: document.getElementById("hidden-input"),
    visibleInput: document.getElementById("visible-char-input"),
    submitBtn: document.getElementById("submit-char-btn"),
    startBtn: document.getElementById("start-btn"),
    gameOverModal: document.getElementById("gameover-modal"),
    finalScore: document.getElementById("final-score"),
    finalHighScore: document.getElementById("final-highscore"),
    newRecordBadge: document.getElementById("new-record-badge"),
    restartBtn: document.getElementById("restart-btn"),
    homeBtn: document.getElementById("home-btn")
  };

  // ================= 2. Web Audio 纯代码合成古风音效 =================
  let audioCtx = null;

  function initAudio() {
    if (!audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        audioCtx = new AudioContext();
      }
    }
    if (audioCtx && audioCtx.state === "suspended") {
      audioCtx.resume();
    }
  }

  function playSound(type) {
    if (!audioCtx) return;
    try {
      const now = audioCtx.currentTime;
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.connect(gain);
      gain.connect(audioCtx.destination);

      if (type === "correct") {
        // 编钟五音清鸣 (G5 -> C6)
        osc.type = "sine";
        osc.frequency.setValueAtTime(783.99, now);
        osc.frequency.exponentialRampToValueAtTime(1046.5, now + 0.15);
        gain.gain.setValueAtTime(0.3, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.45);
        osc.start(now);
        osc.stop(now + 0.45);
      } else if (type === "wrong") {
        // 沉郁木铎低音 (220Hz -> 110Hz)
        osc.type = "triangle";
        osc.frequency.setValueAtTime(220, now);
        osc.frequency.exponentialRampToValueAtTime(110, now + 0.3);
        gain.gain.setValueAtTime(0.4, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.4);
        osc.start(now);
        osc.stop(now + 0.4);
      } else if (type === "click") {
        // 轻叩云板
        osc.type = "sine";
        osc.frequency.setValueAtTime(520, now);
        gain.gain.setValueAtTime(0.15, now);
        gain.gain.exponentialRampToValueAtTime(0.001, now + 0.08);
        osc.start(now);
        osc.stop(now + 0.08);
      }
    } catch (e) {
      console.warn("Audio playback not permitted yet", e);
    }
  }

  // ================= 3. 页面与屏幕切换 =================
  function showScreen(name) {
    dom.startScreen.classList.remove("active");
    dom.gameScreen.classList.remove("active");
    dom.gameOverModal.classList.remove("active");

    if (name === "start") {
      dom.startScreen.classList.add("active");
      fetchInfo();
    } else if (name === "game") {
      dom.gameScreen.classList.add("active");
    }
  }

  // ================= 4. API 数据交互 =================
  async function fetchInfo() {
    try {
      const res = await fetch("/api/info");
      const data = await res.json();
      if (data.status === "success") {
        state.highScore = data.high_score;
        state.timeLimit = data.time_limit || 15;
        dom.homeHighScore.textContent = state.highScore;
        dom.gameHighScore.textContent = state.highScore;
      }
    } catch (err) {
      console.error("获取基础信息失败:", err);
    }
  }

  async function startGame() {
    initAudio();
    playSound("click");
    state.isProcessing = true;

    try {
      const res = await fetch("/api/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" }
      });
      const data = await res.json();

      if (data.status === "success") {
        state.score = data.score;
        state.lives = data.lives;
        state.highScore = data.high_score;
        dom.currentScore.textContent = state.score;
        dom.gameHighScore.textContent = state.highScore;
        updateLivesUI(state.lives);

        showScreen("game");
        renderQuestion(data.question);
      } else {
        alert("开局失败: " + (data.message || "未知错误"));
      }
    } catch (err) {
      console.error("开局请求异常:", err);
      alert("网络连接异常，请确保后端服务正常运行。");
    } finally {
      state.isProcessing = false;
    }
  }

  async function submitCurrentAnswer(userChar, isTimeout = false) {
    if (state.isProcessing) return;
    state.isProcessing = true;
    stopTimer();

    try {
      const res = await fetch("/api/submit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          answer: userChar,
          timeout: isTimeout
        })
      });
      const data = await res.json();

      if (data.status === "success") {
        handleAnswerResult(data);
      } else {
        alert(data.message || "提交验证失败");
        state.isProcessing = false;
      }
    } catch (err) {
      console.error("答案提交异常:", err);
      state.isProcessing = false;
    }
  }

  // ================= 5. 题目与倒计时渲染 =================
  function renderQuestion(q) {
    state.currentQuestion = q;
    state.isProcessing = false;

    // 清空输入框
    dom.visibleInput.value = "";
    dom.hiddenInput.value = "";
    hideFeedback();

    // 渲染成语米字格方块
    dom.idiomTiles.innerHTML = "";
    const fullWord = q.full_word;
    const missingIndex = q.missing_index;

    for (let i = 0; i < fullWord.length; i++) {
      const tile = document.createElement("div");
      tile.className = "idiom-tile";

      if (i === missingIndex) {
        tile.classList.add("blank-tile", "focused");
        tile.id = "active-blank-tile";
        tile.innerHTML = `<span class="ancient-cursor"></span>`;
        // 点击挖空方块自动获取软键盘焦点
        tile.addEventListener("click", focusInput);
      } else {
        tile.innerHTML = `<span class="tile-char">${fullWord[i]}</span>`;
      }
      dom.idiomTiles.appendChild(tile);
    }

    // 自动聚焦
    focusInput();
    // 启动 15 秒倒计时
    startTimer(q.time_limit || 15);
  }

  // function focusInput() {
  //   setTimeout(() => {
  //     dom.visibleInput.focus();
  //   }, 50);
  // }

  // 修改 main.js 第 180 行附近的 focusInput 函数
  function focusInput() {
    setTimeout(() => {
      dom.visibleInput.focus();
      // 聚焦时确保输入框滚动到可视区域内
      dom.visibleInput.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }, 50);
  }

  // 15 秒精准倒计时
  function startTimer(duration) {
    stopTimer();
    state.timeLeft = duration;
    updateTimerUI(state.timeLeft, duration);

    const stepMs = 100;
    state.timerId = setInterval(() => {
      state.timeLeft -= stepMs / 1000;
      if (state.timeLeft <= 0) {
        state.timeLeft = 0;
        updateTimerUI(0, duration);
        stopTimer();
        // 触发超时结算
        submitCurrentAnswer("", true);
      } else {
        updateTimerUI(state.timeLeft, duration);
      }
    }, stepMs);
  }

  function stopTimer() {
    if (state.timerId) {
      clearInterval(state.timerId);
      state.timerId = null;
    }
  }

  function updateTimerUI(timeLeft, totalDuration) {
    const pct = Math.max(0, Math.min(100, (timeLeft / totalDuration) * 100));
    dom.timerBar.style.width = pct + "%";
    dom.timerText.textContent = Math.ceil(timeLeft) + "s";

    if (timeLeft <= 5) {
      dom.timerWrapper.classList.add("urgent");
    } else {
      dom.timerWrapper.classList.remove("urgent");
    }
  }

  // ================= 6. 判定反馈与动效 =================
  function handleAnswerResult(data) {
    const isCorrect = data.correct;
    state.score = data.score;
    state.lives = data.lives;
    state.highScore = data.high_score;

    dom.currentScore.textContent = state.score;
    dom.gameHighScore.textContent = state.highScore;
    updateLivesUI(state.lives);

    const blankTile = document.getElementById("active-blank-tile");

    if (isCorrect) {
      playSound("correct");
      showFeedback("妙哉！回答正确 +1分", true);
      if (blankTile) {
        blankTile.classList.remove("focused");
        blankTile.classList.add("tile-correct");
        blankTile.innerHTML = `<span class="tile-char" style="color: var(--c-jade);">${state.currentQuestion.correct_char}</span>`;
      }
    } else {
      playSound("wrong");
      const correctChar = data.correct_char || state.currentQuestion.correct_char;
      showFeedback(`惜哉！正确答案：【${correctChar}】`, false);
      if (blankTile) {
        blankTile.classList.remove("focused");
        blankTile.classList.add("tile-wrong");
        blankTile.innerHTML = `<span class="tile-char" style="color: var(--c-cinnabar);">${correctChar}</span>`;
      }
    }

    // 延迟切换下一题或展示结算弹窗
    const delayTime = isCorrect ? 1000 : 1600;
    setTimeout(() => {
      if (data.game_over) {
        showGameOver(data);
      } else if (data.question) {
        renderQuestion(data.question);
      }
    }, delayTime);
  }

  function updateLivesUI(currentLives) {
    const seals = dom.livesContainer.querySelectorAll(".life-seal");
    seals.forEach((seal, idx) => {
      if (idx < currentLives) {
        seal.classList.remove("lost");
      } else {
        seal.classList.add("lost");
      }
    });
  }

  function showFeedback(text, isCorrect) {
    dom.feedbackBanner.textContent = text;
    dom.feedbackBanner.className = "feedback-banner " + (isCorrect ? "show-correct" : "show-wrong");
  }

  function hideFeedback() {
    dom.feedbackBanner.className = "feedback-banner";
  }

  function showGameOver(data) {
    dom.finalScore.textContent = data.score;
    dom.finalHighScore.textContent = data.high_score;

    if (data.new_high_score) {
      dom.newRecordBadge.classList.remove("hidden");
    } else {
      dom.newRecordBadge.classList.add("hidden");
    }

    dom.gameOverModal.classList.add("active");
  }

  // ================= 7. 输入法事件监听与单字过滤 =================
  function onInputChar(e) {
    if (state.isComposing) return; // 正在输入拼音，暂不处理

    const val = dom.visibleInput.value.trim();
    if (!val) return;

    // 提取最后一个输入的有效汉字
    const lastChar = val[val.length - 1];
    // 确保为汉字
    if (/[\u4e00-\u9fa5]/.test(lastChar)) {
      dom.visibleInput.value = lastChar;
      // 自动即时提交
      submitCurrentAnswer(lastChar, false);
    } else {
      // 过滤掉非汉字输入
      dom.visibleInput.value = "";
    }
  }

  // 绑定事件监听
  function bindEvents() {
    // 首页开始按钮
    dom.startBtn.addEventListener("click", startGame);

    // 结算弹窗按钮
    dom.restartBtn.addEventListener("click", () => {
      dom.gameOverModal.classList.remove("active");
      startGame();
    });
    dom.homeBtn.addEventListener("click", () => {
      dom.gameOverModal.classList.remove("active");
      showScreen("start");
    });

    // 中文输入法 IME 合成事件兼容 (手机/微信端)
    dom.visibleInput.addEventListener("compositionstart", () => {
      state.isComposing = true;
    });

    dom.visibleInput.addEventListener("compositionend", (e) => {
      state.isComposing = false;
      onInputChar(e);
    });

    dom.visibleInput.addEventListener("input", onInputChar);

    // 回车或点击“确认”按钮提交
    dom.visibleInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        const char = dom.visibleInput.value.trim();
        if (char) submitCurrentAnswer(char, false);
      }
    });

    dom.submitBtn.addEventListener("click", () => {
      playSound("click");
      const char = dom.visibleInput.value.trim();
      if (char) {
        submitCurrentAnswer(char, false);
      } else {
        focusInput();
      }
    });


        // ----------------- 移动端软键盘弹起与自适应布局优化 -----------------
    function updateAppHeight() {
      // 优先获取 visualViewport 高度，兼容 iOS/Android 键盘弹起情况
      const vh = window.visualViewport ? window.visualViewport.height : window.innerHeight;
      document.documentElement.style.setProperty('--app-height', `${vh}px`);
    }

    // 初始化视口高度
    updateAppHeight();

    // 监听窗口大小及 visualViewport 变化
    if (window.visualViewport) {
      window.visualViewport.addEventListener('resize', updateAppHeight);
      window.visualViewport.addEventListener('scroll', updateAppHeight);
    } else {
      window.addEventListener('resize', updateAppHeight);
    }

    // 解决 iOS 输入法关闭后页面底部留白错位的问题
    dom.visibleInput.addEventListener('blur', () => {
      window.scrollTo(0, 0);
      updateAppHeight();
    });
    // ------------------------------------------------------------------






    // 首次触摸屏幕时解锁音频上下文
    document.addEventListener("touchstart", initAudio, { once: true });
    document.addEventListener("click", initAudio, { once: true });
  }

  // 初始化入口
  function init() {
    bindEvents();
    showScreen("start");
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
