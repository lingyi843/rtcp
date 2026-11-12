(function () {
  "use strict";

  const ROOT_ID = "rtcp-switch";
  const POLL_INTERVAL_MS = 1000;
  let latest = null;
  let busy = false;
  let pendingMessage = "";

  function installStyles() {
    if (document.getElementById("rtcp-switch-styles")) return;
    const style = document.createElement("style");
    style.id = "rtcp-switch-styles";
    style.textContent = `
      .rtcp-switch-card {
        position: fixed;
        right: 18px;
        bottom: 18px;
        z-index: 2147483000;
        width: 226px;
        padding: 12px 13px 11px;
        border: 1px solid #3a494d;
        border-radius: 12px;
        background: rgba(20, 29, 31, .96);
        box-shadow: 0 10px 32px rgba(0, 0, 0, .38);
        color: #e9eeee;
        font-family: "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
        backdrop-filter: blur(8px);
        user-select: none;
      }
      .rtcp-switch-card.is-active {
        border-color: #3eb77b;
      }
      .rtcp-switch-card.is-error {
        border-color: #c95c63;
      }
      .rtcp-switch-head {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
      }
      .rtcp-switch-dot {
        width: 8px;
        height: 8px;
        flex: 0 0 8px;
        border-radius: 50%;
        background: #657477;
        box-shadow: 0 0 0 3px rgba(101, 116, 119, .14);
      }
      .rtcp-switch-card.is-active .rtcp-switch-dot {
        background: #45d58f;
        box-shadow: 0 0 0 3px rgba(69, 213, 143, .16);
      }
      .rtcp-switch-title {
        flex: 1;
        font-size: 13px;
        font-weight: 700;
        letter-spacing: .02em;
      }
      .rtcp-switch-state {
        color: #8c9b9e;
        font: 700 11px/1 Consolas, "Cascadia Mono", monospace;
      }
      .rtcp-switch-card.is-active .rtcp-switch-state {
        color: #56dda0;
      }
      .rtcp-switch-row {
        display: flex;
        align-items: center;
        gap: 10px;
      }
      .rtcp-switch-button {
        position: relative;
        width: 58px;
        height: 30px;
        flex: 0 0 58px;
        padding: 0;
        border: 1px solid #4b5b5f;
        border-radius: 18px;
        background: #2d393c;
        cursor: pointer;
        transition: background .18s, border-color .18s, opacity .18s;
      }
      .rtcp-switch-button::after {
        content: "";
        position: absolute;
        top: 3px;
        left: 3px;
        width: 22px;
        height: 22px;
        border-radius: 50%;
        background: #d9e0e1;
        box-shadow: 0 2px 5px rgba(0, 0, 0, .35);
        transition: transform .18s, background .18s;
      }
      .rtcp-switch-button[aria-checked="true"] {
        border-color: #38ae74;
        background: #1f7150;
      }
      .rtcp-switch-button[aria-checked="true"]::after {
        transform: translateX(28px);
        background: #effff7;
      }
      .rtcp-switch-button:focus-visible {
        outline: 2px solid #6ed6aa;
        outline-offset: 2px;
      }
      .rtcp-switch-button.is-busy {
        cursor: wait;
        opacity: .55;
      }
      .rtcp-switch-message {
        min-width: 0;
        color: #91a0a3;
        font-size: 10px;
        line-height: 1.35;
      }
      .rtcp-switch-card.is-error .rtcp-switch-message {
        color: #ef8d94;
      }
      @media (max-width: 700px) {
        .rtcp-switch-card {
          right: 10px;
          bottom: 10px;
          width: 205px;
        }
      }
    `;
    document.head.appendChild(style);
  }

  function ensureCard() {
    let root = document.getElementById(ROOT_ID);
    if (root) return root;
    root = document.createElement("section");
    root.id = ROOT_ID;
    root.className = "rtcp-switch-card";
    root.setAttribute("aria-label", "RTCP 坐标补偿开关");
    root.innerHTML = `
      <div class="rtcp-switch-head">
        <span class="rtcp-switch-dot" aria-hidden="true"></span>
        <span class="rtcp-switch-title">RTCP 坐标补偿</span>
        <span class="rtcp-switch-state">--</span>
      </div>
      <div class="rtcp-switch-row">
        <button class="rtcp-switch-button" type="button" role="switch"
                aria-checked="false" aria-label="切换 RTCP"></button>
        <span class="rtcp-switch-message">正在读取状态...</span>
      </div>
    `;
    root.querySelector("button").addEventListener("click", toggle);
    document.body.appendChild(root);
    return root;
  }

  function render() {
    const root = ensureCard();
    const button = root.querySelector("button");
    const state = root.querySelector(".rtcp-switch-state");
    const message = root.querySelector(".rtcp-switch-message");
    const rtcp = latest && latest.machine && latest.machine.rtcp;
    const authorized = Boolean(latest && latest.session && latest.session.authorized);
    const available = Boolean(rtcp && rtcp.available);
    const active = Boolean(available && rtcp.active);

    root.classList.toggle("is-active", active);
    root.classList.toggle("is-error", Boolean(pendingMessage));
    button.setAttribute("aria-checked", active ? "true" : "false");
    button.classList.toggle("is-busy", busy);
    button.disabled = busy;
    state.textContent = busy ? "..." : active ? "ON" : "OFF";

    if (pendingMessage) {
      message.textContent = pendingMessage;
      return;
    }
    if (!available) {
      message.textContent = "Klipper 未加载 rtcp";
      return;
    }
    if (!authorized) {
      message.textContent = "需先在操作台完成运动授权";
      return;
    }
    message.textContent = active
      ? `补偿中 · ${rtcp.last_segments || 0} 段`
      : (rtcp.reason || "机器坐标模式");
    root.title = active
      ? "RTCP 已启用：当前 G-code XYZ 使用工件坐标"
      : "RTCP 已关闭：当前 G-code XYZ 使用机器坐标";
  }

  async function request(path, options) {
    const response = await fetch(`/control/api/${path}`, {
      credentials: "same-origin",
      cache: "no-store",
      ...options,
    });
    let payload = {};
    try {
      payload = await response.json();
    } catch (_error) {
      payload = {};
    }
    if (!response.ok || payload.ok === false) {
      throw new Error(payload.error || `HTTP ${response.status}`);
    }
    return payload;
  }

  async function refresh() {
    try {
      latest = await request("status");
      render();
    } catch (error) {
      pendingMessage = String(error.message || error);
      render();
    }
  }

  async function toggle() {
    if (busy || !latest) return;
    const rtcp = latest.machine && latest.machine.rtcp;
    const authorized = Boolean(latest.session && latest.session.authorized);
    if (!rtcp || !rtcp.available) {
      pendingMessage = "Klipper 未加载 rtcp";
      render();
      return;
    }
    if (!authorized) {
      pendingMessage = "请先在五轴操作台完成运动授权";
      render();
      return;
    }

    busy = true;
    pendingMessage = "";
    render();
    try {
      const action = rtcp.active ? "disable" : "enable";
      await request(`rtcp/${action}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ confirm: true }),
      });
      pendingMessage = "";
      await refresh();
    } catch (error) {
      pendingMessage = String(error.message || error);
      render();
    } finally {
      busy = false;
      render();
    }
  }

  function start() {
    installStyles();
    ensureCard();
    refresh();
    window.setInterval(refresh, POLL_INTERVAL_MS);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start, { once: true });
  } else {
    start();
  }
})();
