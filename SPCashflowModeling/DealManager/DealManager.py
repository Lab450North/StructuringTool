from Utils.SPCFUtils import SPCFUtils
from AssetModeling.Asset import Asset
from StructureModeling.Structure import Structure
from StructureModeling.Storage import StructureStore
from functools import reduce
import numpy as np
import pandas as pd
import re

class DealManager:
    def __init__(self, **kwargs):
        self.dealName = kwargs.get("dealName")
        self.dealDescriptive = kwargs.get("dealDescriptive")
        self.dealFees = kwargs.get("dealFees")

        self.assetScenarios = {}
        self.leveredContainer = {}
        
        self.rampSchedule = kwargs.get("rampSchedule", {"ramp": "100", "px": 100})
        self.financingTerms = kwargs.get("financingTerms", StructureStore.STRUCTURESTORE['PTNoFees'])
        
        assetScenarios = kwargs.get("assetScenarios")
        for k, v in assetScenarios.items():
            self.addAssetScenario(k,v)
        
    def getCapitalStack(self):
        if "base" not in self.assetScenarios:
            print("Base scenario not found.")
            return None
                        
        return self.leveredContainer["base"].getCapitalStack()
    

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
        self.assetScenarios[scenarioName] = assetAssumption
        
        assetTemp = Asset(**self.assetScenarios[scenarioName])
        assetTemp.addRampSchedule(self.rampSchedule["ramp"], self.rampSchedule["px"], clear = True)

        self.leveredContainer[scenarioName] = Structure(
        assetTemp,
        **self.financingTerms
        )
        self.checkAssetData()

        return True

    def addSeriesDefaultScenario(self, startingMultiple, endingMultiple, step, baseScenario = "base"):
        if baseScenario not in self.assetScenarios:
            print(f"{baseScenario} scenario not found.")
            return None
        
        baseTotalDefault = self.leveredContainer[baseScenario].asset.assumptionSet.get('totalDefault')
        baseDefaultTiming = self.leveredContainer[baseScenario].asset.assumptionSet.get('defaultTimingCurve')
        baseCdrVector = self.leveredContainer[baseScenario].asset.assumptionSet.get('cdrVector')

        for multiple in np.arange(startingMultiple, endingMultiple + step, step):
            if (baseTotalDefault is not None) and (baseDefaultTiming is not None):
                self.copyAssetWithNewAssumption(baseScenario, f"{baseScenario}_{multiple}x", 
                                                {"totalDefault": baseTotalDefault * multiple,
                                                "cdrVector": None
                                                })
            else:
                self.copyAssetWithNewAssumption(baseScenario, f"{baseScenario}_{multiple}x", 
                                                {"totalDefault": None,
                                                 "defaultTimingCurve": None,
                                                "cdrVector": [min(item * multiple, 0.99999999999999) for item in baseCdrVector]
                                                })

    def removeMultipleScenario(self, scenarioName = "base"):
        pattern = re.compile(r'(?i)' + scenarioName + r'_\d+(\.\d+)?x')
        removedScenario = [k for k in self.assetScenarios if pattern.match(k)]
        
        for item in removedScenario:
            self.removeScenario(item)
        
        print(f"removed scenarios: {removedScenario}")

    def removeScenario(self, scenarioName):
        if isinstance(scenarioName, list):
            for item in scenarioName:
                self.removeScenario(item)
            return True
        
        self.assetScenarios.pop(scenarioName, None)
        self.leveredContainer.pop(scenarioName, None)
        self.checkAssetData()

        return True

    # def getStructureStaticMetrics(self):
    #     df = [v.getStaticMetrics().rename(columns = {"value":k, "matrics":"matrics/px"}) for k, v in self.leveredContainer.items()]
    #     df = reduce(lambda left,right: pd.merge(left,right,on='matrics/px', how='outer'), df)
        
    #     return df

    # def getStructureDynamicMetrics(self, metrics):
    #     resDict = {}
    #     for k, v in self.leveredContainer.items():
    #         resDict[k] = v.getDynamicMetrics(metrics)
    #     return resDict

    # def getAssetStaticMetrics(self, pxList = [100], ramp = False):
    #     df = [v.asset.getStaticMetrics(ramp).rename(columns = {"value":k, "matrics":"matrics/px"}) for k, v in self.leveredContainer.items()]
    #     df = reduce(lambda left,right: pd.merge(left,right,on='matrics/px', how='outer'), df)
        
    #     if ramp == False:
    #         dfYT = [v.asset.calculateYieldTable(pxList).rename(columns = {"yield":k, "px":"matrics/px"}) for k, v in self.leveredContainer.items()]
    #         dfYT = reduce(lambda left,right: pd.merge(left,right,on='matrics/px', how='outer'), dfYT)
    #         df = pd.concat([df, dfYT], axis = 0, ignore_index=True)
        
    #     return df

    # def getAssetDynamicMetrics(self, metrics):
    #     returnNewDf = lambda x, newName: x.rename(columns = {x.columns[1]: newName})
    #     df = [returnNewDf(v.asset.getDynamicMetrics(metrics), k) for k, v in self.leveredContainer.items()]
    #     df = reduce(lambda left,right: pd.merge(left,right,on='period', how='outer'), df)
    #     return df


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
    
    def getScenarioCount(self):
        return self.scenarioCount
    
    def getScenarioNames(self):
        return list(self.assetScenarios.keys())