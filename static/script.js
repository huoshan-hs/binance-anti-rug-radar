document.addEventListener("DOMContentLoaded", () => {
    const chainSelect = document.getElementById("chainSelect");
    const addressInput = document.getElementById("addressInput");
    const scanBtn = document.getElementById("scanBtn");
    const watchBtn = document.getElementById("watchBtn");

    const statusBox = document.getElementById("statusBox");
    const summaryPanel = document.getElementById("summaryPanel");
    const detailsPanel = document.getElementById("detailsPanel");
    const watchlistPanel = document.getElementById("watchlistPanel");

    scanBtn.addEventListener("click", runAnalyze);
    watchBtn.addEventListener("click", loadWatchlist);
    addressInput.addEventListener("keypress", (event) => {
        if (event.key === "Enter") {
            runAnalyze();
        }
    });

    async function runAnalyze() {
        const tokenAddress = addressInput.value.trim();
        if (!tokenAddress.startsWith("0x") || tokenAddress.length !== 42) {
            window.alert("请输入有效的 0x 合约地址。");
            return;
        }

        setStatus("正在拉取 Binance 官方审计、市场、聪明钱和回退数据...");
        try {
            const response = await fetch("/api/analyze", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                    token_address: tokenAddress,
                    chain: chainSelect.value,
                }),
            });
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || "分析失败");
            }
            renderToken(data);
            clearStatus();
        } catch (error) {
            setStatus(`分析失败：${error.message}`);
        }
    }

    async function loadWatchlist() {
        setStatus("正在生成 BSC 每 10 分钟观察名单快照...");
        try {
            const response = await fetch("/api/watchlist");
            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.error || "观察名单生成失败");
            }
            renderWatchlist(data);
            clearStatus();
        } catch (error) {
            setStatus(`观察名单生成失败：${error.message}`);
        }
    }

    function renderToken(data) {
        const token = data.token;
        const classification = data.classification;
        const decision = data.decision;
        const facts = data.facts;

        document.getElementById("tokenTitle").textContent = `${token.name} (${token.symbol})`;
        document.getElementById("tokenMeta").textContent =
            `${classification.requested_chain.toUpperCase()} -> ${classification.detected_chain.toUpperCase()} | ${token.address}`;
        document.getElementById("worthWatching").textContent = decision.worth_watching;
        document.getElementById("maxRisk").textContent = decision.max_risk_point;
        document.getElementById("nextAction").textContent = decision.next_action;
        document.getElementById("confidence").textContent = classification.confidence;

        const riskBadge = document.getElementById("riskBadge");
        riskBadge.textContent = `${decision.risk_level} / ${decision.score}`;
        riskBadge.className = `risk-badge ${riskClass(decision.risk_level)}`;

        const baseFacts = [
            ["请求链", classification.requested_chain.toUpperCase()],
            ["识别链", classification.detected_chain.toUpperCase()],
            ["地址类型", classification.address_type],
            ["地址判断", classification.address_judgement || "-"],
            ["数据源", classification.data_sources.join(", ") || "-"],
            ["启动时间", token.launch_time || "-"],
            ["流动性", usd(facts.market.liquidity_usd)],
            ["持有人", facts.market.holders ?? facts.holders.holder_count ?? "-"],
            ["Top10 持仓", pct(facts.holders.top_10_total_percent)],
        ];
        document.getElementById("baseFacts").innerHTML = baseFacts
            .map(([label, value]) => `<li><span>${label}</span><strong>${value}</strong></li>`)
            .join("");

        const riskItems = facts.key_risks.length
            ? facts.key_risks
            : ["暂未发现明显硬风险，但仍需人工复核。"];
        document.getElementById("riskFacts").innerHTML = riskItems
            .map((item) => `<li><span>•</span><strong>${item}</strong></li>`)
            .join("");

        summaryPanel.classList.remove("hidden");
        detailsPanel.classList.remove("hidden");
    }

    function renderWatchlist(data) {
        const meta = `${data.scan_time} | ${data.source}`;
        document.getElementById("watchMeta").textContent = meta;

        const cards = data.candidates.map((item, index) => `
            <article class="watch-card">
                <div class="watch-rank">#${index + 1}</div>
                <h3>${item.name} (${item.symbol})</h3>
                <p class="muted mono">${item.address}</p>
                <div class="watch-score">雷达分 ${item.watchlist_score}</div>
                <ul class="fact-list compact">
                    <li><span>流动性</span><strong>${usd(item.liquidity_usd)}</strong></li>
                    <li><span>市值</span><strong>${usd(item.market_cap_usd)}</strong></li>
                    <li><span>持有人</span><strong>${item.holders ?? "-"}</strong></li>
                    <li><span>Top10</span><strong>${pct(item.top10_percent)}</strong></li>
                    <li><span>税率</span><strong>${pct(item.buy_tax_percent)} / ${pct(item.sell_tax_percent)}</strong></li>
                </ul>
                <p class="watch-reason">${item.reasons.join("；") || "通过基础风控筛选"}</p>
            </article>
        `);

        document.getElementById("watchlistCards").innerHTML = cards.length
            ? cards.join("")
            : '<p class="muted">本轮没有通过筛选的新 meme 候选。</p>';

        watchlistPanel.classList.remove("hidden");
    }

    function setStatus(text) {
        statusBox.textContent = text;
        statusBox.classList.remove("hidden");
    }

    function clearStatus() {
        statusBox.classList.add("hidden");
        statusBox.textContent = "";
    }

    function usd(value) {
        const num = Number(value);
        if (!Number.isFinite(num)) {
            return "-";
        }
        return `$${num.toLocaleString(undefined, { maximumFractionDigits: 2 })}`;
    }

    function pct(value) {
        const num = Number(value);
        if (!Number.isFinite(num)) {
            return "-";
        }
        return `${num.toFixed(2)}%`;
    }

    function riskClass(level) {
        if (level === "高风险") {
            return "risk-high";
        }
        if (level === "中风险") {
            return "risk-mid";
        }
        return "risk-low";
    }
});
