import pandas as pd
import numpy_financial as npf
from functools import reduce
from AssetModeling.AssetRamper import AssetRamper
from Utils.SPCFUtils import SPCFUtils

class Asset:
    def __new__(cls, **kwargs):
        assetType = kwargs.get("assetType")
        if cls is Asset:
            if assetType.lower() == "amortization":
                # to avoid circular import, import module here
                from AssetModeling.AmortizationAsset import AmortizationAsset
                return super(Asset, cls).__new__(AmortizationAsset)
        return super(Asset, cls).__new__(cls)

    def __init__(self, **kwargs):
        self.assumptionSet = kwargs
        self.rampSchedule = AssetRamper()
        
    def addRampSchedule(self, rampSchedule, px, clear = False):
        if clear:
            self.rampSchedule.clearAllAsset()

        rampNotional, rampPx = (SPCFUtils.rampSchdule(rampSchedule, px)[key] for key in ('rampNotional', 'px'))
        for notional, px in zip(rampNotional, rampPx):
            cashflow = self.buildCashflow(notional, px)
            self.rampSchedule.appendAsset(notional, px, cashflow)
        self.rampCashflow = self.getRampCashflow()
        self.rampAssetStats = self._buildRampStats()
    
    def getRampCashflow(self):
        res = self.rampSchedule.aggregateCashflows()
        return res[["period", 'periodYears'] + self.dollarColumns]
        
    def getAssumptions(self):
        return self.assumptionSet
                   
    def getStaticMetrics(self, ramp=False):
        dataSoure = self.rampAssetStats if ramp else self.assetStats
            
        df = pd.DataFrame([dataSoure["metrics"]]).T

        df = df.reset_index()
        df.columns = ["matrics", "value"]
        return df

    def getDynamicMetrics(self, metrics, ramp = False):
        dataSoure = self.rampAssetStats if ramp else self.assetStats
        metrics = metrics if isinstance(metrics, list) else [metrics]
        for metric in metrics:
            if metric not in dataSoure["ts_metrics"]:
                print(f"metrics {metric} not found")
                return None
        df = [dataSoure["ts_metrics"][k] for k in metrics]
        df = reduce(lambda left,right: pd.merge(left,right,on='period', how='outer'), df)
        return df        

    def calculateYield(self, px):
        calcdf = self.cashflow[["period", "totalCF"]]
        calcdf.loc[calcdf["period"] == 0, "totalCF"] = -1 * self.notional * px / 100.0
        calcirr = npf.irr(calcdf["totalCF"].values) * 12

        return calcirr

    def calculateYieldTable(self, pxList):
        yieldList = [self.calculateYield(px) for px in pxList]
        return pd.DataFrame({"px": pxList, "yield": yieldList})