import pandas as pd
from functools import reduce

def printStarryString(_str):
    length = len(_str)
    star_row = '*' * (length + 20)
    padded_string = '******     ' + _str + '      ******'
    print("\n")
    print(star_row)
    print(padded_string)
    print(star_row)


class DealAnalytics:
    def __init__(self, deal):
        self.deal = deal
    
    def presentDeal(self):
        printStarryString("Capital Stack")
        print(self.getCapitalStack())
        printStarryString("Asset Economics (single one without ramp)")
        print(self.getAssetStaticMetrics(pxList = range(100, 89, -5)).set_index("matrics/px"))
        printStarryString("Ramped Asset Unlevered Stats")
        print(self.getAssetStaticMetrics(ramp = True).set_index("matrics/px"))
        printStarryString("Structure / Levered Economics")
        print(self.getStructureStaticMetrics().set_index("matrics/px"))

    def getStructureStaticMetrics(self):
        df = [v.getStaticMetrics().rename(columns = {"value":k, "matrics":"matrics/px"}) for k, v in self.deal.leveredContainer.items()]
        df = reduce(lambda left,right: pd.merge(left,right,on='matrics/px', how='outer'), df)
        
        return df

    def getStructureDynamicMetrics(self, metrics):
        resDict = {}
        for k, v in self.deal.leveredContainer.items():
            resDict[k] = v.getDynamicMetrics(metrics)
        return resDict

    def getAssetStaticMetrics(self, pxList = [100], ramp = False):
        df = [v.asset.getStaticMetrics(ramp).rename(columns = {"value":k, "matrics":"matrics/px"}) for k, v in self.deal.leveredContainer.items()]
        df = reduce(lambda left,right: pd.merge(left,right,on='matrics/px', how='outer'), df)
        
        if ramp == False:
            dfYT = [v.asset.calculateYieldTable(pxList).rename(columns = {"yield":k, "px":"matrics/px"}) for k, v in self.deal.leveredContainer.items()]
            dfYT = reduce(lambda left,right: pd.merge(left,right,on='matrics/px', how='outer'), dfYT)
            df = pd.concat([df, dfYT], axis = 0, ignore_index=True)
        
        return df

    def getAssetDynamicMetrics(self, metrics):
        returnNewDf = lambda x, newName: x.rename(columns = {x.columns[1]: newName})
        df = [returnNewDf(v.asset.getDynamicMetrics(metrics), k) for k, v in self.deal.leveredContainer.items()]
        df = reduce(lambda left,right: pd.merge(left,right,on='period', how='outer'), df)
        return df
    
    def getCapitalStack(self):
        return self.deal.leveredContainer["base"].getCapitalStack()
        
        