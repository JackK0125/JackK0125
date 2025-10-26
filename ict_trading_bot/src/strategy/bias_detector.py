"""
Higher Time Frame (HTF) Bias Detector
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple
from .fvg_detector import FVGDetector
from .liquidity_detector import LiquidityDetector


class BiasDetector:
    """
    Determines market bias based on:
    1. Liquidity delivery (buy-side vs sell-side)
    2. FVG respect/disrespect patterns
    3. 4-hour candle direction
    """

    def __init__(self):
        """Initialize Bias Detector"""
        self.fvg_detector = FVGDetector()
        self.liquidity_detector = LiquidityDetector()

    def determine_bias(self, df: pd.DataFrame, current_index: int,
                      df_4h: Optional[pd.DataFrame] = None) -> Dict:
        """
        Determine the current market bias

        Args:
            df: DataFrame with price and indicator data
            current_index: Current position in the dataframe
            df_4h: 4-hour timeframe dataframe (optional but recommended)

        Returns:
            Dictionary with bias information
        """
        bias_signals = {
            'liquidity_bias': None,
            'fvg_bias': None,
            'four_hour_bias': None,
            'overall_bias': None,
            'bias_strength': 0,  # 0-3 (number of confirming signals)
            'details': {}
        }

        # 1. Analyze liquidity delivery
        liquidity_bias = self._analyze_liquidity_delivery(df, current_index)
        bias_signals['liquidity_bias'] = liquidity_bias['bias']
        bias_signals['details']['liquidity'] = liquidity_bias

        # 2. Analyze FVG respect/disrespect
        fvg_bias = self._analyze_fvg_patterns(df, current_index)
        bias_signals['fvg_bias'] = fvg_bias['bias']
        bias_signals['details']['fvg'] = fvg_bias

        # 3. Check 4-hour candle direction
        if df_4h is not None:
            four_hour_bias = self._check_4h_candle(df, df_4h, current_index)
            bias_signals['four_hour_bias'] = four_hour_bias['bias']
            bias_signals['details']['four_hour'] = four_hour_bias

        # Determine overall bias
        bias_signals['overall_bias'] = self._calculate_overall_bias(bias_signals)

        return bias_signals

    def _analyze_liquidity_delivery(self, df: pd.DataFrame,
                                   current_index: int,
                                   lookback: int = 20) -> Dict:
        """
        Analyze whether price is delivering from buy-side or sell-side liquidity

        Args:
            df: DataFrame with liquidity data
            current_index: Current position
            lookback: Candles to look back

        Returns:
            Dictionary with liquidity analysis
        """
        result = {
            'bias': None,
            'last_sweep': None,
            'sweep_type': None,
            'pdh_pdl_relation': None
        }

        start_index = max(0, current_index - lookback)

        # Check for recent liquidity sweeps
        for i in range(current_index, start_index, -1):
            # Sell-side sweep = bullish bias
            if df['sell_side_sweep'].iloc[i]:
                result['bias'] = 'bullish'
                result['last_sweep'] = i
                result['sweep_type'] = 'sell_side'
                break

            # Buy-side sweep = bearish bias
            elif df['buy_side_sweep'].iloc[i]:
                result['bias'] = 'bearish'
                result['last_sweep'] = i
                result['sweep_type'] = 'buy_side'
                break

        # Check PDH/PDL relationship
        if 'pdh' in df.columns and 'pdl' in df.columns:
            current_price = df['close'].iloc[current_index]
            pdh = df['pdh'].iloc[current_index]
            pdl = df['pdl'].iloc[current_index]

            # Check if we've taken out PDL (bullish) or PDH (bearish)
            for i in range(current_index, start_index, -1):
                if df['low'].iloc[i] < pdl:
                    result['pdh_pdl_relation'] = 'below_pdl_bullish'
                    if result['bias'] is None:
                        result['bias'] = 'bullish'
                    break
                elif df['high'].iloc[i] > pdh:
                    result['pdh_pdl_relation'] = 'above_pdh_bearish'
                    if result['bias'] is None:
                        result['bias'] = 'bearish'
                    break

        return result

    def _analyze_fvg_patterns(self, df: pd.DataFrame,
                             current_index: int,
                             lookback: int = 20) -> Dict:
        """
        Analyze FVG respect/disrespect patterns to determine bias

        Bullish bias: Respects bullish FVGs, disrespects bearish FVGs
        Bearish bias: Respects bearish FVGs, disrespects bullish FVGs

        Args:
            df: DataFrame with FVG data
            current_index: Current position
            lookback: Candles to look back

        Returns:
            Dictionary with FVG analysis
        """
        result = {
            'bias': None,
            'bullish_fvg_respected': 0,
            'bullish_fvg_disrespected': 0,
            'bearish_fvg_respected': 0,
            'bearish_fvg_disrespected': 0
        }

        start_index = max(0, current_index - lookback)

        # Count respect/disrespect patterns
        for i in range(start_index, current_index):
            current_close = df['close'].iloc[i]
            current_low = df['low'].iloc[i]
            current_high = df['high'].iloc[i]

            # Check for bullish FVG interactions
            for j in range(max(0, i - 10), i):
                if df['bullish_fvg'].iloc[j] and not df['fvg_filled'].iloc[j]:
                    fvg_top = df['fvg_top'].iloc[j]
                    fvg_bottom = df['fvg_bottom'].iloc[j]

                    # Respect: wick into FVG, close above it
                    if current_low <= fvg_top and current_close >= fvg_bottom:
                        result['bullish_fvg_respected'] += 1

                    # Disrespect: close through FVG
                    elif current_close < fvg_bottom:
                        result['bullish_fvg_disrespected'] += 1

            # Check for bearish FVG interactions
            for j in range(max(0, i - 10), i):
                if df['bearish_fvg'].iloc[j] and not df['fvg_filled'].iloc[j]:
                    fvg_top = df['fvg_top'].iloc[j]
                    fvg_bottom = df['fvg_bottom'].iloc[j]

                    # Respect: wick into FVG, close below it
                    if current_high >= fvg_bottom and current_close <= fvg_top:
                        result['bearish_fvg_respected'] += 1

                    # Disrespect: close through FVG
                    elif current_close > fvg_top:
                        result['bearish_fvg_disrespected'] += 1

        # Determine bias from FVG patterns
        bullish_score = result['bullish_fvg_respected'] + result['bearish_fvg_disrespected']
        bearish_score = result['bearish_fvg_respected'] + result['bullish_fvg_disrespected']

        if bullish_score > bearish_score:
            result['bias'] = 'bullish'
        elif bearish_score > bullish_score:
            result['bias'] = 'bearish'
        else:
            result['bias'] = 'neutral'

        return result

    def _check_4h_candle(self, df: pd.DataFrame, df_4h: pd.DataFrame,
                        current_index: int) -> Dict:
        """
        Check the 4-hour candle direction (10:00 AM ET candle)

        Args:
            df: Main timeframe dataframe
            df_4h: 4-hour timeframe dataframe
            current_index: Current position in main df

        Returns:
            Dictionary with 4-hour bias
        """
        result = {
            'bias': None,
            'candle_time': None,
            'open': None,
            'close': None,
            'direction': None
        }

        try:
            # Get current timestamp from main df
            current_time = df.index[current_index]

            # Find the most recent 4-hour candle at or before current time
            # Specifically looking for the 10:00 AM candle
            four_hour_candles = df_4h[df_4h.index <= current_time]

            if len(four_hour_candles) > 0:
                # Get the most recent 4-hour candle
                latest_4h = four_hour_candles.iloc[-1]

                result['candle_time'] = latest_4h.name
                result['open'] = latest_4h['open']
                result['close'] = latest_4h['close']

                # Determine direction
                if latest_4h['close'] > latest_4h['open']:
                    result['direction'] = 'bullish'
                    result['bias'] = 'bullish'
                elif latest_4h['close'] < latest_4h['open']:
                    result['direction'] = 'bearish'
                    result['bias'] = 'bearish'
                else:
                    result['direction'] = 'neutral'
                    result['bias'] = 'neutral'

        except Exception as e:
            print(f"Error checking 4-hour candle: {str(e)}")

        return result

    def _calculate_overall_bias(self, bias_signals: Dict) -> str:
        """
        Calculate overall bias from individual signals

        Args:
            bias_signals: Dictionary with individual bias signals

        Returns:
            Overall bias ('bullish', 'bearish', or 'neutral')
        """
        bullish_count = 0
        bearish_count = 0

        # Count bullish signals
        if bias_signals['liquidity_bias'] == 'bullish':
            bullish_count += 1
        if bias_signals['fvg_bias'] == 'bullish':
            bullish_count += 1
        if bias_signals['four_hour_bias'] == 'bullish':
            bullish_count += 1

        # Count bearish signals
        if bias_signals['liquidity_bias'] == 'bearish':
            bearish_count += 1
        if bias_signals['fvg_bias'] == 'bearish':
            bearish_count += 1
        if bias_signals['four_hour_bias'] == 'bearish':
            bearish_count += 1

        # Update bias strength
        bias_signals['bias_strength'] = max(bullish_count, bearish_count)

        # Determine overall bias
        if bullish_count > bearish_count:
            return 'bullish'
        elif bearish_count > bullish_count:
            return 'bearish'
        else:
            return 'neutral'

    def check_bias_against_equal_highs_lows(self, df: pd.DataFrame,
                                           current_index: int,
                                           bias: str) -> bool:
        """
        Critical Rule #1: Don't trade against equal highs/lows

        Args:
            df: DataFrame with equal highs/lows data
            current_index: Current position
            bias: Current bias ('bullish' or 'bearish')

        Returns:
            True if bias is safe (no conflicting equal highs/lows), False otherwise
        """
        current_price = df['close'].iloc[current_index]
        lookback = 50

        # For bullish bias, check for equal lows below current price
        if bias == 'bullish':
            for i in range(max(0, current_index - lookback), current_index):
                if df['equal_lows'].iloc[i]:
                    equal_low_level = df['equal_lows_level'].iloc[i]
                    # If equal lows are just below, don't go long
                    if equal_low_level < current_price and (current_price - equal_low_level) / current_price < 0.01:
                        return False

        # For bearish bias, check for equal highs above current price
        elif bias == 'bearish':
            for i in range(max(0, current_index - lookback), current_index):
                if df['equal_highs'].iloc[i]:
                    equal_high_level = df['equal_highs_level'].iloc[i]
                    # If equal highs are just above, don't go short
                    if equal_high_level > current_price and (equal_high_level - current_price) / current_price < 0.01:
                        return False

        return True
