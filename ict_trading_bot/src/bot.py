"""
ICT Trading Bot - Main Orchestrator
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional
import yaml
import sys
import os
from datetime import datetime, timedelta

# Import using relative or absolute imports depending on how the module is run
try:
    # Try relative imports first (when used as package)
    from .data.data_fetcher import DataFetcher
    from .backtesting.backtest_engine import BacktestEngine
    from .backtesting.performance_metrics import PerformanceMetrics
except ImportError:
    # Fall back to absolute imports (when run directly)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    from data.data_fetcher import DataFetcher
    from backtesting.backtest_engine import BacktestEngine
    from backtesting.performance_metrics import PerformanceMetrics


class ICTTradingBot:
    """
    Main orchestrator for the ICT Trading Bot
    """

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the ICT Trading Bot

        Args:
            config_path: Path to configuration file (optional)
        """
        self.config = self._load_config(config_path)
        self.data_fetcher = DataFetcher(symbol=self.config.get('symbol', 'NQ=F'))
        self.backtest_engine = None
        self.results = None

    def _load_config(self, config_path: Optional[str]) -> Dict:
        """
        Load configuration from file or use defaults

        Args:
            config_path: Path to YAML config file

        Returns:
            Configuration dictionary
        """
        default_config = {
            'symbol': 'NQ=F',
            'timeframe': '5m',
            'start_date': (datetime.now() - timedelta(days=60)).strftime('%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d'),
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

        if config_path and os.path.exists(config_path):
            with open(config_path, 'r') as f:
                user_config = yaml.safe_load(f)
                # Merge with defaults
                default_config.update(user_config)

        return default_config

    def fetch_historical_data(self) -> tuple:
        """
        Fetch historical data for backtesting

        Returns:
            Tuple of (main_df, df_4h)
        """
        print(f"\nFetching data for {self.config['symbol']}...")
        print(f"Period: {self.config['start_date']} to {self.config['end_date']}")
        print(f"Timeframe: {self.config['timeframe']}")

        # Fetch main timeframe data
        df = self.data_fetcher.fetch_data(
            start_date=self.config['start_date'],
            end_date=self.config['end_date'],
            interval=self.config['timeframe']
        )

        # Fetch 4-hour data
        df_4h = self.data_fetcher.fetch_data(
            start_date=self.config['start_date'],
            end_date=self.config['end_date'],
            interval='1h'
        )
        df_4h = self.data_fetcher.resample_to_4h(df_4h)

        # Add previous session levels
        df = self.data_fetcher.add_previous_session_levels(df)
        df = self.data_fetcher.get_session_boundaries(df, 'london')
        df = self.data_fetcher.get_session_boundaries(df, 'asia')

        print(f"Data fetched successfully!")
        print(f"Main timeframe: {len(df)} candles")
        print(f"4-hour timeframe: {len(df_4h)} candles")

        return df, df_4h

    def run_backtest(self, df: Optional[pd.DataFrame] = None,
                    df_4h: Optional[pd.DataFrame] = None) -> Dict:
        """
        Run backtest

        Args:
            df: Main timeframe DataFrame (optional, will fetch if not provided)
            df_4h: 4-hour DataFrame (optional, will fetch if not provided)

        Returns:
            Backtest results dictionary
        """
        # Fetch data if not provided
        if df is None or df_4h is None:
            df, df_4h = self.fetch_historical_data()

        # Initialize backtest engine
        self.backtest_engine = BacktestEngine(config=self.config['strategy'])

        # Prepare data
        df_prepared = self.backtest_engine.prepare_data(df, df_4h)

        # Run backtest
        self.results = self.backtest_engine.run_backtest(
            df_prepared, df_4h,
            start_date=self.config['start_date'],
            end_date=self.config['end_date']
        )

        return self.results

    def generate_report(self, output_dir: str = './reports') -> None:
        """
        Generate comprehensive performance report

        Args:
            output_dir: Directory to save reports
        """
        if self.results is None:
            print("No backtest results available. Run backtest first.")
            return

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Generate performance metrics
        if len(self.results['trades']) > 0:
            metrics = PerformanceMetrics(self.results['trades'])

            # Generate text report
            report_path = os.path.join(output_dir, f'backtest_report_{timestamp}.txt')
            report = metrics.generate_report(save_path=report_path)
            print(report)

            # Generate equity curve
            equity_path = os.path.join(output_dir, f'equity_curve_{timestamp}.png')
            metrics.plot_equity_curve(save_path=equity_path)

            # Generate trade distribution plots
            distribution_path = os.path.join(output_dir, f'trade_distribution_{timestamp}.png')
            metrics.plot_trade_distribution(save_path=distribution_path)

            # Save trades to CSV
            trades_path = os.path.join(output_dir, f'trades_{timestamp}.csv')
            self.results['trades'].to_csv(trades_path, index=False)
            print(f"\nTrades saved to {trades_path}")

            print(f"\nAll reports saved to {output_dir}/")
        else:
            print("No trades were executed in the backtest.")

    def run_optimization(self, df: Optional[pd.DataFrame] = None,
                        df_4h: Optional[pd.DataFrame] = None,
                        param_grid: Optional[Dict] = None) -> pd.DataFrame:
        """
        Run parameter optimization

        Args:
            df: Main timeframe DataFrame (optional)
            df_4h: 4-hour DataFrame (optional)
            param_grid: Parameter grid to test (optional)

        Returns:
            Optimization results DataFrame
        """
        # Fetch data if not provided
        if df is None or df_4h is None:
            df, df_4h = self.fetch_historical_data()

        # Initialize backtest engine
        self.backtest_engine = BacktestEngine(config=self.config['strategy'])

        # Prepare data once (reuse for all optimization runs)
        df_prepared = self.backtest_engine.prepare_data(df.copy(), df_4h)

        # Run optimization
        results_df = self.backtest_engine.run_parameter_optimization(
            df_prepared, df_4h, param_grid
        )

        # Save results
        output_path = f"./optimization_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        results_df.to_csv(output_path, index=False)
        print(f"\nOptimization results saved to {output_path}")

        return results_df

    def get_trade_summary(self) -> pd.DataFrame:
        """
        Get summary of all trades

        Returns:
            DataFrame with trade summary
        """
        if self.results is None or len(self.results['trades']) == 0:
            return pd.DataFrame()

        return self.results['trades']

    def get_statistics(self) -> Dict:
        """
        Get trading statistics

        Returns:
            Dictionary with statistics
        """
        if self.results is None:
            return {}

        return self.results['statistics']


def main():
    """Main entry point for the bot"""
    print("""
    ╔═══════════════════════════════════════════════════════════════╗
    ║                                                               ║
    ║              ICT TRADING BOT - NQ Futures                     ║
    ║         Inner Circle Trader Strategy Implementation           ║
    ║                                                               ║
    ╚═══════════════════════════════════════════════════════════════╝
    """)

    # Initialize bot
    config_path = './ict_trading_bot/config/strategy_config.yaml'
    bot = ICTTradingBot(config_path=config_path if os.path.exists(config_path) else None)

    # Run backtest
    print("\n[1/2] Running backtest...")
    results = bot.run_backtest()

    # Generate reports
    print("\n[2/2] Generating reports...")
    bot.generate_report()

    print("\n" + "="*80)
    print("ICT TRADING BOT - EXECUTION COMPLETE")
    print("="*80)


if __name__ == "__main__":
    main()
