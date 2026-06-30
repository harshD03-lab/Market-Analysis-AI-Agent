import asyncio
from typing import Dict, Any
from utils.logger import setup_logger
import logging

import pandas as pd
import random
from typing import Dict, Any, Optional

class StrategyAgent:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Hyperparameters for optimization
        self.best_performance = float('-inf')
        self.best_params = {
            'fast_window': 20,
            'slow_window': 50,
            'rsi_lower': 30,
            'rsi_upper': 70
        }
        self.current_params = self.best_params.copy()
        self.history = []
        self.iteration = 0

    async def generate_strategies(self, analysis_results: Dict[str, Any], feedback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate trading strategies based on analysis results and feedback"""
        self.logger.info(f'Generating trading strategies (Iteration {self.iteration+1})...')
        await asyncio.sleep(0.1)
        
        # If we have feedback from the previous iteration, process it
        if feedback is not None:
            perf = feedback.get('performance_metrics', {}).get('sharpe_ratio', 0.0)
            self.history.append((self.current_params.copy(), perf))
            self.logger.info(f"Feedback received: Sharpe ratio = {perf:.4f} for parameters: {self.current_params}")
            
            # If the previous parameters outperformed, save them as the best parameters
            if perf > self.best_performance:
                self.best_performance = perf
                self.best_params = self.current_params.copy()
                self.logger.info(f"New best performance: {self.best_performance:.4f} with params: {self.best_params}")
            
            # Select new parameters to explore by perturbing the best parameters
            self.current_params = self.best_params.copy()
            param_to_perturb = random.choice(['fast_window', 'slow_window', 'rsi_lower', 'rsi_upper'])
            
            if param_to_perturb == 'fast_window':
                self.current_params['fast_window'] = random.choice([10, 20])
            elif param_to_perturb == 'slow_window':
                self.current_params['slow_window'] = random.choice([50, 100])
            elif param_to_perturb == 'rsi_lower':
                self.current_params['rsi_lower'] = random.choice([25, 30, 35])
            elif param_to_perturb == 'rsi_upper':
                self.current_params['rsi_upper'] = random.choice([65, 70, 75])
                
            self.logger.info(f"Exploring new parameters: {self.current_params}")
        else:
            self.logger.info(f"Initial run. Using default parameters: {self.current_params}")

        self.iteration += 1

        # Generate signals based on indicators
        signals = {}
        indicators = analysis_results.get('indicators', {})
        
        fast_key = f"sma_{self.current_params['fast_window']}"
        slow_key = f"sma_{self.current_params['slow_window']}"
        rsi_lower = self.current_params['rsi_lower']
        rsi_upper = self.current_params['rsi_upper']

        for symbol, ind in indicators.items():
            close = ind['close']
            sma_fast = ind[fast_key]
            sma_slow = ind[slow_key]
            rsi = ind['rsi_14']
            
            holding = 0
            position = []
            
            for date in close.index:
                f_val = sma_fast.loc[date]
                s_val = sma_slow.loc[date]
                r_val = rsi.loc[date]
                
                # Default to out-of-market if values are NaN
                if pd.isna(f_val) or pd.isna(s_val) or pd.isna(r_val):
                    position.append(0)
                    continue
                    
                if holding == 0:
                    # Buy when short-term trend is positive and RSI is not overbought
                    if f_val > s_val and r_val < rsi_upper:
                        holding = 1
                else:
                    # Sell when short-term trend reverses or RSI becomes overbought
                    if f_val < s_val or r_val > rsi_lower:
                        holding = 0
                position.append(holding)
                
            sig = pd.Series(position, index=close.index)
            signals[symbol] = sig
            self.logger.info(f"Generated signals for {symbol} (holds: {sig.sum()} days out of {len(sig)})")

        strategies = {
            'parameters': self.current_params.copy(),
            'best_parameters': self.best_params.copy(),
            'best_performance': self.best_performance,
            'signals': signals,
            'history': self.history.copy()
        }
        self.logger.info('Strategy generation completed')
        return strategies