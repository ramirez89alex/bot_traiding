from src.risk import RiskManager


def test_position_size_leaves_room_for_fees_on_expensive_assets():
    """Con balance pequeño y un activo caro (ej. BTC ~90000), el tamaño de posición
    limitado por saldo debe dejar margen para la comisión: comprar el 100% del
    balance sin margen hace que costo = qty * precio * (1 + fee) supere el saldo
    y la orden se rechace siempre (bug reproducido con datos reales de Binance)."""
    risk_manager = RiskManager(risk_per_trade=0.01, atr_multiplier=2.0)
    balance = 1000.0
    entry_price = 90000.0
    atr = 300.0  # ATR grande relativo al risk_amount fuerza el tope por balance

    qty = risk_manager.position_size(balance, entry_price, atr)
    fee_rate = 0.001
    cost = qty * entry_price * (1 + fee_rate)

    assert qty > 0
    assert cost <= balance


def test_position_size_zero_when_atr_zero():
    risk_manager = RiskManager()
    assert risk_manager.position_size(1000.0, 90000.0, atr=0.0) == 0.0
