from dataclasses import dataclass, field
from datetime import date


@dataclass
class RiskManager:
    """Calcula tamaño de posición y aplica un límite de pérdida diaria.

    - El tamaño de posición se calcula para que, si el stop-loss (basado en ATR)
      se ejecuta, la pérdida sea aproximadamente `risk_per_trade` del balance.
    - `max_daily_loss` es un interruptor de seguridad: si se supera, el bot deja
      de abrir nuevas operaciones hasta el día siguiente.
    """

    risk_per_trade: float = 0.01
    max_daily_loss: float = 0.03
    atr_multiplier: float = 2.0
    reward_risk_ratio: float = 1.5
    fee_buffer: float = 0.002

    _current_day: date = field(default_factory=date.today, init=False, repr=False)
    _daily_pnl: float = field(default=0.0, init=False, repr=False)

    def position_size(self, balance: float, entry_price: float, atr: float) -> float:
        stop_distance = atr * self.atr_multiplier
        if stop_distance <= 0 or entry_price <= 0:
            return 0.0
        risk_amount = balance * self.risk_per_trade
        quantity = risk_amount / stop_distance
        # Deja margen para comisiones: si el tamaño se limita por saldo disponible
        # (activos caros como BTC frente a un balance pequeño), comprar el 100%
        # exacto del balance haría que el costo con comisión superara el saldo
        # y la orden se rechazara siempre.
        max_affordable = balance / (entry_price * (1 + self.fee_buffer))
        return max(0.0, min(quantity, max_affordable))

    def stop_loss_price(self, entry_price: float, atr: float, side: str = "long") -> float:
        distance = atr * self.atr_multiplier
        return entry_price - distance if side == "long" else entry_price + distance

    def take_profit_price(self, entry_price: float, atr: float, side: str = "long") -> float:
        distance = atr * self.atr_multiplier * self.reward_risk_ratio
        return entry_price + distance if side == "long" else entry_price - distance

    def register_trade_result(self, pnl: float, when: date | None = None) -> None:
        today = when or date.today()
        if today != self._current_day:
            self._current_day = today
            self._daily_pnl = 0.0
        self._daily_pnl += pnl

    def can_open_new_trade(self, balance: float) -> bool:
        loss_limit = -abs(self.max_daily_loss) * balance
        return self._daily_pnl > loss_limit

    @property
    def daily_pnl(self) -> float:
        return self._daily_pnl
