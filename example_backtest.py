#!/usr/bin/env python3
"""
Simple Example - Run a quick backtest

This is a minimal example showing how to use the ICT Trading Bot programmatically.
"""

import sys
import os
from datetime import datetime, timedelta

# Add source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ict_trading_bot', 'src'))

from bot import ICTTradingBot


def main():
    """Run a simple backtest example"""

    print("="*60)
    print("ICT Trading Bot - Simple Example")
    print("="*60 + "\n")

    # Create bot instance with custom configuration
    config = {
        'symbol': 'NQ=F',
        'timeframe': '5m',
        'start_date': '2024-10-01',
        'end_date': '2024-10-25',
        'strategy': {
            'min_fvg_size': 0.0,
            'equal_threshold': 0.0002,
            'min_rr_ratio': 1.0,
            'max_rr_ratio': 3.0,
            'swing_window': 5,
            'bias_lookback': 20,
            'fvg_lookback': 10
        },
        'session': {
            'start_hour': 9,
            'start_minute': 30,
            'end_hour': 11,
            'end_minute': 0
        }
    }

    # Initialize bot
    bot = ICTTradingBot()
    bot.config = config

    print("Configuration:")
    print(f"  Symbol: {config['symbol']}")
    print(f"  Period: {config['start_date']} to {config['end_date']}")
    print(f"  Min R:R: {config['strategy']['min_rr_ratio']}")
    print(f"  Max R:R: {config['strategy']['max_rr_ratio']}")
    print()

    # Run backtest
    print("Fetching data and running backtest...")
    print("(This may take a minute...)\n")

    try:
        results = bot.run_backtest()

        # Print results
        stats = results['statistics']
        print("\n" + "="*60)
        print("RESULTS")
        print("="*60)
        print(f"Total Trades:       {stats['total_trades']}")
        print(f"Winning Trades:     {stats['winning_trades']}")
        print(f"Losing Trades:      {stats['losing_trades']}")
        print(f"Win Rate:           {stats['win_rate']:.2f}%")
        print(f"Total P&L:          {stats['total_pnl']:.2f} points")
        print(f"Profit Factor:      {stats['profit_factor']:.2f}")
        print(f"Average Win:        {stats['avg_win']:.2f} points")
        print(f"Average Loss:       {stats['avg_loss']:.2f} points")
        print("="*60 + "\n")

        # Generate reports
        if stats['total_trades'] > 0:
            print("Generating reports...")
            bot.generate_report()
            print("\nReports saved to ./reports directory")
        else:
            print("No trades were executed during this period.")
            print("\nPossible reasons:")
            print("  - No valid setups met all criteria")
            print("  - Data quality issues")
            print("  - Strategy parameters too strict")
            print("\nTry:")
            print("  - Longer date range")
            print("  - Adjusted parameters")
            print("  - Different timeframe")

    except Exception as e:
        print(f"\nError: {str(e)}")
        print("\nCommon issues:")
        print("  1. No internet connection")
        print("  2. Yahoo Finance API limits")
        print("  3. Invalid date range")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
