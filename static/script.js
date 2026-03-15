document.addEventListener('DOMContentLoaded', () => {
    const addressInput = document.getElementById('addressInput');
    const chainSelect = document.getElementById('chainSelect');
    const scanBtn = document.getElementById('scanBtn');

    const loadingOverlay = document.getElementById('loadingOverlay');
    const resultsArea = document.getElementById('resultsArea');
    const redFlagsContainer = document.getElementById('redFlagsContainer');
    const redFlagsList = document.getElementById('redFlagsList');

    // UI Elements map
    const els = {
        name: document.getElementById('tokenName'),
        chain: document.getElementById('tokenChain'),
        addr: document.getElementById('tokenAddr'),
        riskLevelBox: document.getElementById('riskLevelBox'),
        riskLevelText: document.getElementById('riskLevelText'),

        // Audit
        hp: document.getElementById('valHoneypot'),
        mint: document.getElementById('valMintable'),
        taxes: document.getElementById('valTaxes'),
        bl: document.getElementById('valBlacklist'),
        proxy: document.getElementById('valProxy'),

        // Holders
        holders: document.getElementById('valHolders'),
        top10: document.getElementById('valTop10'),
        creator: document.getElementById('valCreator'),
        lpList: document.getElementById('lpList'),

        // Market
        liq: document.getElementById('valLiquidity'),
        vol: document.getElementById('valVolume'),
        price: document.getElementById('valPrice'),
        p5m: document.getElementById('valPrice5m'),
        p1h: document.getElementById('valPrice1h'),

        // Smart
        b1h: document.getElementById('valBuy1h'),
        s1h: document.getElementById('valSell1h'),
        signalsList: document.getElementById('signalsList'),

        // AI
        aiBox: document.getElementById('aiSummaryBox'),
        aiText: document.getElementById('aiSummaryText')
    };

    scanBtn.addEventListener('click', () => performScan());
    addressInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') performScan();
    });

    async function performScan() {
        const addr = addressInput.value.trim();
        const chain = chainSelect.value;

        if (!addr.startsWith('0x') || addr.length !== 42) {
            alert('❌ 无效地址！请输入 0x 开头的 42 位合约地址');
            return;
        }

        // Show loading, hide old results
        resultsArea.classList.add('hidden');
        redFlagsContainer.classList.add('hidden');
        loadingOverlay.classList.remove('hidden');
        scanBtn.disabled = true;
        scanBtn.querySelector('.btn-text').textContent = 'SCANNING...';

        try {
            const response = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token_address: addr, chain: chain })
            });

            const rawData = await response.json();

            if (!response.ok) {
                throw new Error(rawData.error || 'Server Error');
            }

            renderResults(rawData);

        } catch (err) {
            alert(`⚠️ 扫描失败: ${err.message}`);
        } finally {
            loadingOverlay.classList.add('hidden');
            scanBtn.disabled = false;
            scanBtn.querySelector('.btn-text').textContent = 'SCAN';
        }
    }

    function renderResults(res) {
        // 1. Header
        els.name.textContent = res.token.name !== "Unknown" ? `${res.token.name} (${res.token.symbol})` : "未知代币";
        els.chain.textContent = res.token.chain.toUpperCase();
        els.addr.textContent = res.token.address;

        // 2. Risk Banner
        const box = els.riskLevelBox;
        box.style.background = 'rgba(0,0,0,0.5)';
        box.style.border = '1px solid transparent';
        const dot = box.querySelector('.pulse-dot');
        dot.style.animation = 'pulse 1s infinite alternate';

        if (res.risk_level === "HIGH") {
            box.style.borderColor = 'var(--red-alert)';
            box.style.boxShadow = '0 0 20px rgba(255,42,42,0.3)';
            dot.style.background = 'var(--red-alert)';
            els.riskLevelText.textContent = 'EXTREME RISK';
            els.riskLevelText.className = 'text-danger';
        } else if (res.risk_level === "MEDIUM") {
            box.style.borderColor = '#facc15';
            box.style.boxShadow = '0 0 20px rgba(250,204,21,0.2)';
            dot.style.background = '#facc15';
            els.riskLevelText.textContent = 'MEDIUM RISK';
            els.riskLevelText.className = 'text-warning';
        } else {
            box.style.borderColor = 'var(--green-safe)';
            box.style.boxShadow = '0 0 20px rgba(0,255,136,0.2)';
            dot.style.background = 'var(--green-safe)';
            els.riskLevelText.textContent = 'LOW RISK';
            els.riskLevelText.className = 'text-safe';
        }

        // 3. Red Flags
        if (res.red_flags.length > 0) {
            redFlagsList.innerHTML = res.red_flags.map(f => `<li>${f}</li>`).join('');
            redFlagsContainer.classList.remove('hidden');
        }

        const d = res.data;

        // 4. Audit
        els.hp.innerHTML = safeRiskSpan(d.audit.is_honeypot, "是 (危险)", "否");
        els.mint.innerHTML = safeRiskSpan(d.audit.is_mintable, "是 (危险)", "否");
        const bTax = d.audit.buy_tax_percent || 0;
        const sTax = d.audit.sell_tax_percent || 0;
        els.taxes.innerHTML = `<span class="${bTax > 10 ? 'text-danger' : (bTax > 0 ? 'text-warning' : 'text-safe')}">B:${bTax}%</span> / <span class="${sTax > 10 ? 'text-danger' : (sTax > 0 ? 'text-warning' : 'text-safe')}">S:${sTax}%</span>`;
        els.bl.innerHTML = warnSpan(d.audit.is_blacklisted, "有", "无");
        els.proxy.innerHTML = warnSpan(d.audit.is_proxy, "是(可升级)", "否");

        // 5. Holders
        els.holders.textContent = d.holders.holder_count || '-';
        const t10 = d.holders.top_10_total_percent || 0;
        els.top10.innerHTML = `<span class="${t10 > 50 ? 'text-danger' : (t10 > 20 ? 'text-warning' : 'text-safe')}">${t10}%</span>`;
        els.creator.textContent = (d.holders.creator_percent || 0) + '%';

        els.lpList.innerHTML = (d.holders.lp_holders || []).slice(0, 3).map(lp => {
            const shortAddr = lp.address.substring(0, 6) + '...' + lp.address.slice(-4);
            const lockStr = lp.is_locked ? `<span class="text-safe">🔒已锁</span>` : `<span class="text-danger">🔓未锁</span>`;
            return `<li><span>${shortAddr}</span> <span style="text-align:right">${lp.percent}% ${lockStr}</span></li>`;
        }).join('') || '<li>暂无公开 LP 数据</li>';

        // 6. Market
        const m = d.market;
        if (m.error) {
            els.liq.textContent = 'N/A';
            els.vol.textContent = 'N/A';
            els.price.textContent = 'N/A';
        } else {
            const liq = m.liquidity_usd || 0;
            els.liq.innerHTML = `<span class="${liq < 10000 ? 'text-danger' : 'text-safe'}">$${liq.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>`;
            els.vol.textContent = '$' + (m.volume_24h_usd || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });
            els.price.textContent = '$' + m.price_usd;
            els.p5m.innerHTML = pctSpan(m.price_change_5m || 0);
            els.p1h.innerHTML = pctSpan(m.price_change_1h || 0);

            els.b1h.textContent = (m.txns_1h || {}).buys || 0;
            els.s1h.textContent = (m.txns_1h || {}).sells || 0;
        }

        // 7. Signals
        els.signalsList.innerHTML = (d.smart.signals || []).map(s => {
            let color = 'text-main';
            if (s.includes('🔴')) color = 'text-danger';
            if (s.includes('🟡')) color = 'text-warning';
            if (s.includes('🟢')) color = 'text-safe';
            return `<li class="${color}" style="font-size:0.8rem">${s}</li>`;
        }).join('') || '<li class="text-safe">🟢 暂无异常资金异动</li>';

        // 8. AI Summary
        if (res.ai_summary) {
            els.aiText.textContent = res.ai_summary;
            els.aiBox.classList.remove('hidden');
        } else {
            els.aiBox.classList.add('hidden');
        }

        resultsArea.classList.remove('hidden');
        resultsArea.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

    // Helpers
    function safeRiskSpan(isRisk, tTrue, tFalse) {
        if (isRisk) return `<span class="text-danger">${tTrue}</span>`;
        return `<span class="text-safe">${tFalse}</span>`;
    }
    function warnSpan(cond, tTrue, tFalse) {
        if (cond) return `<span class="text-warning">${tTrue}</span>`;
        return `<span class="text-safe">${tFalse}</span>`;
    }
    function pctSpan(val) {
        if (val > 0) return `<span class="text-safe">+${val}%</span>`;
        if (val < 0) return `<span class="text-danger">${val}%</span>`;
        return `<span>0%</span>`;
    }
});
