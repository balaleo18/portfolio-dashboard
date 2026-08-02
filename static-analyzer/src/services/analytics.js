// Portfolio analytics services, translated from update_kite_dashboard.py

export const SCENARIOS = [
  {
    name: "10% India equity correction",
    shocks: {
      "Core/direct equity": -0.10,
      "High beta / small-mid-factor": -0.14,
      "Mid/broad equity": -0.12,
      "Global equity FoF": -0.05,
      "Low-vol hybrid/arbitrage": -0.005,
      "Hybrid/other FoF": -0.01,
      "Debt / liquidity": 0.0,
    }
  },
  {
    name: "15% India equity correction",
    shocks: {
      "Core/direct equity": -0.15,
      "High beta / small-mid-factor": -0.22,
      "Mid/broad equity": -0.18,
      "Global equity FoF": -0.08,
      "Low-vol hybrid/arbitrage": -0.01,
      "Hybrid/other FoF": -0.015,
      "Debt / liquidity": -0.0025,
    }
  },
  {
    name: "Small/mid/factor -30%",
    shocks: {
      "Core/direct equity": -0.06,
      "High beta / small-mid-factor": -0.30,
      "Mid/broad equity": -0.22,
      "Global equity FoF": -0.05,
      "Low-vol hybrid/arbitrage": 0.0,
      "Hybrid/other FoF": -0.01,
      "Debt / liquidity": 0.0,
    }
  },
  {
    name: "Oil + INR risk-off shock",
    shocks: {
      "Core/direct equity": -0.12,
      "High beta / small-mid-factor": -0.20,
      "Mid/broad equity": -0.16,
      "Global equity FoF": 0.05,
      "Low-vol hybrid/arbitrage": -0.005,
      "Hybrid/other FoF": -0.005,
      "Debt / liquidity": -0.005,
    }
  },
  {
    name: "Credit event in weak listed debt",
    shocks: {
      "Debt / liquidity": -0.085
    }
  }
];

export function getAssetClass(instrumentType, sector) {
  const instrument = String(instrumentType || "-").trim();
  const sec = String(sector || "-").trim().toUpperCase();

  if (instrument && instrument !== "-") {
    if (instrument.startsWith("Debt")) {
      return "MF debt/liquid";
    }
    if (instrument.startsWith("Hybrid")) {
      return "MF hybrid/arbitrage";
    }
    if (instrument.startsWith("Equity")) {
      return "MF active equity";
    }
    if (instrument.includes("Index Funds/ETFs")) {
      return "MF index/factor";
    }
    if (instrument.includes("Fund of Funds")) {
      return "MF FoF/global/other";
    }
    return "MF other";
  }
  if (sec === "DEBT") {
    return "Direct listed debt";
  }
  if (sec === "ETF") {
    return "Listed ETF/commodity";
  }
  return "Direct equity";
}

export function getRiskBucket(assetClass, instrumentType, sector, symbol) {
  const asset = assetClass;
  const instrument = String(instrumentType || "-").trim();
  const sec = String(sector || "-").trim().toUpperCase();
  const sym = String(symbol || "").toUpperCase();

  if (asset === "MF debt/liquid" || asset === "Direct listed debt") {
    return "Debt / liquidity";
  }
  if (asset === "MF hybrid/arbitrage") {
    return "Low-vol hybrid/arbitrage";
  }
  if (asset === "MF FoF/global/other") {
    const globalTokens = ["U.S.", "US ", "CHINA", "GLOBAL"];
    if (globalTokens.some(token => sym.includes(token))) {
      return "Global equity FoF";
    }
    return "Hybrid/other FoF";
  }
  
  const highBetaTokens = ["SMALL", "ALPHA", "MOMENTUM"];
  if (
    instrument.includes("Small Cap") ||
    sym.includes("MICROCAP") ||
    sec === "REAL ESTATE" ||
    sec === "DEFENCE" ||
    highBetaTokens.some(token => sym.includes(token))
  ) {
    return "High beta / small-mid-factor";
  }

  if (instrument.includes("Mid Cap") || sym.includes("NEXT 50") || sym.includes("NIFTY500")) {
    return "Mid/broad equity";
  }

  return "Core/direct equity";
}

export function getHoldingAction(symbol, sector, assetClass, riskBucket, pnlPct, weight) {
  const isFund = assetClass.startsWith("MF");
  const isDebt = riskBucket === "Debt / liquidity";
  const isHighBeta = riskBucket === "High beta / small-mid-factor";
  const isDirectEquity = assetClass === "Direct equity";

  let rec = "Hold";
  let valueCase = "Position is acceptable but not a priority add.";
  let tradeCase = "Monitor; wait for a clear trend or valuation trigger.";

  if (isDebt && pnlPct <= -20) {
    rec = "Exit/Review";
    valueCase = "Credit/liquidity risk dominates valuation; do not average before issuer-level review.";
    tradeCase = "No short-term trade case; treat as recovery/exit decision.";
  } else if (isDirectEquity && pnlPct <= -20) {
    rec = "Exit/Review";
    valueCase = "Deep drawdown; thesis needs fresh fundamentals before adding.";
    tradeCase = "Momentum is broken; wait for base formation or reclaim of trend.";
  } else if (weight > 10 && (riskBucket === "Low-vol hybrid/arbitrage" || riskBucket === "Debt / liquidity")) {
    rec = "Trim";
    valueCase = "Useful defensive asset, but position size creates opportunity cost.";
    tradeCase = "No urgency; reduce gradually into liquidity or redeploy on equity corrections.";
  } else if (pnlPct >= 25 && (isDirectEquity || isHighBeta)) {
    rec = "Trim";
    valueCase = "Good winner; protect capital if valuation has run ahead of earnings.";
    tradeCase = "Trail profits; book partial gains on failed breakout or high-volume reversal.";
  } else if (isFund && (riskBucket === "Core/direct equity" || riskBucket === "Mid/broad equity")) {
    rec = "Buy/Add";
    valueCase = "Cleaner diversified compounding sleeve.";
    tradeCase = "Add on market pullbacks instead of chasing sharp rallies.";
  } else if (isDirectEquity && pnlPct >= -10) {
    rec = "Hold";
    valueCase = "Maintain while thesis and earnings quality remain intact.";
    tradeCase = "Hold; add only after strength confirms or support retest holds.";
  } else if (isHighBeta) {
    rec = "Hold";
    valueCase = "High-beta exposure can compound, but valuation risk is higher.";
    tradeCase = "Size carefully; avoid averaging during momentum fades.";
  }

  let pros = isFund ? "Diversifies the sleeve." : `Adds exposure to ${sector.toLowerCase()}.`;
  if (pnlPct > 0) {
    pros += " Position is currently profitable.";
  }
  if (riskBucket === "Low-vol hybrid/arbitrage" || riskBucket === "Debt / liquidity") {
    pros += " Provides defensive ballast.";
  }

  let cons = weight < 0.5 ? "Limited direct alpha impact at small weight." : "Needs active monitoring.";
  if (pnlPct < -10) {
    cons += " Current drawdown is a warning signal.";
  }
  if (isHighBeta) {
    cons += " High-beta sleeve can reverse quickly."
  }
  if (isDebt && pnlPct <= -20) {
    cons += " Possible value trap or credit event.";
  }

  return {
    recommendation: rec,
    valueCase,
    tradeCase,
    pros,
    cons
  };
}

export function processHoldingsData(rawRows) {
  // Parse rows and calculate intermediate fields
  let holdings = [];
  
  for (const row of rawRows) {
    // Basic numerical checks
    const qty = parseFloat(row["Quantity Available"] || row["QuantityAvailable"] || 0);
    const avgPrice = parseFloat(row["Average Price"] || row["AveragePrice"] || 0);
    const prevClose = parseFloat(row["Previous Closing Price"] || row["PreviousClosingPrice"] || row["Last Price"] || row["LastPrice"] || 0);
    
    if (qty <= 0 || prevClose <= 0) continue;
    
    const symbol = String(row["Symbol"] || row["Trading Symbol"] || row["TradingSymbol"] || "-").trim();
    const isin = String(row["ISIN"] || row["Isin"] || "-").trim();
    const sector = String(row["Sector"] || "-").trim();
    const instrumentType = String(row["Instrument Type"] || row["InstrumentType"] || "-").trim();
    
    const investedValue = qty * avgPrice;
    const currentValue = qty * prevClose;
    const pnl = currentValue - investedValue;
    const pnlPct = investedValue > 0 ? (pnl / investedValue) * 100 : 0;
    
    const assetClass = getAssetClass(instrumentType, sector);
    const riskBucket = getRiskBucket(assetClass, instrumentType, sector, symbol);
    
    holdings.push({
      symbol,
      isin,
      sector,
      instrumentType,
      quantity: qty,
      avgPrice,
      currentPrice: prevClose,
      investedValue,
      currentValue,
      pnl,
      pnlPct,
      assetClass,
      riskBucket
    });
  }
  
  // Total summary
  const totalValue = holdings.reduce((sum, h) => sum + h.currentValue, 0);
  const totalInvested = holdings.reduce((sum, h) => sum + h.investedValue, 0);
  const totalPnL = totalValue - totalInvested;
  const totalPnLPct = totalInvested > 0 ? (totalPnL / totalInvested) * 100 : 0;
  
  // Calculate weights & actions
  holdings = holdings.map(h => {
    const weight = totalValue > 0 ? (h.currentValue / totalValue) * 100 : 0;
    const action = getHoldingAction(h.symbol, h.sector, h.assetClass, h.riskBucket, h.pnlPct, weight);
    return {
      ...h,
      weight,
      ...action
    };
  });
  
  // Group by Asset Class
  const assetClassMap = {};
  holdings.forEach(h => {
    if (!assetClassMap[h.assetClass]) {
      assetClassMap[h.assetClass] = { name: h.assetClass, value: 0, pnl: 0, count: 0 };
    }
    assetClassMap[h.assetClass].value += h.currentValue;
    assetClassMap[h.assetClass].pnl += h.pnl;
    assetClassMap[h.assetClass].count += 1;
  });
  const assetClassSummary = Object.values(assetClassMap).map(g => ({
    ...g,
    weight: totalValue > 0 ? (g.value / totalValue) * 100 : 0
  })).sort((a, b) => b.value - a.value);
  
  // Group by Risk Bucket
  const riskBucketMap = {};
  holdings.forEach(h => {
    if (!riskBucketMap[h.riskBucket]) {
      riskBucketMap[h.riskBucket] = { name: h.riskBucket, value: 0, pnl: 0, count: 0 };
    }
    riskBucketMap[h.riskBucket].value += h.currentValue;
    riskBucketMap[h.riskBucket].pnl += h.pnl;
    riskBucketMap[h.riskBucket].count += 1;
  });
  const riskBucketSummary = Object.values(riskBucketMap).map(g => ({
    ...g,
    weight: totalValue > 0 ? (g.value / totalValue) * 100 : 0
  })).sort((a, b) => b.value - a.value);

  // Group by Sector (top 12)
  const sectorMap = {};
  holdings.forEach(h => {
    if (!sectorMap[h.sector]) {
      sectorMap[h.sector] = { name: h.sector, value: 0, pnl: 0, count: 0 };
    }
    sectorMap[h.sector].value += h.currentValue;
    sectorMap[h.sector].pnl += h.pnl;
    sectorMap[h.sector].count += 1;
  });
  const sectorSummary = Object.values(sectorMap).map(g => ({
    ...g,
    weight: totalValue > 0 ? (g.value / totalValue) * 100 : 0
  })).sort((a, b) => b.value - a.value);
  
  // Stress Tests Calculation
  const stressTests = SCENARIOS.map(sc => {
    let loss = 0;
    holdings.forEach(h => {
      const shock = sc.shocks[h.riskBucket] || 0;
      loss += h.currentValue * shock;
    });
    return {
      scenario: sc.name,
      loss: loss,
      lossPct: totalValue > 0 ? (loss / totalValue) * 100 : 0,
      endingValue: totalValue + loss
    };
  });
  
  // Risk Flags Engine
  const flags = [];
  
  if (holdings.length > 0) {
    // 1. Single holding concentration
    const sortedByWeight = [...holdings].sort((a, b) => b.weight - a.weight);
    const top = sortedByWeight[0];
    if (top.weight > 15) {
      flags.push({
        severity: "High",
        title: "Single holding concentration",
        detail: `${top.symbol} is ${top.weight.toFixed(1)}% of your portfolio. This is opportunity-cost concentration even if the fund is low volatility.`
      });
    }
    
    // 2. Credit/liquidity risk in listed debt
    const weakDebt = holdings.filter(h => h.assetClass === "Direct listed debt" && h.pnlPct <= -20)
      .sort((a, b) => a.pnlPct - b.pnlPct);
    if (weakDebt.length > 0) {
      const w = weakDebt[0];
      flags.push({
        severity: "High",
        title: "Credit/liquidity risk in listed debt",
        detail: `${w.symbol} is down ${w.pnlPct.toFixed(1)}% and still worth INR ${w.currentValue.toLocaleString('en-IN')}. Treat this as a credit review item, not a normal bond fluctuation.`
      });
    }
    
    // 3. Financial services overlap
    const directHoldings = holdings.filter(h => h.instrumentType === "-");
    const financialVal = directHoldings.filter(h => h.sector === "FINANCIAL SERVICES")
      .reduce((sum, h) => sum + h.currentValue, 0);
    const financialWeight = totalValue > 0 ? (financialVal / totalValue) * 100 : 0;
    if (financialWeight > 10) {
      flags.push({
        severity: "Medium",
        title: "Financial services and market overlap",
        detail: `Financial services is ${financialWeight.toFixed(1)}% of your portfolio and includes several correlated capital-market platform names.`
      });
    }
    
    // 4. Too many immaterial positions
    const tinyCount = holdings.filter(h => h.weight < 0.5).length;
    if (tinyCount >= 20) {
      flags.push({
        severity: "Medium",
        title: "Too many immaterial positions",
        detail: `${tinyCount} holdings are below 0.5% weight. They add monitoring load without meaningful return impact.`
      });
    }
    
    // 5. Under-risked for aggressive growth
    const defensiveVal = holdings.filter(h => ["Low-vol hybrid/arbitrage", "Debt / liquidity"].includes(h.riskBucket))
      .reduce((sum, h) => sum + h.currentValue, 0);
    const defensiveWeight = totalValue > 0 ? (defensiveVal / totalValue) * 100 : 0;
    if (defensiveWeight > 40) {
      flags.push({
        severity: "Medium",
        title: "Under-risked for aggressive growth",
        detail: `Debt, liquid, and arbitrage-like exposure is ${defensiveWeight.toFixed(1)}%. Good dry powder, but high opportunity cost over 3-5 years.`
      });
    }
  }

  // Count recommendations
  const actionCounts = { "Buy/Add": 0, "Hold": 0, "Trim": 0, "Exit/Review": 0 };
  holdings.forEach(h => {
    actionCounts[h.recommendation] = (actionCounts[h.recommendation] || 0) + 1;
  });

  return {
    totalValue,
    totalInvested,
    totalPnL,
    totalPnLPct,
    holdings,
    assetClassSummary,
    riskBucketSummary,
    sectorSummary,
    stressTests,
    flags,
    actionCounts
  };
}
