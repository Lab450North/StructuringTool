from Utils.SPCFUtils import SPCFUtils



ASSETSTORE = {}



ASSETSTORE['consumerLoanUpstart2302'] = SPCFUtils.convertToDict(    
    assetType = "Amortization",
    notional = 1e9, term = 56,intRate = 0.2175,\
    totalDefault = 0.2038,
    defaultTimingCurve = SPCFUtils.convertIntexRamp("0.64 ramp 9 5.1 4.91 ramp 8 2.65 2.37 ramp 36 0.05", term = 56, divisor = 100),
    cprVector = SPCFUtils.convertIntexRamp("7", term = 56, divisor = 100),
    sevVector = SPCFUtils.convertIntexRamp("92", term = 56, divisor = 100),
    dqVector = SPCFUtils.convertIntexRamp("0 ramp 8 8", term = 56, divisor = 100),
    servicingFeesRatio = 0.005)
