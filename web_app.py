import asyncio
import os
import yaml
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
from agents.data_agent import DataAgent
from agents.analysis_agent import AnalysisAgent
from agents.strategy_agent import StrategyAgent
from agents.backtesting_agent import BacktestingAgent
from agents.reporting_agent import ReportingAgent
from utils.logger import setup_logger
from utils.config import Config
import pandas as pd
from datetime import datetime
import traceback

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload

# Setup logger
logger = setup_logger()

# Global config loader
def load_config():
    config_path = Path(__file__).parent / 'config' / 'config.yaml'
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config

# Validate ticker symbols
def validate_tickers(tickers_str):
    if not tickers_str:
        return ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']  # default
    tickers = [t.strip().upper() for t in tickers_str.split(',') if t.strip()]
    # Basic validation: only allow letters, dots, and hyphens (for indices like ^GSPC)
    import re
    valid_tickers = []
    for ticker in tickers:
        if re.match(r'^[A-Z0-9.\-]+$', ticker):
            valid_tickers.append(ticker)
        else:
            logger.warning(f"Invalid ticker symbol rejected: {ticker}")
    return valid_tickers if valid_tickers else ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA']

# Validate period
def validate_period(period):
    valid_periods = ['1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max']
    return period if period in valid_periods else '2y'

# Run analysis with given parameters
async def run_analysis(symbols, period, initial_capital=100000, commission=0.001, slippage=0.0005, benchmark='SPY'):
    try:
        # Load base config
        config = load_config()
        
        # Override config with user inputs
        config['data_collection']['symbols'] = symbols
        config['backtesting']['initial_capital'] = initial_capital
        config['backtesting']['commission'] = commission
        config['backtesting']['slippage'] = slippage
        config['backtesting']['benchmark'] = benchmark
        
        # Update data agent to use the specified period
        # We'll modify the data agent's collection method temporarily
        
        logger.info(f'Starting analysis with symbols: {symbols}, period: {period}')
        
        # Initialize agents with updated config
        async with DataAgent(config.get('data_collection', {})) as data_agent:
            analysis_agent = AnalysisAgent(config.get('analysis', {}))
            strategy_agent = StrategyAgent(config.get('strategy_generation', {}))
            backtesting_agent = BacktestingAgent(config.get('backtesting', {}))
            reporting_agent = ReportingAgent(config.get('reporting', {}))
            
            # AutoResearch loop settings from config
            max_iterations = config.get('autoresearch', {}).get('max_iterations', 3)  # Reduced for web
            convergence_threshold = config.get('autoresearch', {}).get('convergence_threshold', 0.01)
            performance_metric = config.get('autoresearch', {}).get('performance_metric', 'sharpe_ratio')
            
            best_performance = float('-inf')
            best_strategies = None
            backtesting_results = None
            
            for iteration in range(max_iterations):
                logger.info(f'Web analysis iteration {iteration+1}/{max_iterations}')
                
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
                
                # Step 6: Generate report (optional for intermediate iterations)
                # We'll skip saving intermediate reports for web to avoid clutter
            
            logger.info('Web analysis completed')
            
            # Prepare results
            results = {
                'status': 'success',
                'iteration_completed': iteration + 1,
                'performance_metric': performance_metric,
                'best_performance': best_performance if best_performance != float('-inf') else None,
                'backtesting_results': backtesting_results,
                'timestamp': datetime.now().isoformat()
            }
            
            if best_strategies:
                results['best_strategies'] = best_strategies
                # Generate final report
                final_report = await reporting_agent.generate_report({
                    'performance_metrics': {performance_metric: best_performance},
                    'best_strategies': best_strategies
                })
                # Save report
                report_path = await reporting_agent.save_report(final_report, filename=f'web_report_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
                results['report_path'] = report_path
            else:
                results['warning'] = 'No strategies were generated or evaluated.'
            
            return results
            
    except Exception as e:
        logger.error(f'Error in web analysis: {str(e)}')
        logger.error(traceback.format_exc())
        return {
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat()
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        # Get form data
        data = request.get_json() if request.is_json else request.form
        
        # Extract and validate parameters
        symbols_str = data.get('symbols', '')
        period = data.get('period', '2y')
        initial_capital = float(data.get('initial_capital', 100000))
        commission = float(data.get('commission', 0.001))
        slippage = float(data.get('slippage', 0.0005))
        benchmark = data.get('benchmark', 'SPY').upper()
        
        # Validate inputs
        symbols = validate_tickers(symbols_str)
        period = validate_period(period)
        
        # Additional validation
        if initial_capital <= 0:
            return jsonify({'status': 'error', 'message': 'Initial capital must be positive'}), 400
        if commission < 0 or commission > 0.1:
            return jsonify({'status': 'error', 'message': 'Commission must be between 0 and 0.1'}), 400
        if slippage < 0 or slippage > 0.1:
            return jsonify({'status': 'error', 'message': 'Slippage must be between 0 and 0.1'}), 400
        
        # Run analysis asynchronously
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(run_analysis(
            symbols, period, initial_capital, commission, slippage, benchmark
        ))
        loop.close()
        
        return jsonify(result)
        
    except ValueError as e:
        return jsonify({'status': 'error', 'message': f'Invalid input: {str(e)}'}), 400
    except Exception as e:
        logger.error(f'Error in /analyze endpoint: {str(e)}')
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500

@app.route('/download/<filename>')
def download_file(filename):
    # Security: only allow downloading from results directory
    safe_filename = os.path.basename(filename)
    results_dir = Path(__file__).parent / 'data' / 'results'
    file_path = results_dir / safe_filename
    
    # Prevent directory traversal
    if not file_path.is_relative_to(results_dir):
        return jsonify({'status': 'error', 'message': 'Access denied'}), 403
    
    if not file_path.exists():
        return jsonify({'status': 'error', 'message': 'File not found'}), 404
    
    return send_from_directory(results_dir, safe_filename, as_attachment=True)

@app.route('/health')
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs('data/results', exist_ok=True)
    os.makedirs('logs', exist_ok=True)
    os.makedirs('templates', exist_ok=True)
    
    # Get port from environment variable (for platforms like Render, Heroku) or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=False)