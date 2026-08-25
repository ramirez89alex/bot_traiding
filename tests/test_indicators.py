import pandas as pd

from src.indicators import atr, rsi, sma


def test_sma_basic():
    series = pd.Series([1, 2, 3, 4, 5])
    result = sma(series, window=3)
    assert result.iloc[2] == 2.0
    assert result.iloc[4] == 4.0
    assert pd.isna(result.iloc[0])


def test_rsi_all_gains_is_100():
    series = pd.Series(range(1, 30))
    result = rsi(series, period=14)
    assert result.iloc[-1] == 100


def test_rsi_all_losses_is_0():
    series = pd.Series(range(30, 1, -1))
    result = rsi(series, period=14)
    assert result.iloc[-1] < 5


def test_atr_positive_on_volatile_data():
    df = pd.DataFrame(
        {
            "high": [10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24],
            "low": [9, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22],
            "close": [9.5, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23],
        }
    )
    result = atr(df, period=14)
    assert result.iloc[-1] > 0
