import asyncio
import aiohttp
import pandas as pd
import yfinance as yf
from typing import Dict, Any, List
from utils.logger import setup_logger
import logging
from datetime import datetime, timedelta

class DataAgent:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = None
        self.symbols = config.get('symbols', ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA'])

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def collect_data(self) -> Dict[str, Any]:
        """Collect market data from various sources"""
        self.logger.info('Collecting market data...')
        
        # Fetch data for multiple symbols
        market_data = {}
        
        for symbol in self.symbols:
            try:
                # Get historical data for the past 6 months
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="6mo")
                
                if not hist.empty:
                    market_data[symbol] = {
                        'price_data': hist,
                        'info': ticker.info,
                        'history_metadata': getattr(ticker, 'history_metadata', {})
                    }
                    self.logger.info(f'Successfully fetched data for {symbol}')
                else:
                    self.logger.warning(f'No data found for {symbol}')
                    
            except Exception as e:
                self.logger.error(f'Error fetching data for {symbol}: {str(e)}')
                market_data[symbol] = {
                    'price_data': pd.DataFrame(),
                    'info': {},
                    'history_metadata': {}
                }
        
        # Add market indices data
        indices = ['^GSPC', '^DJI', '^IXIC']  # S&P 500, Dow Jones, NASDAQ
        market_data['indices'] = {}
        
        for index in indices:
            try:
                ticker = yf.Ticker(index)
                hist = ticker.history(period="6mo")
                if not hist.empty:
                    market_data['indices'][index] = {
                        'price_data': hist,
                        'info': ticker.info
                    }
                    self.logger.info(f'Successfully fetched data for index {index}')
                else:
                    self.logger.warning(f'No data found for index {index}')
            except Exception as e:
                self.logger.error(f'Error fetching data for index {index}: {str(e)}')
                market_data['indices'][index] = {
                    'price_data': pd.DataFrame(),
                    'info': {}
                }
        
        self.logger.info('Data collection completed')
        return market_data