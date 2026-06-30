import asyncio
import pandas as pd
import numpy as np
from typing import Dict, Any
from utils.logger import setup_logger
import logging

class AnalysisAgent:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def _calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        delta = series.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        avg_gain = gain.rolling(window=period, min_periods=period).mean()
        avg_loss = loss.rolling(window=period, min_periods=period).mean()
        rs = avg_gain / (avg_loss + 1e-9)
        return 100 - (100 / (1 + rs))

    async def analyze(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze market data and generate insights"""
        self.logger.info('Starting data analysis...')
        await asyncio.sleep(0.1)  # Brief yield
        
        indicators = {}
        
        for symbol, data in market_data.items():
            if symbol == 'indices':
                continue
                
            price_data = data.get('price_data')
            if price_data is None or price_data.empty or 'Close' not in price_data.columns:
                self.logger.warning(f'Skipping analysis for {symbol} due to empty price data')
                continue
                
            close_prices = price_data['Close']
            
            indicators[symbol] = {
                'close': close_prices,
                'sma_10': close_prices.rolling(window=10).mean(),
                'sma_20': close_prices.rolling(window=20).mean(),
                'sma_50': close_prices.rolling(window=50).mean(),
                'sma_100': close_prices.rolling(window=100).mean(),
                'rsi_14': self._calculate_rsi(close_prices, 14)
            }
            self.logger.info(f'Calculated technical indicators for {symbol}')

        analysis_results = {
            'indicators': indicators
        }
        self.logger.info('Data analysis completed')
        return analysis_results