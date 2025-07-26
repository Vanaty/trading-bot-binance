import logging
import pandas as pd
import numpy as np
import ta
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from config import TradingConfig, STRATEGY_CONFIG
from binance_client import binance_client

@dataclass
class BacktestResult:
    """Dataclass to store backtesting results"""
    symbol: str
    strategy: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    score: float

class AdvancedStrategy:
    """Advanced trading strategy with multiple indicators"""
    
    def __init__(self):
        self.backtest_results = {}
        
    def calculate_bollinger_bands(self, df: pd.DataFrame, window: int = 20) -> Tuple[pd.Series, pd.Series, pd.Series]:
        """Calculate Bollinger Bands"""
        bb_upper = ta.volatility.bollinger_hband(df.Close, window=window)
        bb_lower = ta.volatility.bollinger_lband(df.Close, window=window)
        bb_middle = ta.volatility.bollinger_mavg(df.Close, window=window)
        return bb_upper, bb_middle, bb_lower
    
    def calculate_vwap(self, df: pd.DataFrame) -> pd.Series:
        """Calculate Volume Weighted Average Price"""
        return ta.volume.volume_weighted_average_price(df.High, df.Low, df.Close, df.Volume)
    
    def calculate_fibonacci_levels(self, df: pd.DataFrame, period: int = 50) -> Dict[str, float]:
        """Calculate Fibonacci retracement levels"""
        high = df.High.rolling(period).max().iloc[-1]
        low = df.Low.rolling(period).min().iloc[-1]
        diff = high - low
        
        levels = {
            'level_0': high,
            'level_236': high - 0.236 * diff,
            'level_382': high - 0.382 * diff,
            'level_500': high - 0.5 * diff,
            'level_618': high - 0.618 * diff,
            'level_100': low
        }
        return levels
    
    def calculate_volume_profile(self, df: pd.DataFrame) -> Dict[str, float]:
        """Calculate volume analysis indicators"""
        # Calculate volume moving average using pandas instead of ta.volume.volume_sma
        volume_sma = df.Volume.rolling(window=20).mean()
        volume_ratio = df.Volume.iloc[-1] / volume_sma.iloc[-1] if volume_sma.iloc[-1] > 0 else 1
        
        return {
            'volume_ratio': volume_ratio,
            'avg_volume': volume_sma.iloc[-1],
            'current_volume': df.Volume.iloc[-1]
        }
    
    def rsi_bollinger_vwap_strategy(self, symbol: str) -> Dict[str, any]:
        """Enhanced RSI + Bollinger Bands + VWAP strategy"""
        try:
            kl = binance_client.get_klines(symbol)
            if kl is None or len(kl) < 50:
                return {'signal': 'none', 'strength': 0, 'reasons': []}
            
            # Technical indicators
            rsi = ta.momentum.RSIIndicator(kl.Close).rsi()
            bb_upper, bb_middle, bb_lower = self.calculate_bollinger_bands(kl)
            vwap = self.calculate_vwap(kl)
            ema200 = ta.trend.ema_indicator(kl.Close, window=200)
            volume_profile = self.calculate_volume_profile(kl)
            
            current_price = kl.Close.iloc[-1]
            signals = []
            reasons = []
            
            # RSI signals
            if rsi.iloc[-1] < 30 and rsi.iloc[-2] >= 30:
                signals.append('buy')
                reasons.append('RSI oversold bounce')
            elif rsi.iloc[-1] > 70 and rsi.iloc[-2] <= 70:
                signals.append('sell')
                reasons.append('RSI overbought decline')
            
            # Bollinger Bands signals
            if current_price <= bb_lower.iloc[-1] * 1.01:
                signals.append('buy')
                reasons.append('Price near BB lower band')
            elif current_price >= bb_upper.iloc[-1] * 0.99:
                signals.append('sell')
                reasons.append('Price near BB upper band')
            
            # VWAP signals
            if current_price > vwap.iloc[-1] and kl.Close.iloc[-2] <= vwap.iloc[-2]:
                signals.append('buy')
                reasons.append('Price crossed above VWAP')
            elif current_price < vwap.iloc[-1] and kl.Close.iloc[-2] >= vwap.iloc[-2]:
                signals.append('sell')
                reasons.append('Price crossed below VWAP')
            
            # Trend filter
            trend_bullish = current_price > ema200.iloc[-1]
            if not trend_bullish and 'buy' in signals:
                reasons.append('Trend filter: bearish trend')
            elif trend_bullish and 'sell' in signals:
                reasons.append('Trend filter: bullish trend')
            
            # Volume filter
            if volume_profile['volume_ratio'] < STRATEGY_CONFIG['volume_threshold']:
                reasons.append(f"Low volume: {volume_profile['volume_ratio']:.2f}")
            
            # Determine final signal
            buy_signals = signals.count('buy')
            sell_signals = signals.count('sell')
            
            if buy_signals >= STRATEGY_CONFIG['min_signal_strength'] and trend_bullish and volume_profile['volume_ratio'] >= STRATEGY_CONFIG['volume_threshold']:
                return {'signal': 'buy', 'strength': buy_signals, 'reasons': reasons}
            elif sell_signals >= STRATEGY_CONFIG['min_signal_strength'] and not trend_bullish and volume_profile['volume_ratio'] >= STRATEGY_CONFIG['volume_threshold']:
                return {'signal': 'sell', 'strength': sell_signals, 'reasons': reasons}
            else:
                return {'signal': 'none', 'strength': max(buy_signals, sell_signals), 'reasons': reasons}
                
        except Exception as e:
            logging.error(f"Error in RSI-BB-VWAP strategy for {symbol}: {str(e)}")
            return {'signal': 'none', 'strength': 0, 'reasons': [f'Error: {str(e)}']}
    
    def macd_ema_volume_strategy(self, symbol: str) -> Dict[str, any]:
        """MACD + EMA + Volume strategy"""
        try:
            kl = binance_client.get_klines(symbol)
            if kl is None or len(kl) < 50:
                return {'signal': 'none', 'strength': 0, 'reasons': []}
            
            # Technical indicators
            macd_line = ta.trend.macd(kl.Close)
            macd_signal = ta.trend.macd_signal(kl.Close)
            macd_diff = ta.trend.macd_diff(kl.Close)
            ema50 = ta.trend.ema_indicator(kl.Close, window=50)
            ema200 = ta.trend.ema_indicator(kl.Close, window=200)
            volume_profile = self.calculate_volume_profile(kl)
            
            signals = []
            reasons = []
            
            # MACD signals
            if (macd_diff.iloc[-1] > 0 and macd_diff.iloc[-2] <= 0 and 
                macd_line.iloc[-1] > macd_signal.iloc[-1]):
                signals.append('buy')
                reasons.append('MACD bullish crossover')
            elif (macd_diff.iloc[-1] < 0 and macd_diff.iloc[-2] >= 0 and 
                  macd_line.iloc[-1] < macd_signal.iloc[-1]):
                signals.append('sell')
                reasons.append('MACD bearish crossover')
            
            # EMA crossover
            if (ema50.iloc[-1] > ema200.iloc[-1] and ema50.iloc[-2] <= ema200.iloc[-2]):
                signals.append('buy')
                reasons.append('EMA50 crossed above EMA200')
            elif (ema50.iloc[-1] < ema200.iloc[-1] and ema50.iloc[-2] >= ema200.iloc[-2]):
                signals.append('sell')
                reasons.append('EMA50 crossed below EMA200')
            
            # Volume confirmation
            if volume_profile['volume_ratio'] >= STRATEGY_CONFIG['volume_threshold']:
                if signals:
                    reasons.append(f"Volume confirmed: {volume_profile['volume_ratio']:.2f}x")
            else:
                reasons.append(f"Insufficient volume: {volume_profile['volume_ratio']:.2f}x")
            
            buy_signals = signals.count('buy')
            sell_signals = signals.count('sell')
            
            if buy_signals >= 2 and volume_profile['volume_ratio'] >= STRATEGY_CONFIG['volume_threshold']:
                return {'signal': 'buy', 'strength': buy_signals, 'reasons': reasons}
            elif sell_signals >= 2 and volume_profile['volume_ratio'] >= STRATEGY_CONFIG['volume_threshold']:
                return {'signal': 'sell', 'strength': sell_signals, 'reasons': reasons}
            else:
                return {'signal': 'none', 'strength': max(buy_signals, sell_signals), 'reasons': reasons}
                
        except Exception as e:
            logging.error(f"Error in MACD-EMA-Volume strategy for {symbol}: {str(e)}")
            return {'signal': 'none', 'strength': 0, 'reasons': [f'Error: {str(e)}']}
    
    def stochastic_fibonacci_trend_strategy(self, symbol: str) -> Dict[str, any]:
        """Stochastic + Fibonacci + Trend strategy"""
        try:
            kl = binance_client.get_klines(symbol)
            if kl is None or len(kl) < 50:
                return {'signal': 'none', 'strength': 0, 'reasons': []}
            
            # Technical indicators
            stoch_k = ta.momentum.stoch(kl.High, kl.Low, kl.Close)
            stoch_d = ta.momentum.stoch_signal(kl.High, kl.Low, kl.Close)
            fib_levels = self.calculate_fibonacci_levels(kl)
            ema100 = ta.trend.ema_indicator(kl.Close, window=100)
            atr = ta.volatility.average_true_range(kl.High, kl.Low, kl.Close)
            
            current_price = kl.Close.iloc[-1]
            signals = []
            reasons = []
            
            # Stochastic signals
            if (stoch_k.iloc[-1] < 20 and stoch_k.iloc[-2] >= 20 and 
                stoch_k.iloc[-1] > stoch_d.iloc[-1]):
                signals.append('buy')
                reasons.append('Stochastic oversold reversal')
            elif (stoch_k.iloc[-1] > 80 and stoch_k.iloc[-2] <= 80 and 
                  stoch_k.iloc[-1] < stoch_d.iloc[-1]):
                signals.append('sell')
                reasons.append('Stochastic overbought reversal')
            
            # Fibonacci retracement signals
            if abs(current_price - fib_levels['level_618']) / current_price < 0.005:
                signals.append('buy')
                reasons.append('Price near Fibonacci 61.8% retracement')
            elif abs(current_price - fib_levels['level_382']) / current_price < 0.005:
                signals.append('sell')
                reasons.append('Price near Fibonacci 38.2% retracement')
            
            # Trend confirmation
            if current_price > ema100.iloc[-1]:
                if 'sell' in signals:
                    reasons.append('Trend filter: against bullish trend')
            else:
                if 'buy' in signals:
                    reasons.append('Trend filter: against bearish trend')
            
            buy_signals = signals.count('buy')
            sell_signals = signals.count('sell')
            
            # Trend alignment check
            trend_aligned = ((current_price > ema100.iloc[-1] and buy_signals > 0) or 
                           (current_price < ema100.iloc[-1] and sell_signals > 0))
            
            if buy_signals >= 2 and trend_aligned:
                return {'signal': 'buy', 'strength': buy_signals, 'reasons': reasons}
            elif sell_signals >= 2 and trend_aligned:
                return {'signal': 'sell', 'strength': sell_signals, 'reasons': reasons}
            else:
                return {'signal': 'none', 'strength': max(buy_signals, sell_signals), 'reasons': reasons}
                
        except Exception as e:
            logging.error(f"Error in Stoch-Fib-Trend strategy for {symbol}: {str(e)}")
            return {'signal': 'none', 'strength': 0, 'reasons': [f'Error: {str(e)}']}
    
    def backtest_strategy(self, symbol: str, strategy_name: str, days: int = 30) -> BacktestResult:
        """Backtest a strategy on historical data"""
        try:
            # Get historical data
            end_time = datetime.now()
            start_time = end_time - timedelta(days=days)
            
            hist_data = pd.DataFrame(binance_client.client.klines(
                symbol, '15m', 
                startTime=int(start_time.timestamp() * 1000),
                endTime=int(end_time.timestamp() * 1000),
                limit=1000
            ))
            
            if hist_data.empty or len(hist_data.columns) < 6:
                return BacktestResult(symbol, strategy_name, 0, 0, 0, 0, 0, 0, 0, 0)
            
            hist_data = hist_data.iloc[:, :6]
            hist_data.columns = ['Time', 'Open', 'High', 'Low', 'Close', 'Volume']
            hist_data = hist_data.set_index('Time')
            hist_data.index = pd.to_datetime(hist_data.index, unit='ms')
            hist_data = hist_data.astype(float)
            
            # Simulate trading
            trades = []
            position = None
            entry_price = 0
            
            for i in range(200, len(hist_data) - 1):
                current_data = hist_data.iloc[:i+1]
                
                # Get strategy signal
                if strategy_name == 'rsi_bb_vwap':
                    signal_data = self._simulate_rsi_bb_vwap(current_data)
                elif strategy_name == 'macd_ema_vol':
                    signal_data = self._simulate_macd_ema_vol(current_data)
                elif strategy_name == 'stoch_fib_trend':
                    signal_data = self._simulate_stoch_fib_trend(current_data)
                else:
                    continue
                
                signal = signal_data['signal']
                current_price = current_data.Close.iloc[-1]
                
                # Execute trades
                if position is None and signal in ['buy', 'sell']:
                    position = signal
                    entry_price = current_price
                    
                elif position is not None:
                    pnl_pct = 0
                    if position == 'buy':
                        pnl_pct = (current_price - entry_price) / entry_price
                    else:
                        pnl_pct = (entry_price - current_price) / entry_price
                    
                    # Exit on TP/SL or opposite signal
                    if pnl_pct >= TradingConfig.TAKE_PROFIT or pnl_pct <= -TradingConfig.STOP_LOSS or signal != position:
                        trades.append({
                            'entry_price': entry_price,
                            'exit_price': current_price,
                            'position': position,
                            'pnl_pct': pnl_pct,
                            'profit': pnl_pct > 0
                        })
                        position = None
            
            # Calculate statistics
            if not trades:
                return BacktestResult(symbol, strategy_name, 0, 0, 0, 0, 0, 0, 0, 0)
            
            total_trades = len(trades)
            winning_trades = sum(1 for t in trades if t['profit'])
            losing_trades = total_trades - winning_trades
            win_rate = winning_trades / total_trades if total_trades > 0 else 0
            total_pnl = sum(t['pnl_pct'] for t in trades)
            
            # Calculate max drawdown
            cumulative_pnl = 0
            peak = 0
            max_drawdown = 0
            for trade in trades:
                cumulative_pnl += trade['pnl_pct']
                if cumulative_pnl > peak:
                    peak = cumulative_pnl
                drawdown = (peak - cumulative_pnl) / (1 + peak) if peak > 0 else 0
                max_drawdown = max(max_drawdown, drawdown)
            
            # Calculate Sharpe ratio
            returns = [t['pnl_pct'] for t in trades]
            if len(returns) > 1 and np.std(returns) > 0:
                sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(len(returns))
            else:
                sharpe_ratio = 0
            
            # Calculate overall score
            score = (win_rate * 40 + 
                    min(total_pnl * 100, 30) + 
                    max(30 - max_drawdown * 100, 0) + 
                    min(sharpe_ratio * 10, 30))
            
            result = BacktestResult(
                symbol=symbol,
                strategy=strategy_name,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                win_rate=win_rate,
                total_pnl=total_pnl,
                max_drawdown=max_drawdown,
                sharpe_ratio=sharpe_ratio,
                score=score
            )
            
            logging.info(f"Backtest {symbol} {strategy_name}: Score={score:.1f}, WinRate={win_rate:.2%}, PnL={total_pnl:.2%}")
            return result
            
        except Exception as e:
            logging.error(f"Backtest error for {symbol} {strategy_name}: {str(e)}")
            return BacktestResult(symbol, strategy_name, 0, 0, 0, 0, 0, 0, 0, 0)
    
    def _simulate_rsi_bb_vwap(self, data):
        """Simulate RSI+BB+VWAP strategy for backtesting"""
        rsi = ta.momentum.RSIIndicator(data.Close).rsi()
        if len(rsi) < 2:
            return {'signal': 'none'}
        
        if rsi.iloc[-1] < 30 and rsi.iloc[-2] >= 30:
            return {'signal': 'buy'}
        elif rsi.iloc[-1] > 70 and rsi.iloc[-2] <= 70:
            return {'signal': 'sell'}
        return {'signal': 'none'}
    
    def _simulate_macd_ema_vol(self, data):
        """Simulate MACD+EMA+Volume strategy for backtesting"""
        macd_diff = ta.trend.macd_diff(data.Close)
        if len(macd_diff) < 2:
            return {'signal': 'none'}
        
        if macd_diff.iloc[-1] > 0 and macd_diff.iloc[-2] <= 0:
            return {'signal': 'buy'}
        elif macd_diff.iloc[-1] < 0 and macd_diff.iloc[-2] >= 0:
            return {'signal': 'sell'}
        return {'signal': 'none'}
    
    def _simulate_stoch_fib_trend(self, data):
        """Simulate Stoch+Fib+Trend strategy for backtesting"""
        stoch_k = ta.momentum.stoch(data.High, data.Low, data.Close)
        if len(stoch_k) < 2:
            return {'signal': 'none'}
        
        if stoch_k.iloc[-1] < 20 and stoch_k.iloc[-2] >= 20:
            return {'signal': 'buy'}
        elif stoch_k.iloc[-1] > 80 and stoch_k.iloc[-2] <= 80:
            return {'signal': 'sell'}
        return {'signal': 'none'}
    
    def get_best_strategy_signal(self, symbol: str) -> Dict[str, any]:
        """Get the best signal from all strategies with backtesting validation"""
        try:
            if STRATEGY_CONFIG['backtesting_enabled']:
                strategies = {
                    'rsi_bb_vwap': self.rsi_bollinger_vwap_strategy,
                    'macd_ema_vol': self.macd_ema_volume_strategy,
                    'stoch_fib_trend': self.stochastic_fibonacci_trend_strategy
                }
                
                best_score = 0
                best_signal = {'signal': 'none', 'strength': 0, 'reasons': []}
                
                for strategy_name, strategy_func in strategies.items():
                    signal_data = strategy_func(symbol)
                    
                    if signal_data['signal'] != 'none':
                        backtest_result = self.backtest_strategy(symbol, strategy_name)
                        
                        if backtest_result.score >= STRATEGY_CONFIG['min_backtest_score']:
                            if backtest_result.score > best_score:
                                best_score = backtest_result.score
                                best_signal = signal_data
                                best_signal['backtest_score'] = backtest_result.score
                                best_signal['strategy'] = strategy_name
                                
                        logging.info(f"{symbol} {strategy_name}: Signal={signal_data['signal']}, "
                                   f"Score={backtest_result.score:.1f}")
                
                return best_signal
            else:
                return self.rsi_bollinger_vwap_strategy(symbol)
                
        except Exception as e:
            logging.error(f"Error getting best strategy signal for {symbol}: {str(e)}")
            return {'signal': 'none', 'strength': 0, 'reasons': [f'Error: {str(e)}']}

# Global strategy instance
strategy_engine = AdvancedStrategy()
