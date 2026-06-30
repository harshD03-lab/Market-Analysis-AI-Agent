import asyncio
from typing import Dict, Any
from utils.logger import setup_logger
import logging

import asyncio
import numpy as np
import pandas as pd
from typing import Dict, Any

class BacktestingAgent:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    async def backtest(self, strategies: Dict[str, Any], market_data: Dict[str, Any]) -> Dict[str, Any]:
        """Backtest strategies against historical data"""
        self.logger.info('Starting backtesting...')
        await asyncio.sleep(0.1)
        
        signals = strategies.get('signals', {})
        parameters = strategies.get('parameters', {})
        
        commission = self.config.get('commission', 0.001)
        slippage = self.config.get('slippage', 0.0005)
        
        asset_backtests = {}
        all_strategy_returns = []
        
        for symbol, sig in signals.items():
            if symbol not in market_data:
                continue
            
            price_data = market_data[symbol].get('price_data')
            if price_data is None or price_data.empty or 'Close' not in price_data.columns:
                continue
                
            close = price_data['Close']
            
            # 1. Compute asset returns
            asset_returns = close.pct_change().fillna(0)
            
            # 2. Shift signals by 1 day to avoid look-ahead bias
            strategy_signals = sig.shift(1).fillna(0)
            
            # 3. Compute raw strategy returns
            strategy_returns = strategy_signals * asset_returns
            
            # 4. Compute trades & transaction costs
            trades = strategy_signals.diff().abs().fillna(0)
            transaction_costs = trades * (commission + slippage)
            
            # 5. Compute net strategy returns
            strategy_net_returns = strategy_returns - transaction_costs
            all_strategy_returns.append(strategy_net_returns)
            
            # 6. Calculate individual metrics
            cum_returns = (1 + strategy_net_returns).cumprod()
            final_cum_ret = cum_returns.iloc[-1] - 1 if not cum_returns.empty else 0.0
            
            mean_ret = strategy_net_returns.mean()
            std_ret = strategy_net_returns.std()
            sharpe = (mean_ret / std_ret * np.sqrt(252)) if std_ret > 1e-9 else 0.0
            
            running_max = cum_returns.cummax()
            drawdown = (cum_returns - running_max) / (running_max + 1e-9)
            max_dd = drawdown.min() if not drawdown.empty else 0.0
            
            asset_backtests[symbol] = {
                'sharpe_ratio': float(sharpe),
                'cumulative_return': float(final_cum_ret),
                'max_drawdown': float(max_dd),
                'num_trades': int(trades.sum())
            }
            self.logger.info(f"Backtested {symbol}: Sharpe={sharpe:.4f}, Return={final_cum_ret*100:.2f}%, Trades={int(trades.sum())}")
            
        # Compute portfolio level metrics if we have active assets
        if all_strategy_returns:
            df_returns = pd.DataFrame(all_strategy_returns).T.fillna(0)
            portfolio_returns = df_returns.mean(axis=1)
            
            portfolio_cum = (1 + portfolio_returns).cumprod()
            port_final_ret = portfolio_cum.iloc[-1] - 1 if not portfolio_cum.empty else 0.0
            
            p_mean = portfolio_returns.mean()
            p_std = portfolio_returns.std()
            portfolio_sharpe = (p_mean / p_std * np.sqrt(252)) if p_std > 1e-9 else 0.0
            
            p_running_max = portfolio_cum.cummax()
            p_drawdown = (portfolio_cum - p_running_max) / (p_running_max + 1e-9)
            portfolio_max_dd = p_drawdown.min() if not p_drawdown.empty else 0.0
        else:
            portfolio_sharpe = 0.0
            port_final_ret = 0.0
            portfolio_max_dd = 0.0
            
        performance_metrics = {
            'sharpe_ratio': float(portfolio_sharpe),
            'cumulative_return': float(port_final_ret),
            'max_drawdown': float(portfolio_max_dd),
        }
        
        results = {
            'performance_metrics': performance_metrics,
            'asset_backtests': asset_backtests,
            'parameters_tested': parameters,
            'best_parameters': strategies.get('best_parameters', {}),
            'history': strategies.get('history', [])
        }
        self.logger.info(f"Backtesting completed. Portfolio Sharpe: {portfolio_sharpe:.4f}, Return: {port_final_ret*100:.2f}%")
        return results