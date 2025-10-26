"""
Target Identifier - Identifies profit targets (draws on liquidity)
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional


class TargetIdentifier:
    """
    Identifies potential profit targets based on:
    1. Unfilled FVGs (primary target)
    2. Relative equal highs/lows
    3. Low resistance liquidity
    4. Session highs/lows
    """

    def __init__(self):
        """Initialize Target Identifier"""
        pass

    def identify_targets(self, df: pd.DataFrame, current_index: int,
                        entry_price: float, bias: str,
                        min_rr_ratio: float = 1.0) -> List[Dict]:
        """
        Identify all potential profit targets

        Args:
            df: DataFrame with all indicators
            current_index: Current position
            entry_price: Entry price of the trade
            bias: Trade direction ('bullish' or 'bearish')
            min_rr_ratio: Minimum risk/reward ratio

        Returns:
            List of target dictionaries sorted by priority
        """
        targets = []

        # 1. Unfilled FVGs (Primary Target)
        fvg_targets = self._identify_fvg_targets(df, current_index, entry_price, bias)
        targets.extend(fvg_targets)

        # 2. Relative Equal Highs/Lows
        equal_targets = self._identify_equal_hl_targets(df, current_index, entry_price, bias)
        targets.extend(equal_targets)

        # 3. Low Resistance Liquidity
        lr_targets = self._identify_lr_liquidity_targets(df, current_index, entry_price, bias)
        targets.extend(lr_targets)

        # 4. Session Highs/Lows
        session_targets = self._identify_session_targets(df, current_index, entry_price, bias)
        targets.extend(session_targets)

        # 5. PDH/PDL and PWH/PWL
        time_targets = self._identify_time_based_targets(df, current_index, entry_price, bias)
        targets.extend(time_targets)

        # Sort by priority and distance
        targets = self._prioritize_targets(targets, entry_price, bias)

        return targets

    def _identify_fvg_targets(self, df: pd.DataFrame, current_index: int,
                             entry_price: float, bias: str) -> List[Dict]:
        """
        Identify unfilled FVG targets (primary target)

        Args:
            df: DataFrame with FVG data
            current_index: Current position
            entry_price: Entry price
            bias: Trade direction

        Returns:
            List of FVG target dictionaries
        """
        targets = []
        search_ahead = min(100, len(df) - current_index)

        # For bullish trades, look for unfilled bearish FVGs above
        # For bearish trades, look for unfilled bullish FVGs below
        target_fvg_type = 'bearish' if bias == 'bullish' else 'bullish'

        for i in range(current_index, current_index + search_ahead):
            if df['fvg_type'].iloc[i] == target_fvg_type and not df['fvg_filled'].iloc[i]:
                fvg_top = df['fvg_top'].iloc[i]
                fvg_bottom = df['fvg_bottom'].iloc[i]
                fvg_mid = (fvg_top + fvg_bottom) / 2

                # Check if FVG is in the direction of our trade
                if bias == 'bullish' and fvg_bottom > entry_price:
                    targets.append({
                        'type': 'fvg',
                        'subtype': '5m_fvg',
                        'level': fvg_mid,
                        'top': fvg_top,
                        'bottom': fvg_bottom,
                        'index': i,
                        'priority': 'high',
                        'distance': fvg_mid - entry_price
                    })
                elif bias == 'bearish' and fvg_top < entry_price:
                    targets.append({
                        'type': 'fvg',
                        'subtype': '5m_fvg',
                        'level': fvg_mid,
                        'top': fvg_top,
                        'bottom': fvg_bottom,
                        'index': i,
                        'priority': 'high',
                        'distance': entry_price - fvg_mid
                    })

        return targets

    def _identify_equal_hl_targets(self, df: pd.DataFrame, current_index: int,
                                   entry_price: float, bias: str) -> List[Dict]:
        """
        Identify equal highs/lows as targets

        Args:
            df: DataFrame with equal highs/lows data
            current_index: Current position
            entry_price: Entry price
            bias: Trade direction

        Returns:
            List of equal high/low target dictionaries
        """
        targets = []
        search_ahead = min(100, len(df) - current_index)

        for i in range(current_index, current_index + search_ahead):
            # For bullish trades, target equal highs above
            if bias == 'bullish' and df['equal_highs'].iloc[i]:
                level = df['equal_highs_level'].iloc[i]
                if level > entry_price:
                    targets.append({
                        'type': 'equal_highs',
                        'level': level,
                        'index': i,
                        'count': df['equal_highs_count'].iloc[i],
                        'priority': 'medium',
                        'distance': level - entry_price
                    })

            # For bearish trades, target equal lows below
            elif bias == 'bearish' and df['equal_lows'].iloc[i]:
                level = df['equal_lows_level'].iloc[i]
                if level < entry_price:
                    targets.append({
                        'type': 'equal_lows',
                        'level': level,
                        'index': i,
                        'count': df['equal_lows_count'].iloc[i],
                        'priority': 'medium',
                        'distance': entry_price - level
                    })

        return targets

    def _identify_lr_liquidity_targets(self, df: pd.DataFrame, current_index: int,
                                       entry_price: float, bias: str) -> List[Dict]:
        """
        Identify low resistance liquidity targets

        Args:
            df: DataFrame with LR liquidity data
            current_index: Current position
            entry_price: Entry price
            bias: Trade direction

        Returns:
            List of LR liquidity target dictionaries
        """
        targets = []
        search_ahead = min(100, len(df) - current_index)

        for i in range(current_index, current_index + search_ahead):
            # For bullish trades, target LR liquidity highs above
            if bias == 'bullish' and 'lr_liquidity_high' in df.columns:
                if df['lr_liquidity_high'].iloc[i]:
                    # Estimate the level from recent highs
                    window_data = df.iloc[max(0, i - 10):i + 1]
                    level = window_data['high'].mean()

                    if level > entry_price:
                        targets.append({
                            'type': 'lr_liquidity',
                            'direction': 'high',
                            'level': level,
                            'index': i,
                            'priority': 'medium',
                            'distance': level - entry_price
                        })

            # For bearish trades, target LR liquidity lows below
            elif bias == 'bearish' and 'lr_liquidity_low' in df.columns:
                if df['lr_liquidity_low'].iloc[i]:
                    # Estimate the level from recent lows
                    window_data = df.iloc[max(0, i - 10):i + 1]
                    level = window_data['low'].mean()

                    if level < entry_price:
                        targets.append({
                            'type': 'lr_liquidity',
                            'direction': 'low',
                            'level': level,
                            'index': i,
                            'priority': 'medium',
                            'distance': entry_price - level
                        })

        return targets

    def _identify_session_targets(self, df: pd.DataFrame, current_index: int,
                                  entry_price: float, bias: str) -> List[Dict]:
        """
        Identify session highs/lows as targets

        Args:
            df: DataFrame with session data
            current_index: Current position
            entry_price: Entry price
            bias: Trade direction

        Returns:
            List of session target dictionaries
        """
        targets = []

        # London session targets
        if 'london_high' in df.columns and 'london_low' in df.columns:
            london_high = df['london_high'].iloc[current_index]
            london_low = df['london_low'].iloc[current_index]

            if bias == 'bullish' and not pd.isna(london_high) and london_high > entry_price:
                targets.append({
                    'type': 'session_high',
                    'session': 'london',
                    'level': london_high,
                    'index': current_index,
                    'priority': 'low',
                    'distance': london_high - entry_price
                })

            if bias == 'bearish' and not pd.isna(london_low) and london_low < entry_price:
                targets.append({
                    'type': 'session_low',
                    'session': 'london',
                    'level': london_low,
                    'index': current_index,
                    'priority': 'low',
                    'distance': entry_price - london_low
                })

        # Asia session targets
        if 'asia_high' in df.columns and 'asia_low' in df.columns:
            asia_high = df['asia_high'].iloc[current_index]
            asia_low = df['asia_low'].iloc[current_index]

            if bias == 'bullish' and not pd.isna(asia_high) and asia_high > entry_price:
                targets.append({
                    'type': 'session_high',
                    'session': 'asia',
                    'level': asia_high,
                    'index': current_index,
                    'priority': 'low',
                    'distance': asia_high - entry_price
                })

            if bias == 'bearish' and not pd.isna(asia_low) and asia_low < entry_price:
                targets.append({
                    'type': 'session_low',
                    'session': 'asia',
                    'level': asia_low,
                    'index': current_index,
                    'priority': 'low',
                    'distance': entry_price - asia_low
                })

        return targets

    def _identify_time_based_targets(self, df: pd.DataFrame, current_index: int,
                                     entry_price: float, bias: str) -> List[Dict]:
        """
        Identify PDH/PDL and PWH/PWL as targets

        Args:
            df: DataFrame with time-based levels
            current_index: Current position
            entry_price: Entry price
            bias: Trade direction

        Returns:
            List of time-based target dictionaries
        """
        targets = []

        # Previous Day High/Low
        if 'pdh' in df.columns and 'pdl' in df.columns:
            pdh = df['pdh'].iloc[current_index]
            pdl = df['pdl'].iloc[current_index]

            if bias == 'bullish' and not pd.isna(pdh) and pdh > entry_price:
                targets.append({
                    'type': 'pdh',
                    'level': pdh,
                    'index': current_index,
                    'priority': 'medium',
                    'distance': pdh - entry_price
                })

            if bias == 'bearish' and not pd.isna(pdl) and pdl < entry_price:
                targets.append({
                    'type': 'pdl',
                    'level': pdl,
                    'index': current_index,
                    'priority': 'medium',
                    'distance': entry_price - pdl
                })

        # Previous Week High/Low
        if 'pwh' in df.columns and 'pwl' in df.columns:
            pwh = df['pwh'].iloc[current_index]
            pwl = df['pwl'].iloc[current_index]

            if bias == 'bullish' and not pd.isna(pwh) and pwh > entry_price:
                targets.append({
                    'type': 'pwh',
                    'level': pwh,
                    'index': current_index,
                    'priority': 'low',
                    'distance': pwh - entry_price
                })

            if bias == 'bearish' and not pd.isna(pwl) and pwl < entry_price:
                targets.append({
                    'type': 'pwl',
                    'level': pwl,
                    'index': current_index,
                    'priority': 'low',
                    'distance': entry_price - pwl
                })

        return targets

    def _prioritize_targets(self, targets: List[Dict], entry_price: float,
                           bias: str) -> List[Dict]:
        """
        Sort and prioritize targets

        Args:
            targets: List of target dictionaries
            entry_price: Entry price
            bias: Trade direction

        Returns:
            Sorted list of targets
        """
        # Priority mapping
        priority_map = {'high': 3, 'medium': 2, 'low': 1}

        # Sort by priority (high to low) then by distance (nearest first)
        targets.sort(key=lambda x: (
            -priority_map.get(x.get('priority', 'low'), 1),
            x.get('distance', float('inf'))
        ))

        return targets

    def get_primary_target(self, targets: List[Dict]) -> Optional[Dict]:
        """
        Get the primary (best) target from the list

        Args:
            targets: List of target dictionaries

        Returns:
            Primary target dictionary or None
        """
        if not targets:
            return None

        # Prefer FVG targets first
        fvg_targets = [t for t in targets if t['type'] == 'fvg']
        if fvg_targets:
            return fvg_targets[0]

        # Otherwise return the highest priority target
        return targets[0]

    def calculate_risk_reward(self, entry_price: float, stop_loss: float,
                             target_price: float) -> float:
        """
        Calculate risk/reward ratio

        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            target_price: Target price

        Returns:
            Risk/reward ratio
        """
        risk = abs(entry_price - stop_loss)
        reward = abs(target_price - entry_price)

        if risk == 0:
            return 0

        return reward / risk
