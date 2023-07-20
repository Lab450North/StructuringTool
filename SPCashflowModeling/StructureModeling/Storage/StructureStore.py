from Utils.SPCFUtils import SPCFUtils

STRUCTURESTORE = {}

STRUCTURESTORE['PTNoFees'] = {
    "structureType":"TermABS",
    "advRate": {"A": 0},
    "coupon": {"A": 0.0},
    "reserveAccount":{"percent": 0.000},
    "redemptionSchedule":{"collateralPct": 0.0},
    "creditEnhancement":{"targetOC": 0,"OCFloor": 0},
    "periodicFees": {"servicing": {"feeAmount": 0.000, "isRatio": True, "feeFreq": 12},
                     "trustee": {"feeAmount": 0, "isRatio": False, "feeFreq": 12}
                     },
    "amTrigger":{"delinquency": SPCFUtils.convertIntexRamp("100", term = 1, divisor = 100.0, forceInt=False),
                 "cnl": SPCFUtils.convertIntexRamp("100", term = 1, divisor = 100.0, forceInt=False)
                                                   },
    "eodTrigger":{"couponShortfall":True},
    }


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

STRUCTURESTORE['ConsumerABS'] = {
    "structureType":"TermABS",
    "advRate": {"A": 53.3, "B": 66.75, "C": 85},
    "coupon": {"A": 0.0677, "B": 0.0792, "C": 0.1187},
    "reserveAccount":{"percent": 0.0050},
    "redemptionSchedule":{"collateralPct": 0.1},
    "creditEnhancement":{"targetOC": 18.5,"OCFloor": 0.02},
    "periodicFees": {"servicing": {"feeAmount": 0.025, "isRatio": True, "feeFreq": 12},
                     "trustee": {"feeAmount": 5000, "isRatio": False, "feeFreq": 12}
                     },
    "amTrigger":{"delinquency": SPCFUtils.convertIntexRamp("100", term = 1, divisor = 100.0, forceInt=False),
                 "cnl": SPCFUtils.convertIntexRamp("3 for 3 4 for 2 8.5 for 3 12.5 for 3 15.65 for 3 18.15 for 3 19.3 for 3 20.5 for 3 20.9 for 3 21.65 for 3 25", term = 56, divisor = 100.0, forceInt=False)
                                                   },
    "eodTrigger":{"couponShortfall":True},
    }


STRUCTURESTORE['WH'] = {
    "structureType":"warehouse",
    "advRate": {"Snr": 70, "Mezz": 85},
    "coupon": {"Snr": 0.07, "Mezz": 0.13},
    "undrawnFee": {"Snr": 0.001, "Mezz": 0.002},
    "commitPeriod": {"Snr": 2, "Mezz": 2},
    "facilitySize": {"Snr": 1e8, "Mezz": 3e7},
    "periodicFees": {"trustee": {"feeAmount": 0.0025, "isRatio": True, "feeFreq": 12},
                     "verificationAgent": {"feeAmount": 0.0025, "isRatio": True, "feeFreq": 12},
                     "backupServicer": {"feeAmount": 0.0025, "isRatio": True, "feeFreq": 12},
                     "trusteeFixed": {"feeAmount": 500, "isRatio": False, "feeFreq": 12},
                     },
    "amTrigger":{"rolling3mDQ": SPCFUtils.convertIntexRamp("100", term = 1, divisor = 100.0, forceInt=False)}    
}
