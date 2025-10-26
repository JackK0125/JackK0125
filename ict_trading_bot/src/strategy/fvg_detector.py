"""
Fair Value Gap (FVG) Detector
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional


class FVGDetector:
    """
    Detects Fair Value Gaps (FVGs) in price action

    A Fair Value Gap is formed when:
    - Bullish FVG: The low of candle 3 > the high of candle 1
    - Bearish FVG: The high of candle 3 < the low of candle 1
    """

    def __init__(self, min_gap_size: float = 0.0):
        """
        Initialize FVG Detector

        Args:
            min_gap_size: Minimum gap size in points to be considered valid
        """
        self.min_gap_size = min_gap_size

    def detect_fvgs(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect all FVGs in the dataframe

        Args:
            df: DataFrame with OHLCV data

        Returns:
            DataFrame with FVG columns added
        """
        df = df.copy()

        # Initialize FVG columns
        df['bullish_fvg'] = False
        df['bearish_fvg'] = False
        df['fvg_top'] = np.nan
        df['fvg_bottom'] = np.nan
        df['fvg_filled'] = False
        df['fvg_type'] = None

        for i in range(2, len(df)):
            # Get three consecutive candles
            candle_1_high = df['high'].iloc[i - 2]
            candle_1_low = df['low'].iloc[i - 2]
            candle_2_high = df['high'].iloc[i - 1]
            candle_2_low = df['low'].iloc[i - 1]
            candle_3_high = df['high'].iloc[i]
            candle_3_low = df['low'].iloc[i]

            # Check for Bullish FVG (gap up)
            if candle_3_low > candle_1_high:
                gap_size = candle_3_low - candle_1_high
                if gap_size >= self.min_gap_size:
                    df.iloc[i, df.columns.get_loc('bullish_fvg')] = True
                    df.iloc[i, df.columns.get_loc('fvg_bottom')] = candle_1_high
                    df.iloc[i, df.columns.get_loc('fvg_top')] = candle_3_low
                    df.iloc[i, df.columns.get_loc('fvg_type')] = 'bullish'

            # Check for Bearish FVG (gap down)
            elif candle_3_high < candle_1_low:
                gap_size = candle_1_low - candle_3_high
                if gap_size >= self.min_gap_size:
                    df.iloc[i, df.columns.get_loc('bearish_fvg')] = True
                    df.iloc[i, df.columns.get_loc('fvg_bottom')] = candle_3_high
                    df.iloc[i, df.columns.get_loc('fvg_top')] = candle_1_low
                    df.iloc[i, df.columns.get_loc('fvg_type')] = 'bearish'

        return df

    def check_fvg_filled(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Mark FVGs that have been filled by subsequent price action

        Args:
            df: DataFrame with FVG data

        Returns:
            DataFrame with fvg_filled column updated
        """
        df = df.copy()

        # Track active FVGs
        active_fvgs = []

        for i in range(len(df)):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]

            # Add new FVG if detected
            if df['bullish_fvg'].iloc[i] or df['bearish_fvg'].iloc[i]:
                active_fvgs.append({
                    'index': i,
                    'type': df['fvg_type'].iloc[i],
                    'top': df['fvg_top'].iloc[i],
                    'bottom': df['fvg_bottom'].iloc[i],
                    'filled': False
                })

            # Check if any active FVGs are filled
            for fvg in active_fvgs:
                if fvg['filled']:
                    continue

                if fvg['type'] == 'bullish':
                    # Bullish FVG is filled when price closes through it downward
                    if current_low <= fvg['bottom']:
                        fvg['filled'] = True
                        df.iloc[fvg['index'], df.columns.get_loc('fvg_filled')] = True

                elif fvg['type'] == 'bearish':
                    # Bearish FVG is filled when price closes through it upward
                    if current_high >= fvg['top']:
                        fvg['filled'] = True
                        df.iloc[fvg['index'], df.columns.get_loc('fvg_filled')] = True

        return df

    def check_fvg_respect(self, df: pd.DataFrame, lookback: int = 10) -> pd.DataFrame:
        """
        Check if price respects or disrespects FVGs

        Args:
            df: DataFrame with FVG data
            lookback: Number of candles to look back for respect/disrespect

        Returns:
            DataFrame with respect/disrespect markers
        """
        df = df.copy()
        df['fvg_respected'] = False
        df['fvg_disrespected'] = False

        for i in range(lookback, len(df)):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            current_close = df['close'].iloc[i]

            # Look back for recent FVGs
            for j in range(i - lookback, i):
                if df['bullish_fvg'].iloc[j] and not df['fvg_filled'].iloc[j]:
                    fvg_top = df['fvg_top'].iloc[j]
                    fvg_bottom = df['fvg_bottom'].iloc[j]

                    # Respect: Price wicks into the FVG but doesn't close through it
                    if current_low <= fvg_top and current_close >= fvg_bottom:
                        df.iloc[i, df.columns.get_loc('fvg_respected')] = True

                    # Disrespect: Price closes through the FVG
                    elif current_close < fvg_bottom:
                        df.iloc[i, df.columns.get_loc('fvg_disrespected')] = True

                elif df['bearish_fvg'].iloc[j] and not df['fvg_filled'].iloc[j]:
                    fvg_top = df['fvg_top'].iloc[j]
                    fvg_bottom = df['fvg_bottom'].iloc[j]

                    # Respect: Price wicks into the FVG but doesn't close through it
                    if current_high >= fvg_bottom and current_close <= fvg_top:
                        df.iloc[i, df.columns.get_loc('fvg_respected')] = True

                    # Disrespect: Price closes through the FVG
                    elif current_close > fvg_top:
                        df.iloc[i, df.columns.get_loc('fvg_disrespected')] = True

        return df

    def get_unfilled_fvgs(self, df: pd.DataFrame, current_index: int,
                          fvg_type: Optional[str] = None) -> List[Dict]:
        """
        Get all unfilled FVGs up to a specific index

        Args:
            df: DataFrame with FVG data
            current_index: Current position in the dataframe
            fvg_type: Filter by FVG type ('bullish', 'bearish', or None for all)

        Returns:
            List of unfilled FVG dictionaries
        """
        unfilled_fvgs = []

        for i in range(current_index):
            if not df['fvg_filled'].iloc[i]:
                if fvg_type is None or df['fvg_type'].iloc[i] == fvg_type:
                    if df['bullish_fvg'].iloc[i] or df['bearish_fvg'].iloc[i]:
                        unfilled_fvgs.append({
                            'index': i,
                            'timestamp': df.index[i],
                            'type': df['fvg_type'].iloc[i],
                            'top': df['fvg_top'].iloc[i],
                            'bottom': df['fvg_bottom'].iloc[i],
                            'size': df['fvg_top'].iloc[i] - df['fvg_bottom'].iloc[i]
                        })

        return unfilled_fvgs

    def find_inversion_fvg(self, df: pd.DataFrame, manipulation_start: int,
                          manipulation_end: int, direction: str) -> Optional[Dict]:
        """
        Find the highest timeframe Inversion FVG within a manipulation leg

        Args:
            df: DataFrame with FVG data
            manipulation_start: Start index of manipulation leg
            manipulation_end: End index of manipulation leg
            direction: Trade direction ('long' or 'short')

        Returns:
            Dictionary with IFVG details or None
        """
        # For a long setup, look for bearish FVG within the manipulation leg
        # For a short setup, look for bullish FVG within the manipulation leg
        target_fvg_type = 'bearish' if direction == 'long' else 'bullish'

        ifvgs = []

        for i in range(manipulation_start, manipulation_end + 1):
            if df['fvg_type'].iloc[i] == target_fvg_type:
                ifvgs.append({
                    'index': i,
                    'timestamp': df.index[i],
                    'type': df['fvg_type'].iloc[i],
                    'top': df['fvg_top'].iloc[i],
                    'bottom': df['fvg_bottom'].iloc[i],
                    'size': df['fvg_top'].iloc[i] - df['fvg_bottom'].iloc[i]
                })

        # Return the largest/most significant IFVG
        if ifvgs:
            return max(ifvgs, key=lambda x: x['size'])

        return None

    def check_fvg_inversion(self, df: pd.DataFrame, ifvg: Dict,
                           current_index: int, direction: str) -> bool:
        """
        Check if price has inverted through an IFVG (entry signal)

        Args:
            df: DataFrame with price data
            ifvg: Inversion FVG dictionary
            current_index: Current candle index
            direction: Trade direction ('long' or 'short')

        Returns:
            True if IFVG has been inverted (entry signal triggered)
        """
        current_close = df['close'].iloc[current_index]

        if direction == 'long':
            # For long, we need bearish IFVG to be broken upward
            return current_close > ifvg['top']
        else:
            # For short, we need bullish IFVG to be broken downward
            return current_close < ifvg['bottom']
