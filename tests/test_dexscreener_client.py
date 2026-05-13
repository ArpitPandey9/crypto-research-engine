import pytest

from src.data.dexscreener_client import (
    DexScreenerError,
    DexPoolDepth,
    fetch_deepest_pool_depth,
    fetch_token_pairs,
    select_deepest_usd_pool,
)


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_fetch_token_pairs_uses_real_dexscreener_token_pairs_endpoint():
    captured = {}

    def fake_get(url, timeout):
        captured["url"] = url
        captured["timeout"] = timeout
        return FakeResponse(
            200,
            [
                {
                    "chainId": "ethereum",
                    "dexId": "uniswap",
                    "pairAddress": "0xpair",
                    "baseToken": {"symbol": "WETH"},
                    "quoteToken": {"symbol": "USDC"},
                    "priceUsd": "3000",
                    "liquidity": {"usd": 1_000_000, "base": 100, "quote": 700_000},
                    "volume": {"h24": 50_000},
                    "url": "https://dexscreener.com/ethereum/0xpair",
                }
            ],
        )

    pairs = fetch_token_pairs("ETH", http_get=fake_get)

    assert len(pairs) == 1
    assert captured["timeout"] == 10
    assert "https://api.dexscreener.com/token-pairs/v1/ethereum/" in captured["url"]
    assert "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2" in captured["url"]


def test_fetch_token_pairs_rejects_unsupported_asset():
    with pytest.raises(ValueError, match="Unsupported asset_symbol"):
        fetch_token_pairs("DOGE", http_get=lambda url, timeout: FakeResponse(200, []))


def test_fetch_token_pairs_raises_on_bad_status_code():
    def fake_get(url, timeout):
        return FakeResponse(500, {"error": "server error"})

    with pytest.raises(DexScreenerError, match="DEX Screener request failed"):
        fetch_token_pairs("ETH", http_get=fake_get)


def test_fetch_token_pairs_raises_on_unexpected_payload_shape():
    def fake_get(url, timeout):
        return FakeResponse(200, {"pairs": []})

    with pytest.raises(DexScreenerError, match="Unexpected DEX Screener response"):
        fetch_token_pairs("ETH", http_get=fake_get)


def test_select_deepest_usd_pool_selects_highest_positive_liquidity():
    pairs = [
        {
            "chainId": "ethereum",
            "dexId": "small-dex",
            "pairAddress": "0xsmall",
            "baseToken": {"symbol": "WETH"},
            "quoteToken": {"symbol": "USDC"},
            "priceUsd": "3000",
            "liquidity": {"usd": 100_000, "base": 10, "quote": 70_000},
            "volume": {"h24": 5_000},
            "url": "https://dexscreener.com/ethereum/0xsmall",
        },
        {
            "chainId": "ethereum",
            "dexId": "deep-dex",
            "pairAddress": "0xdeep",
            "baseToken": {"symbol": "WETH"},
            "quoteToken": {"symbol": "USDC"},
            "priceUsd": "3001",
            "liquidity": {"usd": 5_000_000, "base": 900, "quote": 2_300_000},
            "volume": {"h24": 900_000},
            "url": "https://dexscreener.com/ethereum/0xdeep",
        },
    ]

    pool = select_deepest_usd_pool("ETH", pairs)

    assert isinstance(pool, DexPoolDepth)
    assert pool.asset_symbol == "ETH"
    assert pool.chain_id == "ethereum"
    assert pool.dex_id == "deep-dex"
    assert pool.pair_address == "0xdeep"
    assert pool.base_token_symbol == "WETH"
    assert pool.quote_token_symbol == "USDC"
    assert pool.price_usd == pytest.approx(3001)
    assert pool.liquidity_usd == pytest.approx(5_000_000)
    assert pool.liquidity_base == pytest.approx(900)
    assert pool.liquidity_quote == pytest.approx(2_300_000)
    assert pool.volume_h24 == pytest.approx(900_000)
    assert pool.pair_url == "https://dexscreener.com/ethereum/0xdeep"


def test_select_deepest_usd_pool_rejects_missing_positive_liquidity():
    pairs = [
        {"liquidity": {"usd": 0}},
        {"liquidity": {"usd": None}},
        {"liquidity": {}},
    ]

    with pytest.raises(DexScreenerError, match="No pair with positive liquidity.usd"):
        select_deepest_usd_pool("ETH", pairs)


def test_fetch_deepest_pool_depth_combines_fetch_and_selection():
    def fake_get(url, timeout):
        return FakeResponse(
            200,
            [
                {
                    "chainId": "ethereum",
                    "dexId": "uniswap",
                    "pairAddress": "0xpool",
                    "baseToken": {"symbol": "WBTC"},
                    "quoteToken": {"symbol": "USDC"},
                    "priceUsd": "80000",
                    "liquidity": {"usd": 10_000_000, "base": 50, "quote": 6_000_000},
                    "volume": {"h24": 1_000_000},
                    "url": "https://dexscreener.com/ethereum/0xpool",
                }
            ],
        )

    pool = fetch_deepest_pool_depth("WBTC", http_get=fake_get)

    assert pool.asset_symbol == "WBTC"
    assert pool.liquidity_usd == pytest.approx(10_000_000)
    assert pool.price_usd == pytest.approx(80_000)
