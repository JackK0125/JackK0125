"""
Setup and Run ICT Trading Bot - Fixed Import Version

This script ensures all imports work correctly regardless of where you run it from.
"""

import sys
import os

# Add the src directory to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
src_path = os.path.join(project_root, 'ict_trading_bot', 'src')
sys.path.insert(0, src_path)

from datetime import datetime, timedelta

# Now imports will work
from bot import ICTTradingBot


def main():
    """Run a simple backtest example"""

    print("="*60)
    print("ICT Trading Bot - Simple Example")
    print("="*60 + "\n")

    # Create bot instance
    bot = ICTTradingBot()

    # Override configuration for a quick test
    bot.config['start_date'] = '2024-10-01'
    bot.config['end_date'] = '2024-10-25'
    bot.config['timeframe'] = '5m'

    print("Configuration:")
    print(f"  Symbol: {bot.config['symbol']}")
    print(f"  Period: {bot.config['start_date']} to {bot.config['end_date']}")
    print(f"  Timeframe: {bot.config['timeframe']}")
    print(f"  Min R:R: {bot.config['strategy']['min_rr_ratio']}")
    print(f"  Max R:R: {bot.config['strategy']['max_rr_ratio']}")
    print(f"  Trading Hours: {bot.config['session']['start_hour']}:{bot.config['session']['start_minute']:02d} - {bot.config['session']['end_hour']}:{bot.config['session']['end_minute']:02d} ET")
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
            print("\n✓ Reports saved to ./reports directory")
        else:
            print("⚠ No trades were executed during this period.")
            print("\nPossible reasons:")
            print("  - No valid setups met all criteria")
            print("  - Data quality issues")
            print("  - Strategy parameters too strict")
            print("\nTry:")
            print("  - Longer date range")
            print("  - Adjusted parameters")
            print("  - Different timeframe")

    except Exception as e:
        print(f"\n✗ Error: {str(e)}")
        print("\nCommon issues:")
        print("  1. No internet connection")
        print("  2. Yahoo Finance API limits")
        print("  3. Invalid date range")
        print("  4. Missing dependencies - run: pip install -r requirements.txt")

        import traceback
        print("\nFull error details:")
        traceback.print_exc()


if __name__ == '__main__':
    main()
