class PaymentProviderFactory:
    @classmethod
    def get(cls, provider: str, test_mode: bool = False):
        from .lkl_adapter import LKLAdapter
        from .huifu_adapter import HuifuAdapter
        from .mock_adapter import MockAdapter
        if test_mode:
            return MockAdapter()
        if provider == "lkl":
            return LKLAdapter()
        if provider == "huifu":
            return HuifuAdapter()
        raise ValueError(f"Unknown provider: {provider}")
