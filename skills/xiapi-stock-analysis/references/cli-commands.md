# CLI 命令参考

本文档汇总个股分析所需的 CLI 命令，便于快速查阅。

## 前期准备

### Token 配置

```bash
# 检查当前配置
npx daxiapi-cli@latest config get token

# 配置 Token（方式一：CLI 配置）
npx daxiapi-cli@latest config set token YOUR_TOKEN_FROM_DAXIAPI

# 配置 Token（方式二：环境变量）
export DAXIAPI_TOKEN=YOUR_TOKEN_FROM_DAXIAPI
```

### 标的搜索与验证

```bash
# 搜索股票
npx daxiapi-cli@latest search <公司名> --type stock

# 验证单股数据可用性
npx daxiapi-cli@latest stock info <code>

# 验证多股数据可用性（最多20只）
npx daxiapi-cli@latest stock info <code1>,<code2>,<code3>
```

---

## Step 2: 数据收集命令

### 2.1 基础信息与行情

```bash
# 单股：股票基础信息（含技术指标快照）
npx daxiapi-cli@latest stock info <code>

# 多股：一次性拉取快照（适合做横向对比）
npx daxiapi-cli@latest stock info <code1>,<code2>,<code3>

# K线数据（用于指标复算与形态分析，按股票逐只拉取）
npx daxiapi-cli@latest kline <code>
```

### 2.2 基本面与财务

```bash
# 单股财务报告
npx daxiapi-cli@latest report finance <code>

# 多股财务对比（逐只执行，保持同一报告期口径）
npx daxiapi-cli@latest report finance <code1>
npx daxiapi-cli@latest report finance <code2>
```

**联动 Skill**：`xiapi-financial-roe-analysis`

### 2.2.1 对比模式建议口径

- 技术面对比：统一最近20/60个交易日窗口
- 财报对比：统一年报/季报/TTM口径
- 价值面对比：统一估值口径与行业基准

### 2.3 行业与市场主线

```bash
# 板块内个股排名
npx daxiapi-cli@latest sector stocks --code <BK_CODE> --order cs

# 板块热力图
npx daxiapi-cli@latest sector heatmap --order cs --limit 20

# 市场温度
npx daxiapi-cli@latest market temp
```

### 2.4 技术形态

```bash
# 趋势向上形态
npx daxiapi-cli@latest stock pattern trendUp

# 站上50日线
npx daxiapi-cli@latest stock pattern crossMa50

# VCP 波动收缩形态
npx daxiapi-cli@latest stock pattern vcp
```

### 2.5 资金与情绪

```bash
# 股票热度排名
npx daxiapi-cli@latest hotrank stock --type hour --list-type normal

# 换手率
npx daxiapi-cli@latest turnover

# 涨停股
npx daxiapi-cli@latest zdt --type zt
```

---

## 命令执行顺序建议

### 单股模式

| 分析阶段 | 优先命令 | 可选命令 |
|---------|---------|---------|
| 标的确认 | `search`, `stock info` | - |
| 基本面 | `report finance` | `sector stocks` |
| 技术面 | `stock info`, `kline`, `stock pattern` | - |
| 资金情绪 | `hotrank`, `turnover` | `zdt` |
| 市场环境 | `market temp`, `sector heatmap` | - |

### 多股对比模式

| 阶段 | 优先命令 | 目标 |
|------|---------|------|
| 标的确认 | `search`, `stock info <code1,code2,...>` | 一次性确认对比池 |
| 快照对比 | `stock info <code1,code2,...>` | 获取多股同日指标 |
| 技术细化 | `kline <code>`（逐只） | 复算趋势与形态一致性 |
| 财务对比 | `report finance <code>`（逐只） | 输出财报质量横向比较 |
| 市场校准 | `market temp`, `sector heatmap` | 判断比较结果是否顺势 |
