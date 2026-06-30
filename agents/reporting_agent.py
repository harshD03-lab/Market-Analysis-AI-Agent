import asyncio
import json
from typing import Dict, Any, Optional
from utils.logger import setup_logger
import logging

import asyncio
import json
from pathlib import Path
from typing import Dict, Any, Optional

class ReportingAgent:
    def __init__(self, config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    async def generate_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a report based on backtesting and optimization results"""
        self.logger.info('Generating report...')
        await asyncio.sleep(0.1)
        
        is_final = 'best_strategies' in results
        
        lines = []
        if is_final:
            lines.append("# Final Market Analysis & Strategy Optimization Report")
            lines.append("\n## Executive Summary")
            best_perf = results.get('performance_metrics', {}).get('sharpe_ratio', 0.0)
            lines.append(f"The AutoResearch loop completed successfully. The optimized trading strategy achieved a best portfolio Sharpe Ratio of **{best_perf:.4f}**.")
            
            best_strat = results.get('best_strategies', {})
            best_params = best_strat.get('best_parameters', {})
            lines.append("\n### Optimized Strategy Parameters")
            for param, val in best_params.items():
                lines.append(f"- **{param}**: {val}")
                
            history = best_strat.get('history', [])
            if history:
                lines.append("\n### Optimization History")
                lines.append("| Iteration | Parameters Tried | Portfolio Sharpe Ratio |")
                lines.append("|---|---|---|")
                for i, (params, perf) in enumerate(history):
                    # Format params dict to a readable string
                    params_str = ", ".join([f"{k}={v}" for k, v in params.items()])
                    lines.append(f"| {i+1} | {params_str} | {perf:.4f} |")
        else:
            lines.append("# Intermediate AutoResearch Iteration Report")
            
            params = results.get('parameters_tested', {})
            lines.append("\n### Strategy Parameters Tested")
            for param, val in params.items():
                lines.append(f"- **{param}**: {val}")
                
            perf = results.get('performance_metrics', {})
            lines.append("\n### Portfolio Performance Metrics")
            for k, v in perf.items():
                if k == 'sharpe_ratio':
                    lines.append(f"- **{k.replace('_', ' ').title()}**: {v:.4f}")
                else:
                    lines.append(f"- **{k.replace('_', ' ').title()}**: {v*100:.2f}%")
                
            asset_tests = results.get('asset_backtests', {})
            if asset_tests:
                lines.append("\n### Asset Backtest Breakdown")
                lines.append("| Asset | Sharpe Ratio | Cumulative Return | Max Drawdown | Trades |")
                lines.append("|---|---|---|---|---|")
                for symbol, metrics in asset_tests.items():
                    lines.append(f"| {symbol} | {metrics['sharpe_ratio']:.4f} | {metrics['cumulative_return']*100:.2f}% | {metrics['max_drawdown']*100:.2f}% | {metrics['num_trades']} |")
                    
        report_content = "\n".join(lines)
        
        return {
            'content': report_content,
            'is_final': is_final
        }

    async def save_report(self, report: Dict[str, Any], filename: Optional[str] = None) -> None:
        """Save the report to a file"""
        self.logger.info('Saving report...')
        await asyncio.sleep(0.1)
        
        if filename is None:
            filename = 'intermediate_report'
            
        results_dir = Path("data/results")
        results_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = results_dir / f"{filename}.md"
        with open(filepath, 'w') as f:
            f.write(report['content'])
            
        self.logger.info(f'Report successfully saved as {filepath.resolve()}')