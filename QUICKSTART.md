# Quick Start Guide - ICT Trading Bot

Get started with the ICT Trading Bot in 5 minutes!

## 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

**Note**: If you encounter issues with `ta-lib`, you can remove it from `requirements.txt` as it's not currently used in the core functionality.

## 2. Run Your First Backtest

Run a backtest with default settings (last 60 days):

```bash
python main.py backtest
```

You should see output like:
```
╔═══════════════════════════════════════════════════════════════╗
║              ICT TRADING BOT - NQ Futures                     ║
║         Inner Circle Trader Strategy Implementation           ║
╚═══════════════════════════════════════════════════════════════╝

Fetching data for NQ=F...
Period: 2024-XX-XX to 2024-XX-XX
...
```

## 3. View Your Results

After the backtest completes, check the `reports/` directory:

- `backtest_report_TIMESTAMP.txt` - Full performance report
- `equity_curve_TIMESTAMP.png` - Visual equity curve
- `trade_distribution_TIMESTAMP.png` - Trade analysis charts
- `trades_TIMESTAMP.csv` - Detailed trade log

## 4. Customize Your Backtest

### Test a Specific Date Range

```bash
python main.py backtest --start-date 2024-01-01 --end-date 2024-06-30
```

### Modify Strategy Parameters

Edit `ict_trading_bot/config/strategy_config.yaml`:

```yaml
strategy:
  min_rr_ratio: 1.5  # Increase minimum risk/reward
  max_rr_ratio: 4.0  # Increase maximum risk/reward
  swing_window: 7    # Use more candles for swing detection
```

Then run:
```bash
python main.py backtest
```

## 5. Optimize Parameters

Find the best parameter combinations:

```bash
python main.py optimize
```

This will test multiple parameter combinations and show you the best performers.

## Common Issues

### 1. No Data Fetched

**Problem**: `ValueError: No data fetched for NQ=F`

**Solution**:
- Yahoo Finance may have API limits. Try:
  - Shorter date range
  - Different timeframe (e.g., '15m' instead of '5m')
  - Wait a few minutes and try again

### 2. Import Errors

**Problem**: `ModuleNotFoundError: No module named 'pandas'`

**Solution**:
```bash
pip install -r requirements.txt
```

### 3. TA-Lib Installation Issues

**Problem**: `ERROR: Failed building wheel for TA-Lib`

**Solution**:
Remove `ta-lib>=0.4.28` from `requirements.txt` - it's not currently used.

## Understanding Your Results

### Key Metrics to Watch

1. **Win Rate**: Percentage of winning trades
   - Good: > 40%
   - Excellent: > 50%

2. **Profit Factor**: Total wins / Total losses
   - Good: > 1.5
   - Excellent: > 2.0

3. **Sharpe Ratio**: Risk-adjusted returns
   - Good: > 1.0
   - Excellent: > 2.0

4. **Max Drawdown**: Largest peak-to-trough decline
   - Lower is better
   - Should be manageable relative to total profit

### Sample Good Results

```
Total Trades:              50
Winning Trades:            28
Win Rate:                  56.00%
Total P&L:                 +250.50 points
Profit Factor:             2.15
Sharpe Ratio:              1.85
Max Drawdown:              -45.25 points
```

## Next Steps

1. **Analyze Your Trades**:
   - Open `trades_TIMESTAMP.csv` in Excel/Google Sheets
   - Look for patterns in winning vs losing trades

2. **Optimize Parameters**:
   - Run `python main.py optimize`
   - Test the best parameters from different time periods

3. **Test Different Markets**:
   - Edit `symbol: 'NQ=F'` in config to try other futures
   - ES (S&P 500), YM (Dow), RTY (Russell 2000)

4. **Longer Backtests**:
   - Test over 6+ months to validate strategy robustness
   - Check performance in different market conditions

## Tips for Better Results

1. **Focus on High-Quality Setups**
   - Increase `min_rr_ratio` to 1.5 or 2.0
   - Only trade when all bias signals align

2. **Reduce False Signals**
   - Increase `swing_window` to 7 or 9
   - Tighten `equal_threshold` to reduce noise

3. **Stick to the Rules**
   - Only trade 9:30 AM - 11:00 AM ET
   - Don't trade against equal highs/lows
   - Follow the 4-hour candle

## Getting Help

- Read the full README.md for detailed documentation
- Check the source code comments for implementation details
- Open an issue on GitHub for bugs or questions

Happy Trading! 🚀

---

**Remember**: This is a backtesting tool for educational purposes. Always paper trade before risking real capital.
