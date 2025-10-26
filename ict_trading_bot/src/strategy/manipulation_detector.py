"""
Manipulation Leg and Inversion FVG Detector
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from .fvg_detector import FVGDetector


class ManipulationDetector:
    """
    Detects manipulation legs and Inversion FVGs (IFVGs)

    A manipulation leg is the specific swing that:
    - Hits a key rejection level (FVG, liquidity, PDH/PDL, etc.)
    - Creates the final move before reversal
    """

    def __init__(self):
        """Initialize Manipulation Detector"""
        self.fvg_detector = FVGDetector()

    def identify_manipulation_leg(self, df: pd.DataFrame, rejection_level: Dict,
                                  current_index: int, bias: str) -> Optional[Dict]:
        """
        Identify the manipulation leg after hitting a rejection level

        Args:
            df: DataFrame with price data
            rejection_level: Dictionary with rejection level details
            current_index: Current position
            bias: Market bias ('bullish' or 'bearish')

        Returns:
            Dictionary with manipulation leg details or None
        """
        manipulation = {
            'start_index': None,
            'end_index': None,
            'start_price': None,
            'end_price': None,
            'high': None,
            'low': None,
            'swing_high': None,
            'swing_low': None,
            'rejection_level_hit': False,
            'type': bias  # 'bullish' or 'bearish'
        }

        lookback = 50
        start_search = max(0, current_index - lookback)

        if bias == 'bullish':
            # For bullish setup, look for swing low that hits rejection level
            manipulation_leg = self._find_bullish_manipulation_leg(
                df, rejection_level, start_search, current_index
            )
        else:
            # For bearish setup, look for swing high that hits rejection level
            manipulation_leg = self._find_bearish_manipulation_leg(
                df, rejection_level, start_search, current_index
            )

        return manipulation_leg

    def _find_bullish_manipulation_leg(self, df: pd.DataFrame,
                                       rejection_level: Dict,
                                       start_index: int,
                                       end_index: int) -> Optional[Dict]:
        """
        Find bullish manipulation leg (swing high to low that hits support)

        Args:
            df: DataFrame with price data
            rejection_level: Rejection level details
            start_index: Start of search range
            end_index: End of search range

        Returns:
            Manipulation leg details or None
        """
        level = rejection_level.get('level')
        level_type = rejection_level.get('type')

        # Find the most recent swing that touched or swept the rejection level
        for i in range(end_index, start_index, -1):
            current_low = df['low'].iloc[i]

            # Check if this candle hit the rejection level
            level_hit = False

            if level_type == 'fvg':
                # Check if price entered the FVG zone
                if current_low <= rejection_level.get('top', 0):
                    level_hit = True
            elif level_type in ['pdl', 'pwl', 'equal_lows', 'session_low']:
                # Check if price swept the level
                if current_low <= level:
                    level_hit = True

            if level_hit:
                # Find the swing high before this low
                swing_high_idx = None
                swing_high_price = 0

                for j in range(i, max(0, i - 20), -1):
                    if df['high'].iloc[j] > swing_high_price:
                        swing_high_price = df['high'].iloc[j]
                        swing_high_idx = j

                if swing_high_idx is not None:
                    # Calculate manipulation leg details
                    leg_data = df.iloc[swing_high_idx:i + 1]

                    return {
                        'start_index': swing_high_idx,
                        'end_index': i,
                        'start_price': swing_high_price,
                        'end_price': current_low,
                        'high': leg_data['high'].max(),
                        'low': leg_data['low'].min(),
                        'swing_high': swing_high_price,
                        'swing_low': current_low,
                        'rejection_level_hit': True,
                        'type': 'bullish',
                        'internal_high': None,  # Will be updated during trade
                        'internal_low': current_low
                    }

        return None

    def _find_bearish_manipulation_leg(self, df: pd.DataFrame,
                                       rejection_level: Dict,
                                       start_index: int,
                                       end_index: int) -> Optional[Dict]:
        """
        Find bearish manipulation leg (swing low to high that hits resistance)

        Args:
            df: DataFrame with price data
            rejection_level: Rejection level details
            start_index: Start of search range
            end_index: End of search range

        Returns:
            Manipulation leg details or None
        """
        level = rejection_level.get('level')
        level_type = rejection_level.get('type')

        # Find the most recent swing that touched or swept the rejection level
        for i in range(end_index, start_index, -1):
            current_high = df['high'].iloc[i]

            # Check if this candle hit the rejection level
            level_hit = False

            if level_type == 'fvg':
                # Check if price entered the FVG zone
                if current_high >= rejection_level.get('bottom', float('inf')):
                    level_hit = True
            elif level_type in ['pdh', 'pwh', 'equal_highs', 'session_high']:
                # Check if price swept the level
                if current_high >= level:
                    level_hit = True

            if level_hit:
                # Find the swing low before this high
                swing_low_idx = None
                swing_low_price = float('inf')

                for j in range(i, max(0, i - 20), -1):
                    if df['low'].iloc[j] < swing_low_price:
                        swing_low_price = df['low'].iloc[j]
                        swing_low_idx = j

                if swing_low_idx is not None:
                    # Calculate manipulation leg details
                    leg_data = df.iloc[swing_low_idx:i + 1]

                    return {
                        'start_index': swing_low_idx,
                        'end_index': i,
                        'start_price': swing_low_price,
                        'end_price': current_high,
                        'high': leg_data['high'].max(),
                        'low': leg_data['low'].min(),
                        'swing_high': current_high,
                        'swing_low': swing_low_price,
                        'rejection_level_hit': True,
                        'type': 'bearish',
                        'internal_high': current_high,
                        'internal_low': None  # Will be updated during trade
                    }

        return None

    def find_inversion_fvg(self, df: pd.DataFrame, manipulation_leg: Dict,
                          timeframes: List[str] = ['30s', '1m', '5m']) -> Optional[Dict]:
        """
        Find the highest timeframe Inversion FVG within the manipulation leg

        Args:
            df: DataFrame with FVG data (should have FVGs detected)
            manipulation_leg: Manipulation leg details
            timeframes: List of timeframes to check (in order of preference)

        Returns:
            Inversion FVG details or None
        """
        if manipulation_leg is None:
            return None

        start_idx = manipulation_leg['start_index']
        end_idx = manipulation_leg['end_index']
        direction = 'long' if manipulation_leg['type'] == 'bullish' else 'short'

        # For long setup, look for bearish FVG within manipulation
        # For short setup, look for bullish FVG within manipulation
        target_fvg_type = 'bearish' if direction == 'long' else 'bullish'

        # Find all FVGs within the manipulation leg
        ifvgs = []

        for i in range(start_idx, end_idx + 1):
            if df['fvg_type'].iloc[i] == target_fvg_type:
                ifvgs.append({
                    'index': i,
                    'timestamp': df.index[i],
                    'type': df['fvg_type'].iloc[i],
                    'top': df['fvg_top'].iloc[i],
                    'bottom': df['fvg_bottom'].iloc[i],
                    'size': df['fvg_top'].iloc[i] - df['fvg_bottom'].iloc[i],
                    'midpoint': (df['fvg_top'].iloc[i] + df['fvg_bottom'].iloc[i]) / 2
                })

        # Return the largest IFVG (highest timeframe proxy)
        if ifvgs:
            largest_ifvg = max(ifvgs, key=lambda x: x['size'])
            largest_ifvg['inverted'] = False  # Will be set to True when price breaks through
            return largest_ifvg

        return None

    def check_ifvg_inversion(self, df: pd.DataFrame, ifvg: Dict,
                            current_index: int) -> bool:
        """
        Check if the Inversion FVG has been inverted (entry signal)

        Args:
            df: DataFrame with price data
            ifvg: Inversion FVG details
            current_index: Current candle index

        Returns:
            True if IFVG has been inverted
        """
        if ifvg is None:
            return False

        current_close = df['close'].iloc[current_index]
        current_open = df['open'].iloc[current_index]

        # For bearish IFVG (long setup), inversion occurs when price closes above the top
        if ifvg['type'] == 'bearish':
            # Body closure above the FVG top
            return current_close > ifvg['top']

        # For bullish IFVG (short setup), inversion occurs when price closes below the bottom
        elif ifvg['type'] == 'bullish':
            # Body closure below the FVG bottom
            return current_close < ifvg['bottom']

        return False

    def identify_rejection_levels(self, df: pd.DataFrame,
                                  current_index: int,
                                  bias: str) -> List[Dict]:
        """
        Identify all potential rejection levels for the current bias

        Args:
            df: DataFrame with all indicators
            current_index: Current position
            bias: Market bias ('bullish' or 'bearish')

        Returns:
            List of rejection level dictionaries
        """
        rejection_levels = []
        current_price = df['close'].iloc[current_index]

        # 1. Fair Value Gaps (at least 5-minute)
        unfilled_fvgs = self.fvg_detector.get_unfilled_fvgs(
            df, current_index,
            fvg_type='bullish' if bias == 'bullish' else 'bearish'
        )

        for fvg in unfilled_fvgs:
            # Only consider FVGs in the direction of our bias
            if bias == 'bullish' and fvg['bottom'] < current_price:
                rejection_levels.append({
                    'type': 'fvg',
                    'level': fvg['midpoint'],
                    'top': fvg['top'],
                    'bottom': fvg['bottom'],
                    'index': fvg['index'],
                    'quality': 'high'  # 5-min+ FVGs are high quality
                })
            elif bias == 'bearish' and fvg['top'] > current_price:
                rejection_levels.append({
                    'type': 'fvg',
                    'level': fvg['midpoint'],
                    'top': fvg['top'],
                    'bottom': fvg['bottom'],
                    'index': fvg['index'],
                    'quality': 'high'
                })

        # 2. Previous Day High/Low (PDH/PDL)
        if 'pdh' in df.columns and 'pdl' in df.columns:
            pdh = df['pdh'].iloc[current_index]
            pdl = df['pdl'].iloc[current_index]

            if bias == 'bullish' and not pd.isna(pdl) and pdl < current_price:
                rejection_levels.append({
                    'type': 'pdl',
                    'level': pdl,
                    'index': current_index,
                    'quality': 'high'
                })
            elif bias == 'bearish' and not pd.isna(pdh) and pdh > current_price:
                rejection_levels.append({
                    'type': 'pdh',
                    'level': pdh,
                    'index': current_index,
                    'quality': 'high'
                })

        # 3. Previous Week High/Low (PWH/PWL)
        if 'pwh' in df.columns and 'pwl' in df.columns:
            pwh = df['pwh'].iloc[current_index]
            pwl = df['pwl'].iloc[current_index]

            if bias == 'bullish' and not pd.isna(pwl) and pwl < current_price:
                rejection_levels.append({
                    'type': 'pwl',
                    'level': pwl,
                    'index': current_index,
                    'quality': 'medium'
                })
            elif bias == 'bearish' and not pd.isna(pwh) and pwh > current_price:
                rejection_levels.append({
                    'type': 'pwh',
                    'level': pwh,
                    'index': current_index,
                    'quality': 'medium'
                })

        # 4. Session Liquidity (London/Asia highs and lows)
        if 'london_high' in df.columns and 'london_low' in df.columns:
            london_high = df['london_high'].iloc[current_index]
            london_low = df['london_low'].iloc[current_index]

            if bias == 'bullish' and not pd.isna(london_low) and london_low < current_price:
                rejection_levels.append({
                    'type': 'session_low',
                    'session': 'london',
                    'level': london_low,
                    'index': current_index,
                    'quality': 'medium'
                })
            elif bias == 'bearish' and not pd.isna(london_high) and london_high > current_price:
                rejection_levels.append({
                    'type': 'session_high',
                    'session': 'london',
                    'level': london_high,
                    'index': current_index,
                    'quality': 'medium'
                })

        if 'asia_high' in df.columns and 'asia_low' in df.columns:
            asia_high = df['asia_high'].iloc[current_index]
            asia_low = df['asia_low'].iloc[current_index]

            if bias == 'bullish' and not pd.isna(asia_low) and asia_low < current_price:
                rejection_levels.append({
                    'type': 'session_low',
                    'session': 'asia',
                    'level': asia_low,
                    'index': current_index,
                    'quality': 'medium'
                })
            elif bias == 'bearish' and not pd.isna(asia_high) and asia_high > current_price:
                rejection_levels.append({
                    'type': 'session_high',
                    'session': 'asia',
                    'level': asia_high,
                    'index': current_index,
                    'quality': 'medium'
                })

        # 5. Equal Highs/Lows
        lookback = 50
        for i in range(max(0, current_index - lookback), current_index):
            if bias == 'bullish' and df['equal_lows'].iloc[i]:
                level = df['equal_lows_level'].iloc[i]
                if level < current_price:
                    rejection_levels.append({
                        'type': 'equal_lows',
                        'level': level,
                        'index': i,
                        'quality': 'high'
                    })

            elif bias == 'bearish' and df['equal_highs'].iloc[i]:
                level = df['equal_highs_level'].iloc[i]
                if level > current_price:
                    rejection_levels.append({
                        'type': 'equal_highs',
                        'level': level,
                        'index': i,
                        'quality': 'high'
                    })

        return rejection_levels
