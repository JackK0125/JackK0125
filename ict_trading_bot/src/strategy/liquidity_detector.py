"""
Liquidity Detector - Identifies liquidity pools and sweeps
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional


class LiquidityDetector:
    """
    Detects liquidity pools, equal highs/lows, and liquidity sweeps
    """

    def __init__(self, equal_threshold: float = 0.0002):
        """
        Initialize Liquidity Detector

        Args:
            equal_threshold: Percentage threshold for equal highs/lows (default: 0.02%)
        """
        self.equal_threshold = equal_threshold

    def detect_swing_points(self, df: pd.DataFrame, swing_window: int = 5) -> pd.DataFrame:
        """
        Detect swing highs and swing lows

        Args:
            df: DataFrame with OHLCV data
            swing_window: Number of candles on each side to confirm a swing

        Returns:
            DataFrame with swing point markers
        """
        df = df.copy()
        df['swing_high'] = False
        df['swing_low'] = False
        df['swing_high_value'] = np.nan
        df['swing_low_value'] = np.nan

        for i in range(swing_window, len(df) - swing_window):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]

            # Check if current high is higher than surrounding highs
            left_highs = df['high'].iloc[i - swing_window:i]
            right_highs = df['high'].iloc[i + 1:i + swing_window + 1]

            if (current_high > left_highs.max()) and (current_high > right_highs.max()):
                df.iloc[i, df.columns.get_loc('swing_high')] = True
                df.iloc[i, df.columns.get_loc('swing_high_value')] = current_high

            # Check if current low is lower than surrounding lows
            left_lows = df['low'].iloc[i - swing_window:i]
            right_lows = df['low'].iloc[i + 1:i + swing_window + 1]

            if (current_low < left_lows.min()) and (current_low < right_lows.min()):
                df.iloc[i, df.columns.get_loc('swing_low')] = True
                df.iloc[i, df.columns.get_loc('swing_low_value')] = current_low

        return df

    def detect_equal_highs(self, df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
        """
        Detect equal highs (buy-side liquidity)

        Args:
            df: DataFrame with swing points
            lookback: Number of candles to look back for equal highs

        Returns:
            DataFrame with equal highs markers
        """
        df = df.copy()
        df['equal_highs'] = False
        df['equal_highs_count'] = 0
        df['equal_highs_level'] = np.nan

        for i in range(lookback, len(df)):
            if df['swing_high'].iloc[i]:
                current_high = df['swing_high_value'].iloc[i]

                # Look back for equal highs
                equal_count = 0
                for j in range(i - lookback, i):
                    if df['swing_high'].iloc[j]:
                        prev_high = df['swing_high_value'].iloc[j]
                        # Check if highs are approximately equal
                        if abs(current_high - prev_high) / current_high <= self.equal_threshold:
                            equal_count += 1

                if equal_count >= 1:  # At least 2 equal highs (current + 1 previous)
                    df.iloc[i, df.columns.get_loc('equal_highs')] = True
                    df.iloc[i, df.columns.get_loc('equal_highs_count')] = equal_count + 1
                    df.iloc[i, df.columns.get_loc('equal_highs_level')] = current_high

        return df

    def detect_equal_lows(self, df: pd.DataFrame, lookback: int = 20) -> pd.DataFrame:
        """
        Detect equal lows (sell-side liquidity)

        Args:
            df: DataFrame with swing points
            lookback: Number of candles to look back for equal lows

        Returns:
            DataFrame with equal lows markers
        """
        df = df.copy()
        df['equal_lows'] = False
        df['equal_lows_count'] = 0
        df['equal_lows_level'] = np.nan

        for i in range(lookback, len(df)):
            if df['swing_low'].iloc[i]:
                current_low = df['swing_low_value'].iloc[i]

                # Look back for equal lows
                equal_count = 0
                for j in range(i - lookback, i):
                    if df['swing_low'].iloc[j]:
                        prev_low = df['swing_low_value'].iloc[j]
                        # Check if lows are approximately equal
                        if abs(current_low - prev_low) / current_low <= self.equal_threshold:
                            equal_count += 1

                if equal_count >= 1:  # At least 2 equal lows (current + 1 previous)
                    df.iloc[i, df.columns.get_loc('equal_lows')] = True
                    df.iloc[i, df.columns.get_loc('equal_lows_count')] = equal_count + 1
                    df.iloc[i, df.columns.get_loc('equal_lows_level')] = current_low

        return df

    def detect_liquidity_sweep(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect liquidity sweeps (when price takes out highs/lows then reverses)

        Args:
            df: DataFrame with equal highs/lows

        Returns:
            DataFrame with liquidity sweep markers
        """
        df = df.copy()
        df['buy_side_sweep'] = False
        df['sell_side_sweep'] = False
        df['sweep_level'] = np.nan

        for i in range(1, len(df)):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            current_close = df['close'].iloc[i]

            # Check for sell-side liquidity sweep (taking out equal lows)
            for j in range(max(0, i - 50), i):
                if df['equal_lows'].iloc[j]:
                    equal_low_level = df['equal_lows_level'].iloc[j]

                    # Price swept below the equal lows but closed back above
                    if current_low < equal_low_level and current_close > equal_low_level:
                        df.iloc[i, df.columns.get_loc('sell_side_sweep')] = True
                        df.iloc[i, df.columns.get_loc('sweep_level')] = equal_low_level
                        break

            # Check for buy-side liquidity sweep (taking out equal highs)
            for j in range(max(0, i - 50), i):
                if df['equal_highs'].iloc[j]:
                    equal_high_level = df['equal_highs_level'].iloc[j]

                    # Price swept above the equal highs but closed back below
                    if current_high > equal_high_level and current_close < equal_high_level:
                        df.iloc[i, df.columns.get_loc('buy_side_sweep')] = True
                        df.iloc[i, df.columns.get_loc('sweep_level')] = equal_high_level
                        break

        return df

    def get_session_highs_lows(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate session highs and lows for London and Asia sessions

        Args:
            df: DataFrame with datetime index

        Returns:
            DataFrame with session high/low markers
        """
        df = df.copy()

        # London session: 3:00 AM - 12:00 PM ET
        df['london_high'] = np.nan
        df['london_low'] = np.nan

        # Asia session: 7:00 PM - 2:00 AM ET
        df['asia_high'] = np.nan
        df['asia_low'] = np.nan

        # Group by date and calculate session highs/lows
        for date in df.index.date:
            date_mask = df.index.date == date

            # London session
            london_mask = date_mask & (
                ((df.index.hour >= 3) & (df.index.hour < 12))
            )
            if london_mask.any():
                london_high = df.loc[london_mask, 'high'].max()
                london_low = df.loc[london_mask, 'low'].min()
                df.loc[date_mask, 'london_high'] = london_high
                df.loc[date_mask, 'london_low'] = london_low

            # Asia session
            asia_mask = date_mask & (
                (df.index.hour >= 19) | (df.index.hour < 2)
            )
            if asia_mask.any():
                asia_high = df.loc[asia_mask, 'high'].max()
                asia_low = df.loc[asia_mask, 'low'].min()
                df.loc[date_mask, 'asia_high'] = asia_high
                df.loc[date_mask, 'asia_low'] = asia_low

        return df

    def detect_low_resistance_liquidity(self, df: pd.DataFrame,
                                       window: int = 10,
                                       min_points: int = 3) -> pd.DataFrame:
        """
        Detect low resistance liquidity runs (series of small highs or lows)

        Args:
            df: DataFrame with price data
            window: Lookback window for detection
            min_points: Minimum number of similar highs/lows to qualify

        Returns:
            DataFrame with low resistance liquidity markers
        """
        df = df.copy()
        df['lr_liquidity_high'] = False
        df['lr_liquidity_low'] = False

        for i in range(window, len(df)):
            window_data = df.iloc[i - window:i]

            # Check for low resistance highs
            high_range = window_data['high'].max() - window_data['high'].min()
            avg_high = window_data['high'].mean()

            similar_highs = 0
            for high in window_data['high']:
                if abs(high - avg_high) / avg_high <= self.equal_threshold * 2:
                    similar_highs += 1

            if similar_highs >= min_points:
                df.iloc[i, df.columns.get_loc('lr_liquidity_high')] = True

            # Check for low resistance lows
            low_range = window_data['low'].max() - window_data['low'].min()
            avg_low = window_data['low'].mean()

            similar_lows = 0
            for low in window_data['low']:
                if abs(low - avg_low) / avg_low <= self.equal_threshold * 2:
                    similar_lows += 1

            if similar_lows >= min_points:
                df.iloc[i, df.columns.get_loc('lr_liquidity_low')] = True

        return df

    def get_nearest_liquidity(self, df: pd.DataFrame, current_index: int,
                             direction: str, max_distance: int = 100) -> Optional[Dict]:
        """
        Get the nearest liquidity pool in the specified direction

        Args:
            df: DataFrame with liquidity data
            current_index: Current position
            direction: 'above' or 'below'
            max_distance: Maximum candles to look ahead

        Returns:
            Dictionary with liquidity information or None
        """
        current_price = df['close'].iloc[current_index]
        nearest_liquidity = None
        min_distance = float('inf')

        search_end = min(current_index + max_distance, len(df))

        for i in range(current_index + 1, search_end):
            if direction == 'above':
                # Look for buy-side liquidity above current price
                if df['equal_highs'].iloc[i]:
                    level = df['equal_highs_level'].iloc[i]
                    if level > current_price:
                        distance = level - current_price
                        if distance < min_distance:
                            min_distance = distance
                            nearest_liquidity = {
                                'type': 'equal_highs',
                                'level': level,
                                'index': i,
                                'distance': distance
                            }

            elif direction == 'below':
                # Look for sell-side liquidity below current price
                if df['equal_lows'].iloc[i]:
                    level = df['equal_lows_level'].iloc[i]
                    if level < current_price:
                        distance = current_price - level
                        if distance < min_distance:
                            min_distance = distance
                            nearest_liquidity = {
                                'type': 'equal_lows',
                                'level': level,
                                'index': i,
                                'distance': distance
                            }

        return nearest_liquidity
