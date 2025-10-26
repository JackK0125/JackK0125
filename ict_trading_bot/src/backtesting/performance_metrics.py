"""
Performance Metrics and Reporting
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime


class PerformanceMetrics:
    """
    Calculate and visualize trading performance metrics
    """

    def __init__(self, trades_df: pd.DataFrame):
        """
        Initialize Performance Metrics

        Args:
            trades_df: DataFrame with trade history
        """
        self.trades_df = trades_df

    def calculate_sharpe_ratio(self, risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sharpe Ratio

        Args:
            risk_free_rate: Annual risk-free rate (default: 2%)

        Returns:
            Sharpe ratio
        """
        if len(self.trades_df) == 0:
            return 0.0

        returns = self.trades_df['pnl_percentage'].values
        excess_returns = returns - (risk_free_rate / 252)  # Daily risk-free rate

        if np.std(excess_returns) == 0:
            return 0.0

        sharpe = np.mean(excess_returns) / np.std(excess_returns)
        return sharpe * np.sqrt(252)  # Annualized

    def calculate_sortino_ratio(self, risk_free_rate: float = 0.02) -> float:
        """
        Calculate Sortino Ratio (uses downside deviation)

        Args:
            risk_free_rate: Annual risk-free rate (default: 2%)

        Returns:
            Sortino ratio
        """
        if len(self.trades_df) == 0:
            return 0.0

        returns = self.trades_df['pnl_percentage'].values
        excess_returns = returns - (risk_free_rate / 252)

        # Calculate downside deviation
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) == 0:
            return float('inf')

        downside_deviation = np.std(downside_returns)
        if downside_deviation == 0:
            return 0.0

        sortino = np.mean(excess_returns) / downside_deviation
        return sortino * np.sqrt(252)  # Annualized

    def calculate_max_drawdown(self) -> Dict:
        """
        Calculate maximum drawdown

        Returns:
            Dictionary with drawdown metrics
        """
        if len(self.trades_df) == 0:
            return {'max_drawdown': 0.0, 'max_drawdown_pct': 0.0, 'recovery_trades': 0}

        # Calculate cumulative P&L
        cumulative_pnl = self.trades_df['pnl'].cumsum()

        # Calculate running maximum
        running_max = cumulative_pnl.expanding().max()

        # Calculate drawdown
        drawdown = cumulative_pnl - running_max

        max_drawdown = drawdown.min()
        max_drawdown_idx = drawdown.idxmin()

        # Calculate recovery period
        recovery_trades = 0
        if max_drawdown < 0:
            recovery_idx = cumulative_pnl[max_drawdown_idx:].ge(
                running_max.loc[max_drawdown_idx]
            ).idxmax()
            if recovery_idx:
                recovery_trades = recovery_idx - max_drawdown_idx

        # Calculate percentage drawdown
        peak_value = running_max.loc[max_drawdown_idx]
        max_drawdown_pct = (max_drawdown / peak_value * 100) if peak_value != 0 else 0

        return {
            'max_drawdown': max_drawdown,
            'max_drawdown_pct': max_drawdown_pct,
            'recovery_trades': recovery_trades,
            'drawdown_series': drawdown
        }

    def calculate_win_loss_streaks(self) -> Dict:
        """
        Calculate winning and losing streaks

        Returns:
            Dictionary with streak information
        """
        if len(self.trades_df) == 0:
            return {
                'max_win_streak': 0,
                'max_loss_streak': 0,
                'current_streak': 0,
                'current_streak_type': None
            }

        # Determine if each trade is a win or loss
        wins = (self.trades_df['pnl'] > 0).astype(int)

        # Calculate streaks
        max_win_streak = 0
        max_loss_streak = 0
        current_streak = 0
        current_streak_type = None

        win_streak = 0
        loss_streak = 0

        for win in wins:
            if win == 1:
                win_streak += 1
                loss_streak = 0
                max_win_streak = max(max_win_streak, win_streak)
            else:
                loss_streak += 1
                win_streak = 0
                max_loss_streak = max(max_loss_streak, loss_streak)

        # Current streak
        if wins.iloc[-1] == 1:
            current_streak = win_streak
            current_streak_type = 'winning'
        else:
            current_streak = loss_streak
            current_streak_type = 'losing'

        return {
            'max_win_streak': max_win_streak,
            'max_loss_streak': max_loss_streak,
            'current_streak': current_streak,
            'current_streak_type': current_streak_type
        }

    def calculate_expectancy(self) -> float:
        """
        Calculate trade expectancy (average P&L per trade)

        Returns:
            Expectancy value
        """
        if len(self.trades_df) == 0:
            return 0.0

        return self.trades_df['pnl'].mean()

    def calculate_kelly_criterion(self) -> float:
        """
        Calculate Kelly Criterion (optimal position sizing)

        Returns:
            Kelly percentage
        """
        if len(self.trades_df) == 0:
            return 0.0

        wins = self.trades_df[self.trades_df['pnl'] > 0]
        losses = self.trades_df[self.trades_df['pnl'] <= 0]

        if len(losses) == 0:
            return 1.0  # All wins

        win_rate = len(wins) / len(self.trades_df)
        avg_win = wins['pnl'].mean()
        avg_loss = abs(losses['pnl'].mean())

        if avg_loss == 0:
            return 0.0

        win_loss_ratio = avg_win / avg_loss

        kelly = win_rate - ((1 - win_rate) / win_loss_ratio)
        return max(0, min(kelly, 1))  # Clamp between 0 and 1

    def get_comprehensive_metrics(self) -> Dict:
        """
        Get all performance metrics

        Returns:
            Dictionary with all metrics
        """
        drawdown = self.calculate_max_drawdown()
        streaks = self.calculate_win_loss_streaks()

        return {
            'sharpe_ratio': self.calculate_sharpe_ratio(),
            'sortino_ratio': self.calculate_sortino_ratio(),
            'max_drawdown': drawdown['max_drawdown'],
            'max_drawdown_pct': drawdown['max_drawdown_pct'],
            'recovery_trades': drawdown['recovery_trades'],
            'max_win_streak': streaks['max_win_streak'],
            'max_loss_streak': streaks['max_loss_streak'],
            'current_streak': streaks['current_streak'],
            'current_streak_type': streaks['current_streak_type'],
            'expectancy': self.calculate_expectancy(),
            'kelly_criterion': self.calculate_kelly_criterion()
        }

    def plot_equity_curve(self, save_path: Optional[str] = None):
        """
        Plot equity curve

        Args:
            save_path: Path to save the plot (optional)
        """
        if len(self.trades_df) == 0:
            print("No trades to plot")
            return

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))

        # Cumulative P&L
        cumulative_pnl = self.trades_df['pnl'].cumsum()
        ax1.plot(range(len(cumulative_pnl)), cumulative_pnl, linewidth=2, color='#2E86AB')
        ax1.fill_between(range(len(cumulative_pnl)), cumulative_pnl, alpha=0.3, color='#2E86AB')
        ax1.set_title('Equity Curve', fontsize=16, fontweight='bold')
        ax1.set_xlabel('Trade Number', fontsize=12)
        ax1.set_ylabel('Cumulative P&L (points)', fontsize=12)
        ax1.grid(True, alpha=0.3)
        ax1.axhline(y=0, color='black', linestyle='--', linewidth=1)

        # Drawdown
        drawdown_data = self.calculate_max_drawdown()
        drawdown = drawdown_data['drawdown_series']
        ax2.fill_between(range(len(drawdown)), drawdown, alpha=0.5, color='#A23B72')
        ax2.plot(range(len(drawdown)), drawdown, linewidth=2, color='#A23B72')
        ax2.set_title('Drawdown', fontsize=16, fontweight='bold')
        ax2.set_xlabel('Trade Number', fontsize=12)
        ax2.set_ylabel('Drawdown (points)', fontsize=12)
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Equity curve saved to {save_path}")
        else:
            plt.show()

    def plot_trade_distribution(self, save_path: Optional[str] = None):
        """
        Plot distribution of trade results

        Args:
            save_path: Path to save the plot (optional)
        """
        if len(self.trades_df) == 0:
            print("No trades to plot")
            return

        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(14, 10))

        # P&L Distribution
        ax1.hist(self.trades_df['pnl'], bins=30, color='#2E86AB', alpha=0.7, edgecolor='black')
        ax1.axvline(x=0, color='red', linestyle='--', linewidth=2)
        ax1.set_title('P&L Distribution', fontsize=14, fontweight='bold')
        ax1.set_xlabel('P&L (points)', fontsize=11)
        ax1.set_ylabel('Frequency', fontsize=11)
        ax1.grid(True, alpha=0.3)

        # Win/Loss Pie Chart
        wins = len(self.trades_df[self.trades_df['pnl'] > 0])
        losses = len(self.trades_df[self.trades_df['pnl'] <= 0])
        ax2.pie([wins, losses], labels=['Wins', 'Losses'], autopct='%1.1f%%',
                colors=['#06A77D', '#D62246'], startangle=90)
        ax2.set_title('Win/Loss Ratio', fontsize=14, fontweight='bold')

        # MFE vs MAE
        ax3.scatter(self.trades_df['mae'], self.trades_df['mfe'], alpha=0.6, color='#F18F01')
        ax3.set_title('Max Favorable vs Max Adverse Excursion', fontsize=14, fontweight='bold')
        ax3.set_xlabel('Max Adverse Excursion (MAE)', fontsize=11)
        ax3.set_ylabel('Max Favorable Excursion (MFE)', fontsize=11)
        ax3.grid(True, alpha=0.3)

        # Trade Duration
        if 'entry_timestamp' in self.trades_df.columns and 'exit_timestamp' in self.trades_df.columns:
            durations = (self.trades_df['exit_timestamp'] - self.trades_df['entry_timestamp']).dt.total_seconds() / 60
            ax4.hist(durations, bins=30, color='#9B59B6', alpha=0.7, edgecolor='black')
            ax4.set_title('Trade Duration Distribution', fontsize=14, fontweight='bold')
            ax4.set_xlabel('Duration (minutes)', fontsize=11)
            ax4.set_ylabel('Frequency', fontsize=11)
            ax4.grid(True, alpha=0.3)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Trade distribution plot saved to {save_path}")
        else:
            plt.show()

    def generate_report(self, save_path: Optional[str] = None) -> str:
        """
        Generate a comprehensive text report

        Args:
            save_path: Path to save the report (optional)

        Returns:
            Report as string
        """
        metrics = self.get_comprehensive_metrics()

        report = f"""
{'='*80}
                    ICT TRADING BOT - BACKTEST REPORT
{'='*80}

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{'='*80}
SUMMARY STATISTICS
{'='*80}

Total Trades:              {len(self.trades_df)}
Winning Trades:            {len(self.trades_df[self.trades_df['pnl'] > 0])}
Losing Trades:             {len(self.trades_df[self.trades_df['pnl'] <= 0])}
Win Rate:                  {len(self.trades_df[self.trades_df['pnl'] > 0]) / len(self.trades_df) * 100:.2f}%

{'='*80}
PROFIT & LOSS
{'='*80}

Total P&L:                 {self.trades_df['pnl'].sum():.2f} points
Average P&L per Trade:     {self.trades_df['pnl'].mean():.2f} points
Median P&L:                {self.trades_df['pnl'].median():.2f} points

Average Win:               {self.trades_df[self.trades_df['pnl'] > 0]['pnl'].mean():.2f} points
Average Loss:              {abs(self.trades_df[self.trades_df['pnl'] <= 0]['pnl'].mean()):.2f} points

Largest Win:               {self.trades_df['pnl'].max():.2f} points
Largest Loss:              {self.trades_df['pnl'].min():.2f} points

{'='*80}
RISK METRICS
{'='*80}

Sharpe Ratio:              {metrics['sharpe_ratio']:.3f}
Sortino Ratio:             {metrics['sortino_ratio']:.3f}
Expectancy:                {metrics['expectancy']:.2f} points

Max Drawdown:              {metrics['max_drawdown']:.2f} points
Max Drawdown %:            {metrics['max_drawdown_pct']:.2f}%
Recovery Trades:           {metrics['recovery_trades']}

Kelly Criterion:           {metrics['kelly_criterion']:.2%}

{'='*80}
STREAKS
{'='*80}

Max Win Streak:            {metrics['max_win_streak']} trades
Max Loss Streak:           {metrics['max_loss_streak']} trades
Current Streak:            {metrics['current_streak']} {metrics['current_streak_type']} trades

{'='*80}
TRADE MANAGEMENT
{'='*80}

Breakeven Moves:           {len(self.trades_df[self.trades_df['breakeven_moved'] == True])} ({len(self.trades_df[self.trades_df['breakeven_moved'] == True]) / len(self.trades_df) * 100:.1f}%)
Stopped Out:               {len(self.trades_df[self.trades_df['status'] == 'stopped_out'])} ({len(self.trades_df[self.trades_df['status'] == 'stopped_out']) / len(self.trades_df) * 100:.1f}%)

Average MFE:               {self.trades_df['mfe'].mean():.2f} points
Average MAE:               {self.trades_df['mae'].mean():.2f} points

{'='*80}
        """

        if save_path:
            with open(save_path, 'w') as f:
                f.write(report)
            print(f"Report saved to {save_path}")

        return report
