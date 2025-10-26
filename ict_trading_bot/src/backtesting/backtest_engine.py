"""
Backtesting Engine for ICT Trading Strategy
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from strategy.fvg_detector import FVGDetector
from strategy.liquidity_detector import LiquidityDetector
from strategy.bias_detector import BiasDetector
from strategy.manipulation_detector import ManipulationDetector
from strategy.target_identifier import TargetIdentifier
from execution.trade_executor import TradeExecutor


class BacktestEngine:
    """
    Comprehensive backtesting engine for the ICT trading strategy
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Backtest Engine

        Args:
            config: Configuration dictionary with strategy parameters
        """
        self.config = config or self._get_default_config()

        # Initialize strategy components
        self.fvg_detector = FVGDetector(min_gap_size=self.config.get('min_fvg_size', 0.0))
        self.liquidity_detector = LiquidityDetector(
            equal_threshold=self.config.get('equal_threshold', 0.0002)
        )
        self.bias_detector = BiasDetector()
        self.manipulation_detector = ManipulationDetector()
        self.target_identifier = TargetIdentifier()
        self.trade_executor = TradeExecutor(
            min_rr_ratio=self.config.get('min_rr_ratio', 1.0),
            max_rr_ratio=self.config.get('max_rr_ratio', 3.0)
        )

        # Backtest state
        self.current_bias = None
        self.active_setup = None
        self.results = []

    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            'min_fvg_size': 0.0,
            'equal_threshold': 0.0002,
            'min_rr_ratio': 1.0,
            'max_rr_ratio': 3.0,
            'swing_window': 5,
            'bias_lookback': 20,
            'fvg_lookback': 10
        }

    def prepare_data(self, df: pd.DataFrame, df_4h: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Prepare data by detecting all indicators

        Args:
            df: Main timeframe DataFrame
            df_4h: 4-hour timeframe DataFrame (optional)

        Returns:
            Prepared DataFrame with all indicators
        """
        print("Preparing data for backtesting...")

        # Detect FVGs
        print("  Detecting Fair Value Gaps...")
        df = self.fvg_detector.detect_fvgs(df)
        df = self.fvg_detector.check_fvg_filled(df)
        df = self.fvg_detector.check_fvg_respect(df, lookback=self.config['fvg_lookback'])

        # Detect liquidity
        print("  Detecting liquidity pools...")
        df = self.liquidity_detector.detect_swing_points(df, swing_window=self.config['swing_window'])
        df = self.liquidity_detector.detect_equal_highs(df, lookback=self.config['bias_lookback'])
        df = self.liquidity_detector.detect_equal_lows(df, lookback=self.config['bias_lookback'])
        df = self.liquidity_detector.detect_liquidity_sweep(df)
        df = self.liquidity_detector.get_session_highs_lows(df)
        df = self.liquidity_detector.detect_low_resistance_liquidity(df)

        print("Data preparation complete!")
        return df

    def run_backtest(self, df: pd.DataFrame, df_4h: Optional[pd.DataFrame] = None,
                    start_date: Optional[str] = None,
                    end_date: Optional[str] = None) -> Dict:
        """
        Run the backtest

        Args:
            df: Prepared DataFrame with all indicators
            df_4h: 4-hour timeframe DataFrame (optional)
            start_date: Start date for backtest (optional)
            end_date: End date for backtest (optional)

        Returns:
            Dictionary with backtest results
        """
        print("\nRunning backtest...")
        print(f"Total candles: {len(df)}")

        # Filter by date range if provided
        if start_date:
            df = df[df.index >= start_date]
        if end_date:
            df = df[df.index <= end_date]

        print(f"Backtest period: {df.index[0]} to {df.index[-1]}")

        # Main backtest loop
        for i in range(100, len(df)):  # Start at 100 to have enough history
            current_time = df.index[i]

            # Critical Rule #2: Only trade during NY AM session (9:30 AM - 11:00 AM ET)
            if not self.trade_executor.check_ny_session_time(current_time):
                continue

            # If we have an active trade, manage it
            if self.trade_executor.active_trade is not None:
                exit_reason = self.trade_executor.manage_trade(
                    df, i, self.active_setup.get('manipulation_leg') if self.active_setup else {}
                )
                if exit_reason:
                    print(f"  Trade closed at {current_time}: {exit_reason}")
                    self.active_setup = None
                continue

            # Step 1: Determine HTF Bias
            bias_signals = self.bias_detector.determine_bias(df, i, df_4h)
            overall_bias = bias_signals['overall_bias']

            if overall_bias == 'neutral':
                continue

            # Critical Rule #1: Don't trade against equal highs/lows
            if not self.bias_detector.check_bias_against_equal_highs_lows(df, i, overall_bias):
                continue

            # Critical Rule #3: Follow the 4-hour candle
            if df_4h is not None and bias_signals['four_hour_bias'] is not None:
                if bias_signals['four_hour_bias'] != overall_bias:
                    continue

            # Step 2: Identify Rejection Levels
            rejection_levels = self.manipulation_detector.identify_rejection_levels(
                df, i, overall_bias
            )

            if not rejection_levels:
                continue

            # Step 3: Look for Manipulation Leg hitting a rejection level
            manipulation_leg = None
            best_rejection_level = None

            for rejection_level in rejection_levels[:3]:  # Check top 3 rejection levels
                manip = self.manipulation_detector.identify_manipulation_leg(
                    df, rejection_level, i, overall_bias
                )
                if manip and manip['rejection_level_hit']:
                    manipulation_leg = manip
                    best_rejection_level = rejection_level
                    break

            if manipulation_leg is None:
                continue

            # Step 4: Find Inversion FVG within manipulation leg
            ifvg = self.manipulation_detector.find_inversion_fvg(
                df, manipulation_leg
            )

            if ifvg is None:
                continue

            # Step 5: Check for IFVG inversion (entry signal)
            if not self.manipulation_detector.check_ifvg_inversion(df, ifvg, i):
                continue

            # Step 6: Identify Targets
            entry_price = df['close'].iloc[i]
            stop_loss = self.trade_executor.calculate_stop_loss(
                df, manipulation_leg, entry_price, overall_bias
            )

            targets = self.target_identifier.identify_targets(
                df, i, entry_price, overall_bias,
                min_rr_ratio=self.config['min_rr_ratio']
            )

            if not targets:
                continue

            # Step 7: Enter Trade
            trade = self.trade_executor.enter_trade(
                df, i, manipulation_leg, targets, overall_bias
            )

            if trade:
                print(f"\n  Trade entered at {current_time}")
                print(f"    Direction: {trade.direction}")
                print(f"    Entry: {trade.entry_price:.2f}")
                print(f"    Stop: {trade.stop_loss:.2f}")
                print(f"    Targets: {len(trade.targets)}")

                # Store active setup for trade management
                self.active_setup = {
                    'bias': overall_bias,
                    'manipulation_leg': manipulation_leg,
                    'ifvg': ifvg,
                    'rejection_level': best_rejection_level
                }

        # Get final statistics
        stats = self.trade_executor.get_trade_statistics()
        trades_df = self.trade_executor.get_trades_df()

        print(f"\n{'='*60}")
        print("BACKTEST COMPLETE")
        print(f"{'='*60}")
        print(f"Total Trades: {stats['total_trades']}")
        print(f"Winning Trades: {stats['winning_trades']}")
        print(f"Losing Trades: {stats['losing_trades']}")
        print(f"Win Rate: {stats['win_rate']:.2f}%")
        print(f"Total P&L: {stats['total_pnl']:.2f} points")
        print(f"Average Win: {stats['avg_win']:.2f} points")
        print(f"Average Loss: {stats['avg_loss']:.2f} points")
        print(f"Profit Factor: {stats['profit_factor']:.2f}")
        print(f"Max Win: {stats['max_win']:.2f} points")
        print(f"Max Loss: {stats['max_loss']:.2f} points")
        print(f"{'='*60}\n")

        return {
            'statistics': stats,
            'trades': trades_df,
            'config': self.config
        }

    def run_parameter_optimization(self, df: pd.DataFrame,
                                   df_4h: Optional[pd.DataFrame] = None,
                                   param_grid: Optional[Dict] = None) -> pd.DataFrame:
        """
        Run parameter optimization

        Args:
            df: Prepared DataFrame
            df_4h: 4-hour DataFrame
            param_grid: Dictionary of parameters to test

        Returns:
            DataFrame with optimization results
        """
        if param_grid is None:
            param_grid = {
                'min_rr_ratio': [1.0, 1.5, 2.0],
                'max_rr_ratio': [2.0, 3.0, 4.0],
                'swing_window': [3, 5, 7],
                'equal_threshold': [0.0001, 0.0002, 0.0003]
            }

        print("\nRunning parameter optimization...")
        print(f"Testing {len(param_grid)} parameter combinations\n")

        results = []

        # Generate all parameter combinations
        import itertools
        keys = param_grid.keys()
        values = param_grid.values()
        combinations = list(itertools.product(*values))

        for i, combo in enumerate(combinations):
            config = dict(zip(keys, combo))
            print(f"Testing combination {i+1}/{len(combinations)}: {config}")

            # Create new backtest engine with this config
            engine = BacktestEngine(config)
            prepared_df = engine.prepare_data(df.copy(), df_4h)

            # Run backtest
            result = engine.run_backtest(prepared_df, df_4h)

            # Store results
            result_row = config.copy()
            result_row.update(result['statistics'])
            results.append(result_row)

        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('total_pnl', ascending=False)

        print("\n" + "="*60)
        print("OPTIMIZATION COMPLETE")
        print("="*60)
        print("\nTop 5 configurations by total P&L:")
        print(results_df.head())

        return results_df
