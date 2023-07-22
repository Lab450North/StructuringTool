import pandas as pd
from functools import reduce
import matplotlib.pyplot as plt
from tabulate import tabulate

def tabulatePrint(x):
    print(tabulate(x, headers='keys', tablefmt='psql'))

def printStarryString(_str):
    length = len(_str)
    star_row = '*' * (length + 20)
    padded_string = '******     ' + _str
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

    def getAssetDynamicMetrics(self, metrics, ramp = False):
        returnNewDf = lambda x, newName: x.rename(columns = {x.columns[1]: newName})
        df = [returnNewDf(v.asset.getDynamicMetrics(metrics, ramp), k) for k, v in self.deal.leveredContainer.items()]
        df = reduce(lambda left,right: pd.merge(left,right,on='period', how='outer'), df)
        return df

    def getCapitalStack(self):
        return self.deal.leveredContainer["base"].getCapitalStack()


    def plotStructureCurves(self):
        # structured deal performance curve
        metrics = ['balances', 'effectiveAdv', 'totalCF','CNLTest','CEBuild']
        fig, ax = plt.subplots(5,self.deal.getScenarioCount(), figsize=(20,15), sharex=True)
        
        for i, metric in enumerate(metrics):
            for j, scenario in enumerate(self.deal.getScenarioNames()):
                df = self.getStructureDynamicMetrics(metric)[scenario]
                title_i_j = scenario+"_"+metric
                if metric in ['balances', 'totalCF']:
                    df.loc[:, ["Asset"]].plot(ax = ax[i,j], grid = True, title = title_i_j, color = "black")
                    df.drop("Asset", axis = 1).plot.area(ax = ax[i,j], stacked = True, grid = True, title = title_i_j)
                else:
                    df.plot(ax = ax[i,j], grid = True, title = title_i_j)

                ax[i,j].set_xlabel("")
                ax[i,j].legend(fontsize="6")

        plt.tight_layout();plt.show()
    
    def plotCollateralCurves(self):
        # typical performance curve of amortization asset
        metrics = ['cdrCurve','cprCurve','dqCurve', 'factorCurve', 'cnlCurve', 'ltlCurve']
        fig, ax = plt.subplots(2,3, figsize=(10,8))
        ax = ax.flatten()
        for i, metric in enumerate(metrics):
            self.getAssetDynamicMetrics(metric, ramp = False).plot(x = "period", ax = ax[i], grid = True, title=metric)

        plt.tight_layout();plt.show()
    
    def plotRampCurves(self):
        # ramped asset performance curve
        metrics = ['periodicNetCF','cumulativeCF','portfolioBalance']
        fig, ax = plt.subplots(1,3, figsize=(10,4))
        ax = ax.flatten()
        for i, metric in enumerate(metrics):
            df = self.getAssetDynamicMetrics(metrics = metric, ramp = True)

            if metric == "periodicNetCF":
                df.plot.area(x = "period", ax = ax[i], grid = True, title=metric, stacked = False)
            else:
                df.plot(x = "period", ax = ax[i], grid = True, title=metric)

        plt.tight_layout();plt.show()

    



