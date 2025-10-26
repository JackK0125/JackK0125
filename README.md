# ICT Trading Bot - NQ Futures Strategy

A comprehensive trading bot implementing the Inner Circle Trader (ICT) systematic model for trading NQ (NASDAQ) futures during the New York AM session.

## Overview

This bot implements a complete ICT trading strategy based on the five core steps:

1. **Determine Higher Time Frame (HTF) Bias** - Analyze liquidity delivery and FVG respect/disrespect patterns
2. **Identify Key Rejection Levels** - Find high-probability reversal points (FVGs, liquidity pools, session levels)
3. **Find Manipulation Leg & Inversion FVG** - Detect entry signals
4. **Define Targets** - Identify profit targets (draws on liquidity)
5. **Execute with Precision** - Entry, stop-loss placement, and trade management

## Features

### Strategy Components

- **Fair Value Gap (FVG) Detection**
  - Identifies bullish and bearish FVGs
  - Tracks FVG filling and respect/disrespect patterns
  - Detects Inversion FVGs for entry signals

- **Liquidity Analysis**
  - Swing high/low detection
  - Equal highs/lows identification
  - Liquidity sweep detection
  - Session high/low tracking (London, Asia, NY)
  - Low resistance liquidity runs

- **Bias Determination**
  - Liquidity delivery analysis (buy-side vs sell-side)
  - FVG respect/disrespect patterns
  - 4-hour candle direction confirmation
  - Multi-signal bias confirmation

- **Trade Execution**
  - Manipulation leg identification
  - Inversion FVG entry signals
  - Dynamic stop-loss placement
  - Breakeven move management
  - Multiple target levels

- **Critical Rules Implementation**
  - ✅ Don't trade against equal highs/lows
  - ✅ Only trade 9:30 AM - 11:00 AM ET
  - ✅ Follow the 4-hour candle direction

### Backtesting Engine

- Comprehensive backtesting with historical data
- Multiple timeframe analysis (1m, 5m, 15m, 30m, 1h, 4h, 1d, 1wk)
- Parameter optimization
- Detailed performance metrics

### Performance Analytics

- Sharpe Ratio & Sortino Ratio
- Maximum Drawdown analysis
- Win/Loss streaks
- Profit Factor
- Kelly Criterion
- Maximum Favorable/Adverse Excursion (MFE/MAE)
- Equity curve visualization
- Trade distribution analysis

## Project Structure

```
ict_trading_bot/
├── config/
│   └── strategy_config.yaml      # Strategy configuration
├── src/
│   ├── data/
│   │   └── data_fetcher.py       # Market data fetching
│   ├── strategy/
│   │   ├── fvg_detector.py       # Fair Value Gap detection
│   │   ├── liquidity_detector.py # Liquidity pool detection
│   │   ├── bias_detector.py      # HTF bias determination
│   │   ├── manipulation_detector.py # Manipulation leg detection
│   │   └── target_identifier.py  # Target identification
│   ├── execution/
│   │   └── trade_executor.py     # Trade execution & management
│   ├── backtesting/
│   │   ├── backtest_engine.py    # Backtesting engine
│   │   └── performance_metrics.py # Performance analytics
│   └── bot.py                     # Main bot orchestrator
├── main.py                        # Entry point
├── requirements.txt               # Dependencies
└── README.md                      # This file
```

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd ict_trading_bot
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure the strategy (optional):
```bash
# Edit the configuration file
nano ict_trading_bot/config/strategy_config.yaml
```

## Usage

### Running a Backtest

Basic backtest with default settings:
```bash
python main.py backtest
```

Backtest with custom date range:
```bash
python main.py backtest --start-date 2024-01-01 --end-date 2024-06-30
```

Backtest with custom configuration:
```bash
python main.py backtest --config my_config.yaml
```

### Parameter Optimization

Run parameter optimization to find the best strategy settings:
```bash
python main.py optimize
```

This will test multiple parameter combinations and rank them by performance.

### Configuration

Edit `ict_trading_bot/config/strategy_config.yaml` to customize:

```yaml
# Trading Symbol
symbol: 'NQ=F'  # NASDAQ Futures

# Data Configuration
timeframe: '5m'
start_date: '2024-01-01'
end_date: '2024-12-31'

# Strategy Parameters
strategy:
  min_fvg_size: 0.0
  equal_threshold: 0.0002
  swing_window: 5
  bias_lookback: 20
  fvg_lookback: 10
  min_rr_ratio: 1.0
  max_rr_ratio: 3.0

# Trading Session (NY AM)
session:
  start_hour: 9
  start_minute: 30
  end_hour: 11
  end_minute: 0
```

## Strategy Details

### Step 1: Determine HTF Bias

The bot analyzes three key factors:

1. **Liquidity Delivery**
   - After taking sell-side liquidity (PDL) → Bullish bias
   - After taking buy-side liquidity (PDH) → Bearish bias

2. **FVG Respect/Disrespect**
   - Bullish: Respects bullish FVGs, disrespects bearish FVGs
   - Bearish: Respects bearish FVGs, disrespects bullish FVGs

3. **4-Hour Candle Direction**
   - Must align with the overall bias

### Step 2: Identify Rejection Levels

The bot identifies multiple types of rejection levels:
- Fair Value Gaps (5-minute minimum)
- Previous Day High/Low (PDH/PDL)
- Previous Week High/Low (PWH/PWL)
- London & Asia session highs/lows
- Equal highs/lows
- Intermediate highs/lows

### Step 3: Manipulation Leg & Inversion FVG

1. **Manipulation Leg**: The swing that hits the rejection level
2. **Inversion FVG**: Opposite-direction FVG within the manipulation leg
3. **Entry Signal**: Body closure through the Inversion FVG

### Step 4: Target Identification

Primary targets (in order of preference):
1. Unfilled 5-minute or 15-minute FVG
2. Relative equal highs/lows
3. Low resistance liquidity runs
4. Session highs/lows
5. PDH/PDL, PWH/PWL

### Step 5: Trade Execution

- **Entry**: Body closure through Inversion FVG
- **Stop Loss**: Below swing low (long) or above swing high (short)
  - Can be tightened to nearby FVG
- **Trade Management**:
  - Move stop to breakeven when internal high/low breaks
  - Risk/Reward: 1:1 to 1:3

## Output & Reports

After running a backtest, the bot generates:

1. **Text Report** (`backtest_report_TIMESTAMP.txt`)
   - Summary statistics
   - Profit & Loss metrics
   - Risk metrics (Sharpe, Sortino, Max Drawdown)
   - Streak analysis
   - Trade management stats

2. **Equity Curve** (`equity_curve_TIMESTAMP.png`)
   - Cumulative P&L chart
   - Drawdown visualization

3. **Trade Distribution** (`trade_distribution_TIMESTAMP.png`)
   - P&L histogram
   - Win/Loss pie chart
   - MFE vs MAE scatter plot
   - Trade duration distribution

4. **Trades CSV** (`trades_TIMESTAMP.csv`)
   - Detailed trade-by-trade results
   - Entry/exit prices and timestamps
   - P&L, MFE, MAE for each trade

All reports are saved in the `./reports` directory.

## Performance Metrics Explained

### Sharpe Ratio
Risk-adjusted return measure. Higher is better. Above 1.0 is good, above 2.0 is excellent.

### Sortino Ratio
Similar to Sharpe but only considers downside volatility. Better measure for trading strategies.

### Maximum Drawdown
Largest peak-to-trough decline. Important for risk management.

### Profit Factor
Ratio of gross profit to gross loss. Above 1.5 is good, above 2.0 is excellent.

### Kelly Criterion
Suggests optimal position sizing. Use 25-50% of Kelly for safety.

### MFE/MAE
- MFE (Maximum Favorable Excursion): How far price moved in your favor
- MAE (Maximum Adverse Excursion): How far price moved against you
- Useful for optimizing entries and stops

## Data Sources

The bot uses Yahoo Finance (via `yfinance`) to fetch historical NQ futures data. For live trading, you would need:
- Real-time data feed (e.g., Interactive Brokers, ThinkorSwim)
- Broker API for order execution

## Limitations & Disclaimers

⚠️ **IMPORTANT**: This is a backtesting and educational tool.

- **Not Financial Advice**: This bot is for educational purposes only
- **Past Performance**: Backtested results do not guarantee future performance
- **Data Limitations**: Yahoo Finance data may have gaps or inaccuracies
- **Slippage & Commissions**: Real trading involves costs not fully simulated
- **Live Trading**: Live trading functionality is not implemented

## Future Enhancements

Potential improvements:
- [ ] Live trading integration with broker APIs
- [ ] Real-time data feeds
- [ ] Machine learning for parameter optimization
- [ ] Additional ICT concepts (Order Blocks, Breaker Blocks, etc.)
- [ ] Multi-symbol support
- [ ] Walk-forward optimization
- [ ] Monte Carlo simulation
- [ ] Risk management module
- [ ] Alert system for trade signals

## Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues.

## License

MIT License - See LICENSE file for details

## Acknowledgments

- Strategy based on Inner Circle Trader (ICT) concepts
- Inspired by the YouTube video: [ICT Strategy Video](https://www.youtube.com/watch?v=n8FqECMb-9o)

## Support

For questions or issues, please open a GitHub issue or contact the maintainer.

---

**Disclaimer**: Trading futures involves substantial risk of loss and is not suitable for all investors. Past performance is not indicative of future results. Always conduct your own research and consider seeking advice from a licensed financial advisor before trading.
