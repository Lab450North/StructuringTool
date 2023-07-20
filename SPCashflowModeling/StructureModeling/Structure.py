import pandas as pd
import numpy as np
import numpy_financial as npf
from functools import reduce

class Structure:
    def __new__(cls, asset, **kwargs):
        structureType = kwargs.get("structureType")
        if cls is Structure:

            if structureType.lower() == "termabs":
                # * to avoid circular import, import module here *
                from StructureModeling.TermABS import TermABS
                return super(Structure, cls).__new__(TermABS)

            elif structureType.lower() == "warehouse":
                from StructureModeling.Warehouse import Warehouse
                return super(Structure, cls).__new__(Warehouse)
                
        return super(Structure, cls).__new__(cls)

    def __init__(self, asset, **kwargs):
        self.financingTerms = kwargs

    def getFinancingTerms(self):
        return self.financingTerms

    def runCalcSteps(self):
        self.calcCollatMetrics()
        self.enrichFinancingTerms()

        self.setDealCashflowDF()
        self.buildCashflow()
        
        self.buildAnalysis()
        self.buildStats()
        return self
    
    def readFinancingTerms(self):
        for k, v in self.financingTerms.items():
            setattr(self, k, v)

    def combineDebt(self, x):
        self.DealCashflow[("Debt", x)] = self.DealCashflow[self.capTable.classColumnsGroup(x)].sum(axis=1)

    def getStaticMetrics(self):
        df = pd.DataFrame([self.StructureStats["filteredMetrics"]]).T

        df = df.reset_index()
        df.columns = ["matrics", "value"]
        return df

    def getDynamicMetrics(self, metrics):
        if metrics not in self.StructureStats["ts_metrics"]:
            print(f"metrics {metrics} not found")
            return None
        df = self.StructureStats["ts_metrics"][metrics]
        return df

    
    def getCapitalStack(self):
        pass
        
    def buildSpecificAnalysis(self):
        pass


    def buildAnalysis(self):

        # -calc- ******************* Fees ******************* 
        self.DealCashflow[("Fees", "feesCollected")] = self.DealCashflow[
            self.feesColumns
        ].sum(axis=1)
        
        # -calc- ******************* Asset ******************* 
        self.DealCashflow[("Asset", "investmentCashDeductFees")] = (
            -self.DealCashflow[("Asset", "purchaseCash")]
            + self.DealCashflow[("Asset", "totalCF")]
            - self.DealCashflow[("Fees", "feesCollected")]
        )

        # -calc- ******************* Credit Enhancement ******************* 
        self.DealCashflow[("CreditEnhancement", "actualOC")] = self.DealCashflow[("Asset", "eopBal")] - self.DealCashflow[self.debtEopColumns].sum(axis = 1)
        self.DealCashflow[("CreditEnhancement", "actualOCPct")] = self.DealCashflow[("CreditEnhancement", "actualOC")]/self.DealCashflow[("Asset", "eopBal")]
        
        self.DealCashflow[("CreditEnhancement", "ExcessSpread")] = \
            (self.DealCashflow[("Asset", "netIntCF")] - self.DealCashflow[("Fees", "feesCollected")]) / self.DealCashflow[("Asset", "bopBal")] - \
                np.array(self.DealCashflow[self.capTable.classColumnsGroup("couponDue")].sum(axis=1)) / np.array(self.DealCashflow[self.capTable.classColumnsGroup("bopBal")].sum(axis=1))

        self.DealCashflow[("CreditEnhancement", "ExcessSpread")] = self.DealCashflow[("CreditEnhancement", "ExcessSpread")] * 12

        # -calc- ******************* Rest of Calculation to Specific Structure ******************* 
        self.buildSpecificAnalysis()

    
    def buildSpecificStats(self):
        # spcific stats for each structure
        # select filtered metrics in each structure
        pass
    
    
    def buildStats(self):
        self.StructureStats = {"metrics": {}, "ts_metrics": {}, "filteredMetrics": {}}
        
        # -calc- ******************* ts metrics ******************* 
        
        self.StructureStats["ts_metrics"]["balances"] = self.DealCashflow[
            [("Asset", "eopBal")] + self.capTable.classColumnsGroup("eopBal")
        ]


        self.StructureStats["ts_metrics"]["cashDistribution"] = self.DealCashflow[
            [
                ("Asset", "totalCF"),
                ("Debt", "debtCF"),
                ("Residual", "repaymentCash"),
            ]
        ]

        self.StructureStats["ts_metrics"]["effectiveAdv"] = self.DealCashflow[
            self.capTable.classColumnsGroup("effectiveAdvRate")
        ]
        
        self.StructureStats["ts_metrics"]["totalCF"] = self.DealCashflow[
            [("Asset", "totalCF")] + self.capTable.classColumnsGroup("totalCF") + [("Residual", "repaymentCash")]
        ]

        self.StructureStats["ts_metrics"]["ExcessSpread"] = self.DealCashflow[
            [("CreditEnhancement", "ExcessSpread")]
        ]
        

        # -calc- ******************* metrics ******************* 
        
        self.StructureStats["metrics"]["assetTotalCashflow"] = self.DealCashflow[("Asset", "totalCF")].sum()
        
        self.StructureStats["metrics"]["debtCost"] = self.DealCashflow[("Debt", "debtCostDollar")].sum() / self.DealCashflow[("Debt", "eopBal")].sum() * 12
        
        self.StructureStats["metrics"]["effectiveAdvRate"] = self.DealCashflow[("Debt", "eopBal")].sum()/ self.DealCashflow[("Asset", "eopBal")].sum() * 100
        
        self.StructureStats['metrics']['feesCollected'] = self.DealCashflow[("Fees", "feesCollected")].sum()

        self.StructureStats["metrics"]["debtPrinCollected"] = self.DealCashflow[self.capTable.classColumnsGroup("principalPaid")].sum().sum()
        
        

        for _class in self.capTable.effectiveClass:
            self.StructureStats["metrics"][f"{_class}_coupon"] = self.coupon[_class]
            self.StructureStats["metrics"][f"{_class}_origAdv"] = self.advRate[_class]

            self.StructureStats["metrics"][f"{_class}_size"] = self.DealCashflow[(_class, 'eopBal')].head(1).values[0]
            self.StructureStats["metrics"][f"{_class}_remainingBalance"] = self.DealCashflow[(_class, 'eopBal')].tail(1).values[0]
            self.StructureStats["metrics"][f"{_class}_remainingFactor"] = self.StructureStats["metrics"][f"{_class}_remainingBalance"] / self.StructureStats["metrics"][f"{_class}_size"]
            self.StructureStats["metrics"][f"{_class}_wal"] = (self.DealCashflow[(_class, "principalPaid")] * self.DealCashflow.index).sum()/self.DealCashflow[(_class, "principalPaid")].sum() / 12.0
            
            if len(self.DealCashflow[self.DealCashflow[(_class, 'principalPaid')]>0]) > 0:
                self.StructureStats["metrics"][f"{_class}_paywindow"] = str(self.DealCashflow[self.DealCashflow[(_class, 'principalPaid')]>0].head(1).index.values[0]) \
                    + " - " \
                        + str(self.DealCashflow[self.DealCashflow[(_class, 'principalPaid')]>0].tail(1).index.values[0])
            else:
                self.StructureStats["metrics"][f"{_class}_paywindow"] = "0 - 0"
        
        self.StructureStats["metrics"]["residInvestmented"] = -1.0 * self.DealCashflow[("Residual", "cashInvestment")].sum()
        self.StructureStats["metrics"]["residYield"] =  npf.irr(self.DealCashflow[("Residual", "investmentCF")].values) * 12
        self.StructureStats["metrics"]["residMOIC"] = self.DealCashflow[("Residual", "repaymentCash")].sum() / self.StructureStats["metrics"]["residInvestmented"]


        # -calc- ******************* Rest of Calculation to Specific Structure ******************* 
        self.buildSpecificStats()