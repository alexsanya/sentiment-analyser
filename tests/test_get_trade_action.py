"""Unit tests for get_trade_action function in sentiment_analyzer module."""

import pytest
from typing import Optional

from src.core.sentiment_analyzer import get_trade_action
from src.models.schemas import TradeAction, TradeActionParams


class TestGetTradeAction:
    """Test cases for get_trade_action function."""

    def test_score_below_threshold_returns_none(self):
        """Test that scores below 6 return None."""
        # Test various scores below threshold
        assert get_trade_action(0) is None
        assert get_trade_action(1) is None
        assert get_trade_action(2) is None
        assert get_trade_action(3) is None
        assert get_trade_action(4) is None
        assert get_trade_action(5) is None

    def test_score_none_returns_none(self):
        """Test that None score returns None."""
        assert get_trade_action(None) is None

    def test_negative_score_returns_none(self):
        """Test that negative scores return None."""
        assert get_trade_action(-1) is None
        assert get_trade_action(-10) is None

    def test_moderate_trading_score_6(self):
        """Test moderate trading parameters for score 6."""
        result = get_trade_action(6)
        
        assert result is not None
        assert isinstance(result, TradeAction)
        assert result.action == "trade"
        
        params = result.params
        assert params.pair == "ETHUSDT"
        assert params.side == "long"
        assert params.leverage == 5
        assert params.margin_usd == 300
        assert params.take_profit_percent == 70
        assert params.stop_loss_percent == 12

    def test_moderate_trading_score_7(self):
        """Test moderate trading parameters for score 7."""
        result = get_trade_action(7)
        
        assert result is not None
        assert isinstance(result, TradeAction)
        assert result.action == "trade"
        
        params = result.params
        assert params.pair == "ETHUSDT"
        assert params.side == "long"
        assert params.leverage == 5
        assert params.margin_usd == 300
        assert params.take_profit_percent == 70
        assert params.stop_loss_percent == 12

    def test_aggressive_trading_score_8(self):
        """Test aggressive trading parameters for score 8."""
        result = get_trade_action(8)
        
        assert result is not None
        assert isinstance(result, TradeAction)
        assert result.action == "trade"
        
        params = result.params
        assert params.pair == "ETHUSDT"
        assert params.side == "long"
        assert params.leverage == 7
        assert params.margin_usd == 500
        assert params.take_profit_percent == 120
        assert params.stop_loss_percent == 12

    def test_aggressive_trading_score_9(self):
        """Test aggressive trading parameters for score 9."""
        result = get_trade_action(9)
        
        assert result is not None
        assert isinstance(result, TradeAction)
        assert result.action == "trade"
        
        params = result.params
        assert params.pair == "ETHUSDT"
        assert params.side == "long"
        assert params.leverage == 7
        assert params.margin_usd == 500
        assert params.take_profit_percent == 120
        assert params.stop_loss_percent == 12

    def test_aggressive_trading_score_10(self):
        """Test aggressive trading parameters for score 10."""
        result = get_trade_action(10)
        
        assert result is not None
        assert isinstance(result, TradeAction)
        assert result.action == "trade"
        
        params = result.params
        assert params.pair == "ETHUSDT"
        assert params.side == "long"
        assert params.leverage == 7
        assert params.margin_usd == 500
        assert params.take_profit_percent == 120
        assert params.stop_loss_percent == 12

    def test_high_score_above_10(self):
        """Test that scores above 10 still use aggressive parameters."""
        result = get_trade_action(15)
        
        assert result is not None
        assert isinstance(result, TradeAction)
        assert result.action == "trade"
        
        params = result.params
        assert params.leverage == 7
        assert params.margin_usd == 500
        assert params.take_profit_percent == 120
        assert params.stop_loss_percent == 12

    @pytest.mark.parametrize("score,expected_leverage,expected_margin", [
        (6, 5, 300),
        (7, 5, 300),
        (8, 7, 500),
        (9, 7, 500),
        (10, 7, 500),
    ])
    def test_score_threshold_boundaries(self, score: int, expected_leverage: int, expected_margin: int):
        """Test that score boundaries produce correct leverage and margin values."""
        result = get_trade_action(score)
        
        assert result is not None
        assert result.params.leverage == expected_leverage
        assert result.params.margin_usd == expected_margin

    @pytest.mark.parametrize("score", [0, 1, 2, 3, 4, 5, -1, -10])
    def test_no_action_scores(self, score: int):
        """Test that various low/negative scores return None."""
        assert get_trade_action(score) is None

    @pytest.mark.parametrize("score", [6, 7, 8, 9, 10, 11, 100])
    def test_action_created_scores(self, score: int):
        """Test that actionable scores return TradeAction objects."""
        result = get_trade_action(score)
        
        assert result is not None
        assert isinstance(result, TradeAction)
        assert result.action == "trade"
        assert isinstance(result.params, TradeActionParams)

    def test_common_parameters_consistency(self):
        """Test that common parameters are consistent across all actionable scores."""
        moderate_result = get_trade_action(6)
        aggressive_result = get_trade_action(8)
        
        # Both should have same common parameters
        assert moderate_result.params.pair == aggressive_result.params.pair == "ETHUSDT"
        assert moderate_result.params.side == aggressive_result.params.side == "long"
        assert moderate_result.params.stop_loss_percent == aggressive_result.params.stop_loss_percent == 12
        
        # But different leverage and margin
        assert moderate_result.params.leverage != aggressive_result.params.leverage
        assert moderate_result.params.margin_usd != aggressive_result.params.margin_usd
        assert moderate_result.params.take_profit_percent != aggressive_result.params.take_profit_percent

    def test_return_type_annotations(self):
        """Test that function returns correct types according to annotations."""
        # Should return None for low scores
        result_none = get_trade_action(3)
        assert result_none is None
        
        # Should return TradeAction for high scores
        result_action = get_trade_action(8)
        assert isinstance(result_action, TradeAction)

    def test_trade_action_structure(self):
        """Test that returned TradeAction has correct structure."""
        result = get_trade_action(7)
        
        assert result is not None
        assert hasattr(result, 'action')
        assert hasattr(result, 'params')
        assert result.action == "trade"
        
        params = result.params
        assert hasattr(params, 'pair')
        assert hasattr(params, 'side')
        assert hasattr(params, 'leverage')
        assert hasattr(params, 'margin_usd')
        assert hasattr(params, 'take_profit_percent')
        assert hasattr(params, 'stop_loss_percent')
        
        # All parameters should be set (not None)
        assert params.pair is not None
        assert params.side is not None
        assert params.leverage is not None
        assert params.margin_usd is not None
        assert params.take_profit_percent is not None
        assert params.stop_loss_percent is not None


class TestGetTradeActionEdgeCases:
    """Test edge cases and error conditions for get_trade_action function."""

    def test_boundary_score_5_vs_6(self):
        """Test the critical boundary between no action (5) and action (6)."""
        assert get_trade_action(5) is None
        assert get_trade_action(6) is not None

    def test_boundary_score_7_vs_8(self):
        """Test the boundary between moderate (7) and aggressive (8) trading."""
        moderate = get_trade_action(7)
        aggressive = get_trade_action(8)
        
        assert moderate is not None
        assert aggressive is not None
        
        # Different leverage and margin
        assert moderate.params.leverage == 5
        assert aggressive.params.leverage == 7
        assert moderate.params.margin_usd == 300
        assert aggressive.params.margin_usd == 500

    def test_score_type_safety(self):
        """Test that function handles different numeric types correctly."""
        # Test with float that should be treated as int
        result_float = get_trade_action(8.0)
        result_int = get_trade_action(8)
        
        assert result_float is not None
        assert result_int is not None
        assert result_float.params.leverage == result_int.params.leverage

    def test_extreme_values(self):
        """Test function behavior with extreme score values."""
        # Very high positive score
        result_high = get_trade_action(1000)
        assert result_high is not None
        assert result_high.params.leverage == 7  # Should use aggressive parameters
        
        # Very low negative score
        result_low = get_trade_action(-1000)
        assert result_low is None