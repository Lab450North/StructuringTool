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


ASSETSTORE['subprimeAutoFlagship2303'] = SPCFUtils.convertToDict(    
    assetType = "Amortization",
    notional = 1e9, term = 69,intRate = 0.2073,\
    cdrVector = SPCFUtils.convertIntexRamp("0 ramp 8 10", term = 69, divisor = 100),
    cprVector = SPCFUtils.convertIntexRamp("8", term = 69, divisor = 100),
    sevVector = SPCFUtils.convertIntexRamp("100 95 90 60", term = 69, divisor = 100),
    dqVector = SPCFUtils.convertIntexRamp("0 ramp 12 14", term = 69, divisor = 100),
    servicingFeesRatio = 0.005)


ASSETSTORE['consumerLoanMarlette2303'] = SPCFUtils.convertToDict(    
    assetType = "Amortization",
    notional = 1e9, term = 50,intRate = 0.1593,\
    cdrVector = SPCFUtils.convertIntexRamp("0 ramp 8 9", term = 50, divisor = 100),
    cprVector = SPCFUtils.convertIntexRamp("7", term = 50, divisor = 100),
    sevVector = SPCFUtils.convertIntexRamp("100 95 92", term = 50, divisor = 100),
    dqVector = SPCFUtils.convertIntexRamp("0 ramp 16 6", term = 50, divisor = 100),
    servicingFeesRatio = 0.005)

test = 1