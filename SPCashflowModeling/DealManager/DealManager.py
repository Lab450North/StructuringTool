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
        self.dealMisc = kwargs.get("dealMisc")

        self.assetScenarios = {}
        self.leveredContainer = {}
        
        self.rampSchedule = kwargs.get("rampSchedule", {"ramp": "100", "px": 100})
        self.financingTerms = kwargs.get("financingTerms", StructureStore.STRUCTURESTORE['PTNoFees'])
        
        assetScenarios = kwargs.get("assetScenarios")
        for k, v in assetScenarios.items():
            self.addAssetScenario(k,v)

    def __repr__(self):
        return f'''DealManager(dealName = "{self.dealName}",
    dealDescriptive = {self.dealDescriptive},
    dealMisc = {self.dealMisc},
    rampSchedule = {self.rampSchedule},
    assetScenarios = {self.assetScenarios},
    financingTerms = {self.financingTerms}
    )'''

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