#!/usr/bin/env python3
"""
Standalone ICT Trading Bot Runner
This script sets up all paths correctly before importing anything.
"""

import sys
import os

# CRITICAL: Set up Python path BEFORE any imports
project_root = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(project_root, 'ict_trading_bot', 'src')

# Add src directory to path
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

# Change working directory to src
os.chdir(src_dir)

print(f"Working directory: {os.getcwd()}")
print(f"Python path includes: {src_dir}")
print()

# NOW we can import (after path is set up)
from datetime import datetime, timedelta

try:
    from bot import ICTTradingBot
except ImportError as e:
    print(f"Error importing bot: {e}")
    print("\nTrying alternative import method...")

    # Alternative: Add each subdirectory
    for subdir in ['data', 'strategy', 'execution', 'backtesting']:
        subdir_path = os.path.join(src_dir, subdir)
        if subdir_path not in sys.path:
            sys.path.insert(0, subdir_path)

    from bot import ICTTradingBot


def main():
    """Run a simple backtest"""

    print("="*70)
    print("ICT TRADING BOT - NQ Futures Strategy Backtest")
    print("="*70)
    print()

    # Create bot instance
    print("Initializing bot...")
    bot = ICTTradingBot()

    # Configure for recent dates
    bot.config['start_date'] = '2024-10-01'
    bot.config['end_date'] = '2024-10-25'
    bot.config['timeframe'] = '5m'

    print("Configuration:")
    print(f"  Symbol:          {bot.config['symbol']}")
    print(f"  Timeframe:       {bot.config['timeframe']}")
    print(f"  Date Range:      {bot.config['start_date']} to {bot.config['end_date']}")
    print(f"  Min Risk/Reward: {bot.config['strategy']['min_rr_ratio']}")
    print(f"  Max Risk/Reward: {bot.config['strategy']['max_rr_ratio']}")
    print(f"  Trading Hours:   {bot.config['session']['start_hour']}:{bot.config['session']['start_minute']:02d} - {bot.config['session']['end_hour']}:{bot.config['session']['end_minute']:02d} ET")
    print()

    # Run backtest
    print("-"*70)
    print("Starting backtest...")
    print("-"*70)
    print()

    try:
        results = bot.run_backtest()

        # Print results
        stats = results['statistics']

        print()
        print("="*70)
        print("BACKTEST RESULTS")
        print("="*70)
        print()
        print(f"  Total Trades:        {stats['total_trades']}")
        print(f"  Winning Trades:      {stats['winning_trades']}")
        print(f"  Losing Trades:       {stats['losing_trades']}")
        print(f"  Win Rate:            {stats['win_rate']:.1f}%")
        print()
        print(f"  Total P&L:           {stats['total_pnl']:.2f} points")
        print(f"  Average Win:         {stats['avg_win']:.2f} points")
        print(f"  Average Loss:        {stats['avg_loss']:.2f} points")
        print(f"  Profit Factor:       {stats['profit_factor']:.2f}")
        print()
        print(f"  Max Win:             {stats['max_win']:.2f} points")
        print(f"  Max Loss:            {stats['max_loss']:.2f} points")
        print()
        print("="*70)
        print()

        # Generate reports if we have trades
        if stats['total_trades'] > 0:
            print("Generating detailed reports...")

            # Change back to project root for reports
            os.chdir(project_root)
            bot.generate_report()

            print()
            print("✓ Reports saved to ./reports directory")
            print()
            print("Files generated:")
            print("  - backtest_report_*.txt (detailed statistics)")
            print("  - equity_curve_*.png (visual performance)")
            print("  - trade_distribution_*.png (trade analysis)")
            print("  - trades_*.csv (complete trade log)")
        else:
            print("⚠ No trades were executed during this period.")
            print()
            print("Possible reasons:")
            print("  1. No valid setups met all the ICT criteria")
            print("  2. Yahoo Finance data quality issues")
            print("  3. Strategy parameters too restrictive")
            print()
            print("Suggestions:")
            print("  - Try a longer date range (e.g., 2-3 months)")
            print("  - Check data availability for NQ=F on Yahoo Finance")
            print("  - Adjust strategy parameters in config file")
            print("  - Try a different timeframe (e.g., 15m)")

    except Exception as e:
        print()
        print("="*70)
        print("ERROR OCCURRED")
        print("="*70)
        print()
        print(f"Error: {str(e)}")
        print()
        print("Common issues:")
        print("  1. Internet connection required for data fetching")
        print("  2. Yahoo Finance API rate limits")
        print("  3. Invalid date range or symbol")
        print("  4. Missing dependencies")
        print()
        print("Solutions:")
        print("  1. Check internet connection")
        print("  2. Wait a few minutes and try again")
        print("  3. Install dependencies: pip install -r requirements.txt")
        print("  4. Verify symbol 'NQ=F' is available on Yahoo Finance")
        print()

        # Show detailed error
        import traceback
        print("Detailed error trace:")
        print("-"*70)
        traceback.print_exc()
        print("-"*70)


if __name__ == '__main__':
    main()
