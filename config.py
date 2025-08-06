import os
from typing import Dict, Any
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

class TradingConfig:
    """Centralized configuration for trading strategies"""
    
    # API Configuration
    API_KEY = os.getenv('BINANCE_API_KEY')
    SECRET_KEY = os.getenv('BINANCE_SECRET_KEY')
    
    # Strategy Selection
    ACTIVE_STRATEGIES = [
        'rsi_bb_vwap',
        'macd_ema_vol', 
        'stoch_fib_trend'
    ]
    
    # Signal Requirements
    MIN_SIGNAL_STRENGTH = int(os.getenv('MIN_SIGNAL_STRENGTH', '2'))  # Lowered from 3
    MIN_BACKTEST_SCORE = float(os.getenv('MIN_BACKTEST_SCORE', '45.0'))  # Lowered from 60.0
    ENABLE_BACKTESTING = os.getenv('ENABLE_BACKTESTING', 'false').lower() == 'true'  # Disabled by default
    BACKTEST_DAYS = int(os.getenv('BACKTEST_DAYS', '7'))  # Reduced from 30
    
    # Risk Management
    MAX_POSITION_SIZE_PCT = float(os.getenv('MAX_POSITION_SIZE_PCT', '2.0'))
    MAX_DAILY_TRADES = int(os.getenv('MAX_DAILY_TRADES', '10'))
    MAX_CONCURRENT_POSITIONS = int(os.getenv('MAX_CONCURRENT_POSITIONS', '5'))
    
    # Trading Parameters
    TAKE_PROFIT = max(0.001, min(0.1, float(os.getenv('TAKE_PROFIT', '0.02'))))  # Increased
    STOP_LOSS = max(0.001, min(0.1, float(os.getenv('STOP_LOSS', '0.015'))))  # Increased
    VOLUME = max(5, min(1000, float(os.getenv('VOLUME', '15'))))  # Increased minimum
    LEVERAGE = max(1, min(125, int(os.getenv('LEVERAGE', '10'))))
    MARGIN_TYPE = os.getenv('MARGIN_TYPE', 'ISOLATED')
    MAX_POSITIONS = max(1, min(50, int(os.getenv('MAX_POSITIONS', '5'))))
    KLINE_INTERVAL = os.getenv('KLINE_INTERVAL', '15m')
    BINANCE_FEE = 0.0005  # 0.05% maker/taker fee on futures, x2 for open/close
    
    # Technical Indicators Parameters
    RSI_PERIOD = int(os.getenv('RSI_PERIOD', '14'))
    RSI_OVERSOLD = float(os.getenv('RSI_OVERSOLD', '30'))
    RSI_OVERBOUGHT = float(os.getenv('RSI_OVERBOUGHT', '70'))
    
    BB_PERIOD = int(os.getenv('BB_PERIOD', '20'))
    BB_STD = float(os.getenv('BB_STD', '2.0'))
    
    MACD_FAST = int(os.getenv('MACD_FAST', '12'))
    MACD_SLOW = int(os.getenv('MACD_SLOW', '26'))
    MACD_SIGNAL = int(os.getenv('MACD_SIGNAL', '9'))
    
    EMA_SHORT = int(os.getenv('EMA_SHORT', '50'))
    EMA_LONG = int(os.getenv('EMA_LONG', '200'))
    
    # Volume and Market Filters
    VOLUME_THRESHOLD = float(os.getenv('VOLUME_THRESHOLD', '1.5'))
    
    # Notification Settings
    NOTIFICATION_SERVICES = os.getenv('APPRISE_SERVICES', '').split(',') if os.getenv('APPRISE_SERVICES') else []
    NOTIFY_ON_TRADES = os.getenv('NOTIFY_ON_TRADES', 'true').lower() == 'true'
    NOTIFY_ON_ERRORS = os.getenv('NOTIFY_ON_ERRORS', 'true').lower() == 'true'
    NOTIFY_ON_STARTUP = os.getenv('NOTIFY_ON_STARTUP', 'true').lower() == 'true'
    NOTIFY_ON_BALANCE_LOW = os.getenv('NOTIFY_ON_BALANCE_LOW', 'true').lower() == 'true'
    TIMEZONE = os.getenv('TIMEZONE', 'UTC')  # Default to UTC, can be set to 'UTC+3' or similar
    
    # Security Settings
    MIN_API_INTERVAL = 0.1
    MAX_CONSECUTIVE_ERRORS = 10
    MIN_BALANCE = 10.0
    
    # Debug Settings
    DEBUG_MODE = os.getenv('DEBUG_MODE', 'true').lower() == 'true'
    FORCE_TRADES = os.getenv('FORCE_TRADES', 'false').lower() == 'true'
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration parameters"""
        if not cls.API_KEY or not cls.SECRET_KEY:
            raise ValueError("API credentials not found. Set BINANCE_API_KEY and BINANCE_SECRET_KEY environment variables")
        
        # Valid Binance intervals
        valid_intervals = ['1s', '1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
        
        validations = [
            (0 < cls.MIN_SIGNAL_STRENGTH <= 5, "MIN_SIGNAL_STRENGTH must be between 1 and 5"),
            (0 < cls.MIN_BACKTEST_SCORE <= 100, "MIN_BACKTEST_SCORE must be between 0 and 100"),
            (0 < cls.MAX_POSITION_SIZE_PCT <= 10, "MAX_POSITION_SIZE_PCT must be between 0 and 10"),
            (0 < cls.VOLUME_THRESHOLD <= 10, "VOLUME_THRESHOLD must be between 0 and 10"),
            (0 < cls.STOP_LOSS < 0.1, "STOP_LOSS must be between 0 and 0.1"),
            (0 < cls.TAKE_PROFIT < 0.2, "TAKE_PROFIT must be between 0 and 0.2"),
            (cls.KLINE_INTERVAL in valid_intervals, f"KLINE_INTERVAL must be one of: {', '.join(valid_intervals)}")
        ]
        
        for condition, message in validations:
            if not condition:
                raise ValueError(f"Configuration error: {message}")
        
        return True

# Strategy configuration
STRATEGY_CONFIG = {
    'use_multiple_indicators': True,
    'min_signal_strength': TradingConfig.MIN_SIGNAL_STRENGTH,
    'volume_threshold': TradingConfig.VOLUME_THRESHOLD,
    'volatility_filter': True,
    'trend_filter': True,
    'backtesting_enabled': TradingConfig.ENABLE_BACKTESTING,
    'min_backtest_score': TradingConfig.MIN_BACKTEST_SCORE,
    'strategy_combinations': TradingConfig.ACTIVE_STRATEGIES
}

# Validate configuration on import
TradingConfig.validate_config()
