import asyncio
import yaml
from pathlib import Path
from agents.data_agent import DataAgent
from agents.analysis_agent import AnalysisAgent
from agents.strategy_agent import StrategyAgent
from agents.backtesting_agent import BacktestingAgent
from agents.reporting_agent import ReportingAgent
from utils.logger import setup_logger
from utils.config import Config

async def main():
    # Setup logger
    logger = setup_logger()
    logger.info('Starting Market Analysis AI Agent')

    # Load configuration
    config = Config()
    logger.info('Configuration loaded')

    # Initialize agents
    async with DataAgent(config.get('data_collection', {})) as data_agent:
        analysis_agent = AnalysisAgent(config.get('analysis', {}))
        strategy_agent = StrategyAgent(config.get('strategy_generation', {}))
        backtesting_agent = BacktestingAgent(config.get('backtesting', {}))
        reporting_agent = ReportingAgent(config.get('reporting', {}))

        # AutoResearch loop
        max_iterations = config.get('autoresearch', {}).get('max_iterations', 10)
        convergence_threshold = config.get('autoresearch', {}).get('convergence_threshold', 0.01)
        performance_metric = config.get('autoresearch', {}).get('performance_metric', 'sharpe_ratio')

        best_performance = float('-inf')
        best_strategies = None
        backtesting_results = None

        for iteration in range(max_iterations):
            logger.info(f'Starting AutoResearch iteration {iteration+1}/{max_iterations}')

            # Step 1: Collect data
            market_data = await data_agent.collect_data()

            # Step 2: Analyze data
            analysis_results = await analysis_agent.analyze(market_data)

            # Step 3: Generate strategies
            strategies = await strategy_agent.generate_strategies(analysis_results, backtesting_results)

            # Step 4: Backtest strategies
            backtesting_results = await backtesting_agent.backtest(strategies, market_data)

            # Step 5: Evaluate performance
            current_performance = backtesting_results.get('performance_metrics', {}).get(performance_metric, 0)
            logger.info(f'Iteration {iteration+1} performance ({performance_metric}): {current_performance}')

            # Check for convergence
            if abs(current_performance - best_performance) < convergence_threshold:
                logger.info(f'Convergence reached at iteration {iteration+1}')
                break

            if current_performance > best_performance:
                best_performance = current_performance
                best_strategies = strategies
                logger.info(f'New best performance: {best_performance}')

            # Step 6: Generate report
            report = await reporting_agent.generate_report(backtesting_results)
            await reporting_agent.save_report(report)

        logger.info('AutoResearch loop completed')
        if best_strategies:
            logger.info(f'Best strategies found with {performance_metric}: {best_performance}')
            # Generate final report with best strategies
            final_report = await reporting_agent.generate_report({
                'performance_metrics': {performance_metric: best_performance},
                'best_strategies': best_strategies
            })
            await reporting_agent.save_report(final_report, filename='final_report')
        else:
            logger.warning('No strategies were generated or evaluated.')

if __name__ == '__main__':
    asyncio.run(main())