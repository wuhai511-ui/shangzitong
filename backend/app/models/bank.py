"""Bank dictionary model — common Chinese banks for card selection."""
from sqlalchemy import Column, Integer, String
from .base import Base


class Bank(Base):
    """Bank dictionary table, populated once at startup."""
    __tablename__ = "banks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(32), unique=True, nullable=False)
    code = Column(String(16), nullable=True)
    sort_order = Column(Integer, default=0)


# Common Chinese banks for seeding
DEFAULT_BANKS = [
    ("中国工商银行", "ICBC"),
    ("中国农业银行", "ABC"),
    ("中国银行", "BOC"),
    ("中国建设银行", "CCB"),
    ("交通银行", "BOCOM"),
    ("招商银行", "CMB"),
    ("中信银行", "CITIC"),
    ("中国光大银行", "CEB"),
    ("华夏银行", "HXB"),
    ("中国民生银行", "CMBC"),
    ("广发银行", "CGB"),
    ("平安银行", "PAB"),
    ("兴业银行", "CIB"),
    ("浦发银行", "SPDB"),
    ("中国邮政储蓄银行", "PSBC"),
    ("北京银行", "BOB"),
    ("上海银行", "BOS"),
    ("江苏银行", "JSB"),
    ("南京银行", "NJCB"),
    ("宁波银行", "NBCB"),
    ("杭州银行", "HZB"),
    ("浙商银行", "CZB"),
    ("渤海银行", "CBHB"),
    ("恒丰银行", "HFB"),
    ("上海农商银行", "SRCB"),
    ("北京农商银行", "BRCB"),
    ("广州农商银行", "GRCB"),
    ("深圳农商银行", "SZRCB"),
]
