from Utils.SPCFUtils import SPCFUtils
from AssetModeling.Asset import Asset
from StructureModeling.Structure import Structure
from functools import reduce
import numpy as np
import pandas as pd

class DealManager:
    def __init__(self, **kwargs):
        self.dealName = kwargs.get("dealName")
        self.dealDescriptive = kwargs.get("dealDescriptive")
        self.dealFees = kwargs.get("dealFees")

        self.assetScenarios = {}
        self.unleveredContainer = {}
        self.leveredContainer = {}
        self.statusTracking = pd.DataFrame(columns = ["unleveredLoad", "ramp", "leveredLoad"])

        self.setRampSchedule(kwargs.get("rampSchedule"))
        self.financingTerms = kwargs.get("financingTerms")

        assetScenarios = kwargs.get("assetScenarios")
        for k, v in assetScenarios.items():
            self.addAssetScenario(k,v)

    def getCapitalStack(self):
        if "base" not in self.assetScenarios:
            print("Base scenario not found.")
            return None

        capitalStack = self.leveredContainer["base"].getCapitalStructure()
        additionalMetrics = ["WAL", "Paywindow"]

        capitalStack = capitalStack.append(pd.DataFrame(columns = additionalMetrics))        
        temp = self.leveredContainer["base"].getStaticMetrics()
                
        for _class in capitalStack.loc[:, "class"]:
            for _metric in additionalMetrics:
                classMetric = f"{_class}_{_metric}"
                capitalStack.loc[capitalStack["class"] == _class, _metric] = temp.loc[temp['matrics']==classMetric, "value"].values[0]
                
        return capitalStack
    

    def getDealIdentity(self):
        return {"dealName": self.dealName,
                "dealDescriptive": self.dealDescriptive,
                "dealFees": self.dealFees,
                "rampSchedule": self.rampSchedule,
                "assetScenarios": self.assetScenarios,
                "financingTerms": self.financingTerms
                }

    def copyAssetWithNewAssumption(self, copyScenario, newScenario, editAssumption):
        copyAssumption = self.assetScenarios[copyScenario]
        newAssumption = SPCFUtils.copyChangeAssumption(copyAssumption, editAssumption)
        self.addAssetScenario(newScenario, newAssumption) 
           
    def addAssetScenario(self, scenarioName, assetAssumption):
        if scenarioName in self.assetScenarios:
            return None
        self.assetScenarios[scenarioName] = assetAssumption
        self.statusTracking.loc[scenarioName] = ['', '', '']
        
        self.loadUnlevered(scenarioName)
        self.rampAsset(scenarioName)
        self.loadLevered(scenarioName)
        self.checkAssetData()

        return True

    def addSeriesDefaultScenario(self, startingMultiple, endingMultiple, step):
        if "base" not in self.assetScenarios:
            print("Base scenario not found.")
            return None
        
        baseCGL = self.unleveredContainer["base"].assetStats["metrics"]["cgl"]
        for multiple in np.arange(startingMultiple, endingMultiple + step, step):
            self.copyAssetWithNewAssumption("base", f"base_{multiple}x", 
                                            {"totalDefault": baseCGL * multiple,
                                             "cdrCurve": None
                                             })
            
    
    def removeScenario(self, scenarioName):
        
        if isinstance(scenarioName, list):
            for item in scenarioName:
                self.removeScenario(item)
            return True
        
        self.assetScenarios.pop(scenarioName, None)
        self.unleveredContainer.pop(scenarioName, None)
        self.leveredContainer.pop(scenarioName, None)
        self.statusTracking.drop(scenarioName, inplace = True)

        return True

    def setRampSchedule(self, rampSchedule):
        if rampSchedule is None:
            print("No ramp schedule found. 100mm @ 100px provided")
            self.rampSchedule = {"ramp": "100", "px": 100}
        else:
            self.rampSchedule = rampSchedule

    def rampAsset(self, scenario):
        if scenario in self.assetScenarios:
            self.unleveredContainer[scenario].addRampSchedule(self.rampSchedule["ramp"], self.rampSchedule["px"], clear = True)
            self.statusTracking.loc[scenario, "ramp"] = self.rampSchedule["ramp"] + " @ " + str(self.rampSchedule["px"])
        else:
            print("scenario not found")

    def rampAllAsset(self):
        for k, v in self.assetScenarios.items():
            self.rampAsset(k)

    def setRamp(self, rampSchedule):
        self.setRampSchedule(rampSchedule)
        self.rampAllAsset()
        self.loadAllLevered()

    def setFinancingTerms(self, financingTerms):
        self.financingTerms = financingTerms
        self.loadAllLevered()
        
    def loadUnlevered(self, scenarioName):
        if scenarioName in self.assetScenarios:
            self.unleveredContainer[scenarioName] = Asset(**self.assetScenarios[scenarioName])
            self.statusTracking.loc[scenarioName, "unleveredLoad"] = True
        else:
            print("scenario not found")

    def loadAllUnlevered(self):
        self.unleveredContainer = {}
        for k, v in self.assetScenarios.items():
            self.loadUnlevered(k)

    def loadLevered(self, scenarioName):
        
        if self.financingTerms is None:
            print("no financing terms found")
            return None

        if scenarioName in self.assetScenarios:
            self.leveredContainer[scenarioName] = Structure(self.unleveredContainer[scenarioName].rampCashflow, **self.financingTerms)
            self.statusTracking.loc[scenarioName, "leveredLoad"] = True
        else:
            print("scenario not found")

    def loadAllLevered(self):
        self.leveredContainer = {}
        for k, v in self.assetScenarios.items():
            self.loadLevered(k)

    def getStructureStaticMetrics(self):
        df = [v.getStaticMetrics().rename(columns = {"value":k, "matrics":"matrics/px"}) for k, v in self.leveredContainer.items()]
        df = reduce(lambda left,right: pd.merge(left,right,on='matrics/px', how='outer'), df)
        
        return df

    def getAssetStaticMetrics(self, pxList = [100], ramp = False):
        df = [v.getStaticMetrics(ramp).rename(columns = {"value":k, "matrics":"matrics/px"}) for k, v in self.unleveredContainer.items()]
        df = reduce(lambda left,right: pd.merge(left,right,on='matrics/px', how='outer'), df)
        
        if ramp == False:
            dfYT = [v.calculateYieldTable(pxList).rename(columns = {"yield":k, "px":"matrics/px"}) for k, v in self.unleveredContainer.items()]
            dfYT = reduce(lambda left,right: pd.merge(left,right,on='matrics/px', how='outer'), dfYT)
            df = pd.concat([df, dfYT], axis = 0, ignore_index=True)
        
        return df

    def getAssetDynamicMetrics(self, metrics):
        returnNewDf = lambda x, newName: x.rename(columns = {x.columns[1]: newName})
        df = [returnNewDf(v.getDynamicMetrics(metrics), k) for k, v in self.unleveredContainer.items()]
        df = reduce(lambda left,right: pd.merge(left,right,on='period', how='outer'), df)
        return df


    def checkAssetData(self):
        if "base" not in [k.lower() for k in list(self.assetScenarios.keys())]:
            print("base scenario not found")
            return False
                
        data = [(scenarioName, assumptionSet['assetType']) for scenarioName, assumptionSet in self.assetScenarios.items()]
        df = pd.DataFrame(data, columns=['scenario', 'assetType'])
                
        if df['assetType'].str.lower().nunique() > 1:
            print("more than one asset type found", '*' * 50, '\n', df)
            return False

        self.scenarioCount = len(self.assetScenarios)
        return True
    
    