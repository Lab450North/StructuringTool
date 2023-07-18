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
        advRate = kwargs.get("advRate")
        coupon = kwargs.get("coupon")
        if (advRate is not None) and (coupon is not None):
            data = [{'debtName': k, 'advRate': advRate[k], 'coupon': coupon[k]} for k in advRate]
            self.capitalStructure = pd.DataFrame(data)
        else:
            self.capitalStructure = pd.DataFrame(columns = ["debtName", "advRate", "debtCoupon"])
    
    def addJuniorDebt(self, debtName, advRate, debtCoupon):
        self.capitalStructure.loc[len(self.capitalStructure)] = [debtName, advRate, debtCoupon]
        
    def removeJuniorDebt(self):
        if len(self.capitalStructure) > 0:
            self.capitalStructure.drop(self.capitalStructure.tail(1).index, inplace = True)
     
    def getCapitalStructure(self):
        return self.capitalStructure

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
        if self.checkAdvRate:
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

class Trigger:
    def __init__(self) -> None:
        pass