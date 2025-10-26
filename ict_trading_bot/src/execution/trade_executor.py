"""
Trade Executor - Handles trade execution and management
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
from datetime import datetime


class Trade:
    """Represents a single trade"""

    def __init__(self, entry_index: int, entry_price: float, direction: str,
                 stop_loss: float, targets: List[Dict], size: float = 1.0):
        """
        Initialize a trade

        Args:
            entry_index: Index where trade was entered
            entry_price: Entry price
            direction: 'long' or 'short'
            stop_loss: Initial stop loss price
            targets: List of target dictionaries
            size: Position size (default: 1.0)
        """
        self.entry_index = entry_index
        self.entry_price = entry_price
        self.direction = direction
        self.stop_loss = stop_loss
        self.initial_stop_loss = stop_loss
        self.targets = targets
        self.size = size
        self.status = 'open'  # 'open', 'closed', 'stopped_out'
        self.exit_index = None
        self.exit_price = None
        self.exit_reason = None
        self.pnl = 0.0
        self.pnl_percentage = 0.0
        self.max_favorable_excursion = 0.0
        self.max_adverse_excursion = 0.0
        self.breakeven_moved = False
        self.internal_broken = False
        self.entry_timestamp = None
        self.exit_timestamp = None

    def update_mfe_mae(self, current_price: float):
        """
        Update Maximum Favorable/Adverse Excursion

        Args:
            current_price: Current market price
        """
        if self.direction == 'long':
            favorable = current_price - self.entry_price
            adverse = self.entry_price - current_price
        else:
            favorable = self.entry_price - current_price
            adverse = current_price - self.entry_price

        self.max_favorable_excursion = max(self.max_favorable_excursion, favorable)
        self.max_adverse_excursion = max(self.max_adverse_excursion, adverse)

    def calculate_pnl(self, exit_price: float) -> float:
        """
        Calculate P&L for the trade

        Args:
            exit_price: Exit price

        Returns:
            P&L in points
        """
        if self.direction == 'long':
            pnl = (exit_price - self.entry_price) * self.size
        else:
            pnl = (self.entry_price - exit_price) * self.size

        return pnl

    def to_dict(self) -> Dict:
        """Convert trade to dictionary"""
        return {
            'entry_index': self.entry_index,
            'entry_price': self.entry_price,
            'entry_timestamp': self.entry_timestamp,
            'exit_index': self.exit_index,
            'exit_price': self.exit_price,
            'exit_timestamp': self.exit_timestamp,
            'direction': self.direction,
            'stop_loss': self.stop_loss,
            'initial_stop_loss': self.initial_stop_loss,
            'status': self.status,
            'exit_reason': self.exit_reason,
            'pnl': self.pnl,
            'pnl_percentage': self.pnl_percentage,
            'mfe': self.max_favorable_excursion,
            'mae': self.max_adverse_excursion,
            'breakeven_moved': self.breakeven_moved,
            'size': self.size
        }


class TradeExecutor:
    """
    Executes and manages trades based on ICT strategy signals
    """

    def __init__(self, min_rr_ratio: float = 1.0, max_rr_ratio: float = 3.0):
        """
        Initialize Trade Executor

        Args:
            min_rr_ratio: Minimum risk/reward ratio (default: 1.0)
            max_rr_ratio: Maximum risk/reward ratio (default: 3.0)
        """
        self.min_rr_ratio = min_rr_ratio
        self.max_rr_ratio = max_rr_ratio
        self.active_trade = None
        self.closed_trades = []

    def check_entry_signal(self, df: pd.DataFrame, current_index: int,
                          manipulation_leg: Dict, ifvg: Dict, bias: str) -> bool:
        """
        Check if entry conditions are met

        Args:
            df: DataFrame with price data
            current_index: Current position
            manipulation_leg: Manipulation leg details
            ifvg: Inversion FVG details
            bias: Market bias

        Returns:
            True if entry signal is valid
        """
        if manipulation_leg is None or ifvg is None:
            return False

        # Check if we're within the manipulation leg or shortly after
        if current_index < manipulation_leg['end_index']:
            return False

        # Check if IFVG has been inverted
        current_close = df['close'].iloc[current_index]

        if bias == 'bullish':
            # For long, need close above bearish IFVG
            return current_close > ifvg['top']
        else:
            # For short, need close below bullish IFVG
            return current_close < ifvg['bottom']

    def calculate_stop_loss(self, df: pd.DataFrame, manipulation_leg: Dict,
                           entry_price: float, bias: str,
                           use_fvg_stop: bool = True) -> float:
        """
        Calculate stop loss placement

        Args:
            df: DataFrame with price data
            manipulation_leg: Manipulation leg details
            entry_price: Entry price
            bias: Trade direction
            use_fvg_stop: Whether to use nearby FVG for stop (default: True)

        Returns:
            Stop loss price
        """
        if bias == 'bullish':
            # For long, stop below the manipulation swing low
            base_stop = manipulation_leg['swing_low']

            # Optional: tighten stop to nearby FVG
            if use_fvg_stop:
                # Look for bearish FVG near the swing low
                for i in range(manipulation_leg['start_index'],
                              manipulation_leg['end_index'] + 1):
                    if df['bearish_fvg'].iloc[i]:
                        fvg_bottom = df['fvg_bottom'].iloc[i]
                        # Use FVG if it's between entry and swing low
                        if fvg_bottom > base_stop and fvg_bottom < entry_price:
                            return fvg_bottom

            # Add small buffer below swing low
            return base_stop - (entry_price - base_stop) * 0.05

        else:
            # For short, stop above the manipulation swing high
            base_stop = manipulation_leg['swing_high']

            # Optional: tighten stop to nearby FVG
            if use_fvg_stop:
                # Look for bullish FVG near the swing high
                for i in range(manipulation_leg['start_index'],
                              manipulation_leg['end_index'] + 1):
                    if df['bullish_fvg'].iloc[i]:
                        fvg_top = df['fvg_top'].iloc[i]
                        # Use FVG if it's between entry and swing high
                        if fvg_top < base_stop and fvg_top > entry_price:
                            return fvg_top

            # Add small buffer above swing high
            return base_stop + (base_stop - entry_price) * 0.05

    def enter_trade(self, df: pd.DataFrame, current_index: int,
                   manipulation_leg: Dict, targets: List[Dict],
                   bias: str) -> Optional[Trade]:
        """
        Enter a new trade

        Args:
            df: DataFrame with price data
            current_index: Current position
            manipulation_leg: Manipulation leg details
            targets: List of targets
            bias: Trade direction

        Returns:
            Trade object or None
        """
        if self.active_trade is not None:
            return None

        entry_price = df['close'].iloc[current_index]
        direction = 'long' if bias == 'bullish' else 'short'

        # Calculate stop loss
        stop_loss = self.calculate_stop_loss(df, manipulation_leg, entry_price, bias)

        # Filter targets by risk/reward ratio
        valid_targets = []
        risk = abs(entry_price - stop_loss)

        for target in targets:
            reward = abs(target['level'] - entry_price)
            rr_ratio = reward / risk if risk > 0 else 0

            if self.min_rr_ratio <= rr_ratio <= self.max_rr_ratio:
                target['rr_ratio'] = rr_ratio
                valid_targets.append(target)

        if not valid_targets:
            return None

        # Create trade
        trade = Trade(
            entry_index=current_index,
            entry_price=entry_price,
            direction=direction,
            stop_loss=stop_loss,
            targets=valid_targets,
            size=1.0
        )

        trade.entry_timestamp = df.index[current_index]
        self.active_trade = trade

        return trade

    def manage_trade(self, df: pd.DataFrame, current_index: int,
                    manipulation_leg: Dict) -> Optional[str]:
        """
        Manage active trade (check for exit conditions, move stop to breakeven)

        Args:
            df: DataFrame with price data
            current_index: Current position
            manipulation_leg: Manipulation leg details

        Returns:
            Exit reason if trade was closed, None otherwise
        """
        if self.active_trade is None:
            return None

        current_high = df['high'].iloc[current_index]
        current_low = df['low'].iloc[current_index]
        current_close = df['close'].iloc[current_index]

        trade = self.active_trade

        # Update MFE/MAE
        trade.update_mfe_mae(current_close)

        # 1. Check stop loss
        stop_hit = False
        if trade.direction == 'long':
            if current_low <= trade.stop_loss:
                stop_hit = True
                exit_price = trade.stop_loss
        else:
            if current_high >= trade.stop_loss:
                stop_hit = True
                exit_price = trade.stop_loss

        if stop_hit:
            self._close_trade(current_index, exit_price, 'stop_loss', df)
            return 'stop_loss'

        # 2. Check if internal high/low is broken (move to breakeven)
        if not trade.breakeven_moved:
            internal_broken = False

            if trade.direction == 'long':
                internal_high = manipulation_leg.get('internal_high') or manipulation_leg['high']
                if current_high > internal_high:
                    internal_broken = True
            else:
                internal_low = manipulation_leg.get('internal_low') or manipulation_leg['low']
                if current_low < internal_low:
                    internal_broken = True

            if internal_broken:
                trade.stop_loss = trade.entry_price
                trade.breakeven_moved = True
                trade.internal_broken = True

        # 3. Check targets
        for target in trade.targets:
            target_hit = False

            if trade.direction == 'long':
                if current_high >= target['level']:
                    target_hit = True
                    exit_price = target['level']
            else:
                if current_low <= target['level']:
                    target_hit = True
                    exit_price = target['level']

            if target_hit:
                exit_reason = f"target_{target['type']}"
                self._close_trade(current_index, exit_price, exit_reason, df)
                return exit_reason

        return None

    def _close_trade(self, exit_index: int, exit_price: float,
                    exit_reason: str, df: pd.DataFrame):
        """
        Close the active trade

        Args:
            exit_index: Exit index
            exit_price: Exit price
            exit_reason: Reason for exit
            df: DataFrame with price data
        """
        if self.active_trade is None:
            return

        trade = self.active_trade
        trade.exit_index = exit_index
        trade.exit_price = exit_price
        trade.exit_reason = exit_reason
        trade.exit_timestamp = df.index[exit_index]

        # Calculate P&L
        trade.pnl = trade.calculate_pnl(exit_price)
        trade.pnl_percentage = (trade.pnl / trade.entry_price) * 100

        # Set status
        if exit_reason == 'stop_loss':
            trade.status = 'stopped_out'
        else:
            trade.status = 'closed'

        # Move to closed trades
        self.closed_trades.append(trade)
        self.active_trade = None

    def check_ny_session_time(self, timestamp: pd.Timestamp) -> bool:
        """
        Critical Rule #2: Only trade during NY AM session (9:30 AM - 11:00 AM ET)

        Args:
            timestamp: Current timestamp

        Returns:
            True if within trading hours
        """
        hour = timestamp.hour
        minute = timestamp.minute

        # 9:30 AM - 11:00 AM ET
        if hour == 9 and minute >= 30:
            return True
        elif hour == 10:
            return True
        elif hour == 11 and minute == 0:
            return True

        return False

    def get_trade_statistics(self) -> Dict:
        """
        Calculate trading statistics

        Returns:
            Dictionary with performance metrics
        """
        if not self.closed_trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'max_win': 0.0,
                'max_loss': 0.0
            }

        winning_trades = [t for t in self.closed_trades if t.pnl > 0]
        losing_trades = [t for t in self.closed_trades if t.pnl <= 0]

        total_wins = sum(t.pnl for t in winning_trades)
        total_losses = abs(sum(t.pnl for t in losing_trades))

        return {
            'total_trades': len(self.closed_trades),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': len(winning_trades) / len(self.closed_trades) * 100,
            'total_pnl': sum(t.pnl for t in self.closed_trades),
            'avg_win': total_wins / len(winning_trades) if winning_trades else 0,
            'avg_loss': total_losses / len(losing_trades) if losing_trades else 0,
            'profit_factor': total_wins / total_losses if total_losses > 0 else float('inf'),
            'max_win': max([t.pnl for t in winning_trades]) if winning_trades else 0,
            'max_loss': min([t.pnl for t in losing_trades]) if losing_trades else 0,
            'avg_mfe': np.mean([t.max_favorable_excursion for t in self.closed_trades]),
            'avg_mae': np.mean([t.max_adverse_excursion for t in self.closed_trades]),
            'breakeven_move_rate': len([t for t in self.closed_trades if t.breakeven_moved]) / len(self.closed_trades) * 100
        }

    def get_trades_df(self) -> pd.DataFrame:
        """
        Get all trades as a DataFrame

        Returns:
            DataFrame with trade history
        """
        if not self.closed_trades:
            return pd.DataFrame()

        trades_data = [trade.to_dict() for trade in self.closed_trades]
        return pd.DataFrame(trades_data)
