"""
Setup script for ICT Trading Bot
"""

from setuptools import setup, find_packages

setup(
    name="ict-trading-bot",
    version="1.0.0",
    description="ICT Trading Bot for NQ Futures - Inner Circle Trader Strategy Implementation",
    author="JackK0125",
    packages=find_packages(),
    package_dir={'': 'ict_trading_bot/src'},
    install_requires=[
        'pandas>=2.0.0',
        'numpy>=1.24.0',
        'yfinance>=0.2.28',
        'python-dateutil>=2.8.2',
        'pytz>=2023.3',
        'matplotlib>=3.7.0',
        'seaborn>=0.12.0',
        'pyyaml>=6.0',
    ],
    python_requires='>=3.8',
    entry_points={
        'console_scripts': [
            'ict-bot=bot:main',
        ],
    },
)
