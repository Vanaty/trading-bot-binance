import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
import json
import logging
from typing import Dict, List, Optional
from dataclasses import asdict
import warnings
warnings.filterwarnings('ignore')

class StrategyAnalyzer:
    """Advanced strategy analysis and performance monitoring"""
    
    def __init__(self, results_file='backtest_results.json'):
        self.results_file = results_file
        self.results_history = self.load_results_history()
    
    def load_results_history(self) -> List[Dict]:
        """Load historical backtest results"""
        try:
            with open(self.results_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def save_results_history(self):
        """Save backtest results to file"""
        try:
            with open(self.results_file, 'w') as f:
                json.dump(self.results_history, f, indent=2, default=str)
        except Exception as e:
            logging.error(f"Error saving results: {e}")
    
    def add_backtest_result(self, result):
        """Add a new backtest result to history"""
        result_dict = asdict(result) if hasattr(result, '__dict__') else result
        result_dict['timestamp'] = datetime.now().isoformat()
        self.results_history.append(result_dict)
        self.save_results_history()
    
    def analyze_strategy_performance(self, strategy_name: str, days: int = 30) -> Dict:
        """Analyze performance of a specific strategy"""
        recent_results = [
            r for r in self.results_history 
            if r.get('strategy') == strategy_name and 
            datetime.fromisoformat(r['timestamp']) >= datetime.now() - timedelta(days=days)
        ]
        
        if not recent_results:
            return {}
        
        df = pd.DataFrame(recent_results)
        
        analysis = {
            'strategy': strategy_name,
            'period_days': days,
            'total_backtests': len(df),
            'avg_score': df['score'].mean(),
            'avg_win_rate': df['win_rate'].mean(),
            'avg_total_pnl': df['total_pnl'].mean(),
            'avg_max_drawdown': df['max_drawdown'].mean(),
            'avg_sharpe_ratio': df['sharpe_ratio'].mean(),
            'symbols_tested': df['symbol'].nunique(),
            'best_performing_symbols': df.nlargest(5, 'score')[['symbol', 'score']].to_dict('records'),
            'worst_performing_symbols': df.nsmallest(5, 'score')[['symbol', 'score']].to_dict('records')
        }
        
        return analysis
    
    def generate_performance_report(self) -> str:
        """Generate a comprehensive performance report"""
        if not self.results_history:
            return "No backtest results available."
        
        df = pd.DataFrame(self.results_history)
        
        report = f"""
=== TRADING STRATEGY PERFORMANCE REPORT ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

OVERALL STATISTICS:
- Total Backtests: {len(df)}
- Average Score: {df['score'].mean():.1f}
- Average Win Rate: {df['win_rate'].mean():.2%}
- Average PnL: {df['total_pnl'].mean():.2%}
- Average Max Drawdown: {df['max_drawdown'].mean():.2%}

STRATEGY COMPARISON:
"""
        
        for strategy in df['strategy'].unique():
            strategy_data = df[df['strategy'] == strategy]
            report += f"\n{strategy.upper()}:\n"
            report += f"  - Tests: {len(strategy_data)}\n"
            report += f"  - Avg Score: {strategy_data['score'].mean():.1f}\n"
            report += f"  - Avg Win Rate: {strategy_data['win_rate'].mean():.2%}\n"
            report += f"  - Avg PnL: {strategy_data['total_pnl'].mean():.2%}\n"
        
        report += f"\nTOP 10 BEST PERFORMING SYMBOLS:\n"
        top_symbols = df.nlargest(10, 'score')[['symbol', 'strategy', 'score', 'win_rate']]
        for _, row in top_symbols.iterrows():
            report += f"  {row['symbol']}: {row['score']:.1f} ({row['strategy']}, WR: {row['win_rate']:.1%})\n"
        
        return report
    
    def plot_strategy_comparison(self, save_path='strategy_comparison.png'):
        """Create visualization comparing strategy performances"""
        if not self.results_history:
            logging.warning("No data available for plotting")
            return
        
        df = pd.DataFrame(self.results_history)
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # Score comparison
        df.boxplot(column='score', by='strategy', ax=axes[0,0])
        axes[0,0].set_title('Score Distribution by Strategy')
        axes[0,0].set_xlabel('Strategy')
        axes[0,0].set_ylabel('Score')
        
        # Win rate comparison
        df.boxplot(column='win_rate', by='strategy', ax=axes[0,1])
        axes[0,1].set_title('Win Rate Distribution by Strategy')
        axes[0,1].set_xlabel('Strategy')
        axes[0,1].set_ylabel('Win Rate')
        
        # PnL comparison
        df.boxplot(column='total_pnl', by='strategy', ax=axes[1,0])
        axes[1,0].set_title('PnL Distribution by Strategy')
        axes[1,0].set_xlabel('Strategy')
        axes[1,0].set_ylabel('Total PnL')
        
        # Max drawdown comparison
        df.boxplot(column='max_drawdown', by='strategy', ax=axes[1,1])
        axes[1,1].set_title('Max Drawdown Distribution by Strategy')
        axes[1,1].set_xlabel('Strategy')
        axes[1,1].set_ylabel('Max Drawdown')
        
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close()
        
        logging.info(f"Strategy comparison plot saved to {save_path}")
    
    def get_strategy_recommendations(self) -> Dict[str, List[str]]:
        """Get recommendations for strategy usage"""
        if not self.results_history:
            return {'recommendations': ['No data available for recommendations']}
        
        df = pd.DataFrame(self.results_history)
        recommendations = []
        
        # Analyze recent performance (last 7 days)
        recent_df = df[pd.to_datetime(df['timestamp']) >= datetime.now() - timedelta(days=7)]
        
        if not recent_df.empty:
            best_strategy = recent_df.groupby('strategy')['score'].mean().idxmax()
            recommendations.append(f"Best performing strategy (last 7 days): {best_strategy}")
            
            # High win rate strategies
            high_wr_strategies = recent_df[recent_df['win_rate'] > 0.6]['strategy'].unique()
            if len(high_wr_strategies) > 0:
                recommendations.append(f"High win rate strategies: {', '.join(high_wr_strategies)}")
            
            # Low drawdown strategies
            low_dd_strategies = recent_df[recent_df['max_drawdown'] < 0.1]['strategy'].unique()
            if len(low_dd_strategies) > 0:
                recommendations.append(f"Low drawdown strategies: {', '.join(low_dd_strategies)}")
            
            # Symbols with consistent performance
            symbol_performance = recent_df.groupby('symbol')['score'].agg(['mean', 'count'])
            consistent_symbols = symbol_performance[
                (symbol_performance['mean'] > 60) & (symbol_performance['count'] >= 2)
            ].index.tolist()
            
            if consistent_symbols:
                recommendations.append(f"Consistently good symbols: {', '.join(consistent_symbols[:5])}")
        
        return {'recommendations': recommendations if recommendations else ['Insufficient recent data']}

# Usage example
if __name__ == "__main__":
    analyzer = StrategyAnalyzer()
    
    # Generate and print performance report
    report = analyzer.generate_performance_report()
    print(report)
    
    # Create comparison plots
    analyzer.plot_strategy_comparison()
    
    # Get recommendations
    recommendations = analyzer.get_strategy_recommendations()
    print("\nRECOMMENDations:")
    for rec in recommendations['recommendations']:
        print(f"- {rec}")
