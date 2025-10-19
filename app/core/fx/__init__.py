"""
FX forward curve module
"""
from .forwards import (
    FXQuote,
    FXForwardCurve,
    load_fx_quotes,
    build_fx_forward_curve,
    get_fx_forward_rate,
    get_fx_spot_rate,
    create_usd_eur_fx_curve
)

__all__ = [
    "FXQuote",
    "FXForwardCurve",
    "load_fx_quotes",
    "build_fx_forward_curve",
    "get_fx_forward_rate",
    "get_fx_spot_rate",
    "create_usd_eur_fx_curve"
]

