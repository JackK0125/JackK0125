#!/usr/bin/env python3
"""
ICT Trading Bot - Main Entry Point

This is the main entry point for the ICT (Inner Circle Trader) Trading Bot.
It implements a systematic trading model for NQ (NASDAQ) futures based on:

1. Higher Time Frame Bias Determination
2. Key Rejection Level Identification
3. Manipulation Leg & Inversion FVG Detection
4. Target Identification (Draws on Liquidity)
5. Precision Trade Execution

Trading Rules:
- Only trade 9:30 AM - 11:00 AM ET (New York AM Session)
- Don't trade against equal highs/lows
- Follow the 4-hour candle direction
"""

import sys
import os
import argparse
from datetime import datetime, timedelta

# Add the source directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'ict_trading_bot', 'src'))

from bot import ICTTradingBot


def run_backtest(config_path=None, start_date=None, end_date=None):
    """
    Run a backtest with the ICT strategy

    Args:
        config_path: Path to configuration file
        start_date: Start date for backtest (YYYY-MM-DD)
        end_date: End date for backtest (YYYY-MM-DD)
    """
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║              ICT TRADING BOT - NQ Futures                     ║
    ║         Inner Circle Trader Strategy Implementation           ║
    ║                                                               ║
    ║  Strategy Components:                                         ║
    ║    ✓ HTF Bias Determination (Liquidity & FVG Analysis)       ║
    ║    ✓ Rejection Level Identification                          ║
    ║    ✓ Manipulation Leg Detection                              ║
    ║    ✓ Inversion FVG Entry Signals                             ║
    ║    ✓ Target Identification (Draws on Liquidity)              ║
    ║    ✓ Precision Trade Execution & Management                  ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)

    # Initialize bot
    bot = ICTTradingBot(config_path=config_path)

    # Override dates if provided
    if start_date:
        bot.config['start_date'] = start_date
    if end_date:
        bot.config['end_date'] = end_date

    print(f"\n{'='*80}")
    print("CONFIGURATION")
    print(f"{'='*80}")
    print(f"Symbol:           {bot.config['symbol']}")
    print(f"Timeframe:        {bot.config['timeframe']}")
    print(f"Start Date:       {bot.config['start_date']}")
    print(f"End Date:         {bot.config['end_date']}")
    print(f"Min R:R Ratio:    {bot.config['strategy']['min_rr_ratio']}")
    print(f"Max R:R Ratio:    {bot.config['strategy']['max_rr_ratio']}")
    print(f"Trading Hours:    {bot.config['session']['start_hour']}:{bot.config['session']['start_minute']:02d} - {bot.config['session']['end_hour']}:{bot.config['session']['end_minute']:02d} ET")
    print(f"{'='*80}\n")

    # Run backtest
    print("[STEP 1/2] Running Backtest...")
    try:
        results = bot.run_backtest()
    except Exception as e:
        print(f"\nError during backtest: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    # Generate reports
    print("\n[STEP 2/2] Generating Performance Reports...")
    try:
        bot.generate_report()
    except Exception as e:
        print(f"\nError generating reports: {str(e)}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "="*80)
    print("BACKTEST COMPLETE")
    print("="*80)
    print("\nCheck the 'reports' directory for detailed results and visualizations.")


def run_optimization(config_path=None):
    """
    Run parameter optimization

    Args:
        config_path: Path to configuration file
    """
    print("\n" + "="*80)
    print("PARAMETER OPTIMIZATION")
    print("="*80 + "\n")

    # Initialize bot
    bot = ICTTradingBot(config_path=config_path)

    # Define parameter grid
    param_grid = {
        'min_rr_ratio': [0.5, 1.0, 1.5, 2.0],
        'max_rr_ratio': [2.0, 3.0, 4.0, 5.0],
        'swing_window': [3, 5, 7],
        'equal_threshold': [0.0001, 0.0002, 0.0003, 0.0005]
    }

    print("Testing parameter combinations:")
    for param, values in param_grid.items():
        print(f"  {param}: {values}")
    print()

    # Run optimization
    results = bot.run_optimization(param_grid=param_grid)

    print("\n" + "="*80)
    print("OPTIMIZATION COMPLETE")
    print("="*80)
    print("\nBest parameters based on total P&L:")
    print(results.head(5).to_string())


def live_trading_mode(config_path=None):
    """
    Run bot in live trading mode (placeholder)

    Args:
        config_path: Path to configuration file
    """
    print("\n" + "="*80)
    print("LIVE TRADING MODE")
    print("="*80 + "\n")

    print("⚠️  WARNING: Live trading is not yet implemented!")
    print("\nLive trading would require:")
    print("  1. Connection to a broker API (Interactive Brokers, TD Ameritrade, etc.)")
    print("  2. Real-time data feed")
    print("  3. Order management system")
    print("  4. Risk management controls")
    print("\nFor now, please use backtest mode to test the strategy.")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='ICT Trading Bot - Inner Circle Trader Strategy for NQ Futures',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run backtest with default configuration
  python main.py backtest

  # Run backtest with custom dates
  python main.py backtest --start-date 2024-01-01 --end-date 2024-06-30

  # Run backtest with custom config file
  python main.py backtest --config my_config.yaml

  # Run parameter optimization
  python main.py optimize

  # Future: Live trading mode
  python main.py live
        """
    )

    parser.add_argument(
        'mode',
        choices=['backtest', 'optimize', 'live'],
        help='Trading bot mode'
    )

    parser.add_argument(
        '--config',
        type=str,
        default='./ict_trading_bot/config/strategy_config.yaml',
        help='Path to configuration file'
    )

    parser.add_argument(
        '--start-date',
        type=str,
        help='Start date for backtest (YYYY-MM-DD)'
    )

    parser.add_argument(
        '--end-date',
        type=str,
        help='End date for backtest (YYYY-MM-DD)'
    )

    args = parser.parse_args()

    # Execute based on mode
    if args.mode == 'backtest':
        run_backtest(
            config_path=args.config if os.path.exists(args.config) else None,
            start_date=args.start_date,
            end_date=args.end_date
        )
    elif args.mode == 'optimize':
        run_optimization(config_path=args.config if os.path.exists(args.config) else None)
    elif args.mode == 'live':
        live_trading_mode(config_path=args.config if os.path.exists(args.config) else None)


if __name__ == '__main__':
    main()
