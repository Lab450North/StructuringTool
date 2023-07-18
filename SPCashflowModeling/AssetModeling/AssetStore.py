from Utils.SPCFUtils import SPCFUtils



ASSETSTORE = {}

ASSETSTORE['consumerLoan70'] = SPCFUtils.convertToDict(
    
    assetType = "Amortization",
    notional = 1e9, term = 70,intRate = 0.20,\
    totalDefault = 0.1798,
    defaultTimingCurve = SPCFUtils.timingCurveParse("25/25/25/12", term = 70),
    cprVector = SPCFUtils.convertIntexRamp("7", term = 70, divisor = 100),
    sevVector = SPCFUtils.convertIntexRamp("92", term = 70, divisor = 100),
    dqVector = SPCFUtils.convertIntexRamp("0 ramp 10 7", term = 70, divisor = 100),
    servicingFeesRatio = 0.005)

ASSETSTORE['consumerLoan45'] = SPCFUtils.convertToDict(
    
    assetType = "Amortization",
    notional = 1e9, term = 45,intRate = 0.20,\
    totalDefault = 0.1798,
    defaultTimingCurve = SPCFUtils.timingCurveParse("20/20/20", term = 45),
    cdrVector = None,
    cprVector = SPCFUtils.convertIntexRamp("7", term = 45, divisor = 100),
    sevVector = SPCFUtils.convertIntexRamp("92", term = 45, divisor = 100),
    dqVector = SPCFUtils.convertIntexRamp("0 ramp 10 7", term = 45, divisor = 100),
    servicingFeesRatio = 0.005)

ASSETSTORE['autoLoan45'] = SPCFUtils.convertToDict(assetType = "Amortization",
    notional = 1e9, term = 45,intRate = 0.18,\
    totalDefault = 0.11,
    defaultTimingCurve = SPCFUtils.timingCurveParse("20/20/20", term = 45),
    cdrVector = None,
    cprVector = SPCFUtils.convertIntexRamp("7", term = 45, divisor = 100),
    sevVector = SPCFUtils.convertIntexRamp("60", term = 45, divisor = 100),
    dqVector = SPCFUtils.convertIntexRamp("0 ramp 10 13", term = 45, divisor = 100),
    servicingFeesRatio = 0.005)



ASSETSTORE['consumerLoan58'] = SPCFUtils.convertToDict(
    
    assetType = "Amortization",
    notional = 1e9, term = 58,intRate = 0.1922,\
    totalDefault = 0.18,
    defaultTimingCurve = SPCFUtils.timingCurveParse("40/35/12", term = 58),
    cdrVector = None,
    cprVector = SPCFUtils.convertIntexRamp("7", term = 58, divisor = 100),
    sevVector = SPCFUtils.convertIntexRamp("92", term = 58, divisor = 100),
    dqVector = SPCFUtils.convertIntexRamp("0 ramp 6 7", term = 58, divisor = 100),
    servicingFeesRatio = 0.005)
