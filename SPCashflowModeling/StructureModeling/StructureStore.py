from Utils.SPCFUtils import SPCFUtils

STRUCTURESTORE = {}

STRUCTURESTORE['PT'] = {
    "structureType":"TermABS",
    "advRate": {"A": 0},
    "coupon": {"A": 0.0},
    "reserveAccount":{"percent": 0.000},
    "redemptionSchedule":{"collateralPct": 0.0},
    "creditEnhancement":{"targetOC": 0,"OCFloor": 0},
    "periodicFees": {"servicing": {"feeAmount": 0.025, "isRatio": True, "feeFreq": 12},
                     "trustee": {"feeAmount": 5000, "isRatio": False, "feeFreq": 12}
                     },
    "amTrigger":{"delinquency": SPCFUtils.convertIntexRamp("100", term = 1, divisor = 100.0, forceInt=False),
                 "cnl": SPCFUtils.convertIntexRamp("100", term = 1, divisor = 100.0, forceInt=False)
                                                   },
    "eodTrigger":{"couponShortfall":True},
    }

STRUCTURESTORE['ABCut'] = {
    "structureType":"TermABS",
    "advRate": {"A": 70},
    "coupon": {"A": 0.07},
    "reserveAccount":{"percent": 0.025},
    "redemptionSchedule":{"collateralPct": 0.1},
    "creditEnhancement":{"targetOC": 30,"OCFloor": 0.02},
    "periodicFees": {"servicing": {"feeAmount": 0.025, "isRatio": True, "feeFreq": 12},
                     "trustee": {"feeAmount": 5000, "isRatio": False, "feeFreq": 12}
                     },
    "amTrigger":{"delinquency": SPCFUtils.convertIntexRamp("100", term = 1, divisor = 100.0, forceInt=False),
                 "cnl": SPCFUtils.convertIntexRamp("100", term = 1, divisor = 100.0, forceInt=False)
                                                   },
    "eodTrigger":{"couponShortfall":True},
    }