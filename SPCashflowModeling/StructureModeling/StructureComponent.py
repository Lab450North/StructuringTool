import pandas as pd
import numpy as np
import itertools

class PeriodicFee:
    def __init__(self, feesDict):
        # check if feesDict is a dictionary
        if not isinstance(feesDict, dict):
            print("feesDict should be a dictionary")
            self.fees = pd.DataFrame(columns = ["feeName", "feeAmount", "isRatio", "feeFreq"])
        else:
            self.fees = pd.DataFrame(columns = ["feeName", "feeAmount", "isRatio", "feeFreq"])
            for k, v in feesDict.items():
                self.fees.loc[len(self.fees)] = [k, v["feeAmount"], v["isRatio"], v["feeFreq"]]

class CapitalStructure:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

        if self.allVariablesDefined():
            data = [{'debtName': k, **{var: getattr(self, var)[k] for var in self.variablesToCheck()}} for k in getattr(self, 'advRate')]
            self.capitalStructure = pd.DataFrame(data)
        else:
            self.capitalStructure = pd.DataFrame(columns = ["debtName"] + self.variablesToCheck())
        self.effectiveCapitalStructure()


    def getTerm(self, debtName, feature):
        return self.capitalStructure[self.capitalStructure['debtName'] == debtName][feature].values[0]

    def getCapitalStructure(self):
        return self.capitalStructure

    def allVariablesDefined(self):
        return all(getattr(self, var, None) is not None for var in self.variablesToCheck())

    def variablesToCheck(self):
        return []

    def checkAdvRate(self):
        if len(self.capitalStructure) == 0:
            return True
        if self.capitalStructure.advRate.max() > 100:
            print("advRate should be less than 100")
            return False
        
        temp = self.capitalStructure.advRate.shift(-1) - self.capitalStructure.advRate
        if temp.min() < 0:
            print("junior debt advRate should be higher than senior")
            return False
        return True

    def effectiveCapitalStructure(self):
        if self.checkAdvRate():
            temp = self.capitalStructure[(self.capitalStructure['advRate'].shift(1) < self.capitalStructure['advRate'])]
            self.capitalStructure = pd.concat([self.capitalStructure.head(1), temp], axis = 0)
            self.capitalStructure = self.capitalStructure.reset_index(drop = True)
            self.capitalStructure.loc[:, "thickness"] = self.capitalStructure['advRate'] - self.capitalStructure['advRate'].shift(1)
            self.capitalStructure.loc[0, "thickness"] = self.capitalStructure.loc[0, "advRate"]
            self.effectiveClass = self.capitalStructure['debtName'].tolist()
            self.classColumnsGroup = lambda x: list(itertools.product(self.effectiveClass, [x]))

        else:
            print("advRate check failed")
            return None

class TermCapitalStructure(CapitalStructure):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    def variablesToCheck(self):
        return ['advRate', 'coupon']
        
class RevolvingCapitalStructure(CapitalStructure):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
                
    def variablesToCheck(self):
        return ['advRate', 'coupon', "undrawnFee", "commitPeriod", "facilitySize"]

class Trigger:
    def __init__(self) -> None:
        pass