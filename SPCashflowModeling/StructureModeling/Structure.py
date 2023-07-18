import pandas as pd
import numpy as np
import numpy_financial as npf
from functools import reduce

class Structure:
    def __new__(cls, collateralRampCF, **kwargs):
        structureType = kwargs.get("structureType")
        if cls is Structure:
            if structureType.lower() == "termabs":
                # to avoid circular import, import module here
                from StructureModeling.TermABS import TermABS
                return super(Structure, cls).__new__(TermABS)
        return super(Structure, cls).__new__(cls)

    def __init__(self, collateralRampCF, **kwargs):
        self.financingTerms = kwargs

    def getFinancingTerms(self):
        return self.financingTerms

    def runCalcSteps(self):
        self.calcCollatMetrics()
        self.enrichABSTerms()

        self.SetDealCashflowDF()
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

    def getCapitalStructure(self):
        df = pd.DataFrame(columns = ["class", "size", "coupon", "advRate"])
        for _class in self.capTable.effectiveClass:
            df.loc[len(df)] = [_class, self.StructureStats["metrics"][f"{_class}_Size"], self.StructureStats["metrics"][f"{_class}_Coupon"], self.StructureStats["metrics"][f"{_class}_OrigAdv"]]
        
        return df
    
    def buildAnalysis(self):
        self.DealCashflow[("Fees", "feesCollected")] = self.DealCashflow[
            self.feesColumns
        ].sum(axis=1)
        
        self.DealCashflow[("Asset", "investmentCashDeductFees")] = (
            -self.DealCashflow[("Asset", "purchaseCash")]
            + self.DealCashflow[("Asset", "totalCF")]
            - self.DealCashflow[("Fees", "feesCollected")]
        )

        self.DealCashflow[("CreditEnhancement", "actualOC")] = self.DealCashflow[("Asset", "eopBal")] - self.DealCashflow[self.debtEopColumns].sum(axis = 1)
        self.DealCashflow[("CreditEnhancement", "actualOCPct")] = self.DealCashflow[("CreditEnhancement", "actualOC")]/self.DealCashflow[("Asset", "eopBal")]
        

        self.DealCashflow[self.capTable.classColumnsGroup("effectiveAdvRate")] = (
            np.array(self.DealCashflow[self.capTable.classColumnsGroup("eopBal")])
            / np.expand_dims(np.array(self.DealCashflow[("Asset", "eopBal")]), 1)
        ).cumsum(axis=1)

        self.DealCashflow[self.capTable.classColumnsGroup("debtCostDollar")] = np.array(
            (self.DealCashflow[self.capTable.classColumnsGroup("couponPaid")]))
        
        for _class in self.capTable.effectiveClass:
            self.DealCashflow[(_class, "totalCF")] = self.DealCashflow[(_class, "couponPaid")] + self.DealCashflow[(_class, "principalPaid")]

        self.DealCashflow[("CreditEnhancement", "ExcessSpread")] = \
            (self.DealCashflow[("Asset", "netIntCF")] - self.DealCashflow[("Fees", "servicing")]) / self.DealCashflow[("Asset", "bopBal")] - \
                np.array(self.DealCashflow[self.capTable.classColumnsGroup("couponDue")].sum(axis=1)) / np.array(self.DealCashflow[self.capTable.classColumnsGroup("bopBal")].sum(axis=1))

        self.DealCashflow[("CreditEnhancement", "ExcessSpread")] = self.DealCashflow[("CreditEnhancement", "ExcessSpread")] * 12

        self.combineDebt("eopBal")
        self.combineDebt("debtCostDollar")

        self.DealCashflow[("Debt", "effectiveDebtCost")] = (
            np.array(self.DealCashflow[("Debt", "debtCostDollar")])
            / np.array(
                self.DealCashflow[self.capTable.classColumnsGroup("bopBal")].sum(axis=1)
            )
            * 12.0
        )

    def buildStats(self):
        self.StructureStats = {"metrics": {}, "ts_metrics": {}, "filteredMetrics": {}}
        
        # ts_metrics
        
        self.StructureStats["ts_metrics"]["balances"] = self.DealCashflow[
            [("Asset", "eopBal")] + self.capTable.classColumnsGroup("eopBal")
        ]

        self.StructureStats["ts_metrics"]["effectiveAdv"] = self.DealCashflow[
            self.capTable.classColumnsGroup("effectiveAdvRate")
        ]
        
        self.StructureStats["ts_metrics"]["totalCF"] = self.DealCashflow[
            [("Asset", "totalCF")] + self.capTable.classColumnsGroup("totalCF") + [("Residual", "repaymentCash")]
        ]

        self.StructureStats["ts_metrics"]["CNLTest"] = self.DealCashflow[
            [("AMTriggerTest", "CNLTrigger")] + [("AMTriggerTest", "CNLActual")]+ [("AMTriggerTest", "CNLBreached")]
        ]
        
        self.StructureStats["ts_metrics"]["CEBuild"] = self.DealCashflow[
            [("CreditEnhancement", "targetOCPct")] + [("CreditEnhancement", "actualOCPct")]
        ]

        self.StructureStats["ts_metrics"]["ExcessSpread"] = self.DealCashflow[
            [("CreditEnhancement", "ExcessSpread")]
        ]
        
        self.StructureStats["ts_metrics"]["cashCheck"] = self.DealCashflow[('Asset','totalCF')] + \
            self.DealCashflow[('ReserveAccount','rsvBal')].shift(1) \
                - self.DealCashflow[("Fees", "feesCollected")] \
                    - self.DealCashflow[self.capTable.classColumnsGroup("couponPaid")].sum(axis=1) \
                        - self.DealCashflow[('ReserveAccount','rsvBal')] \
                            - self.DealCashflow[self.capTable.classColumnsGroup("principalPaid")].sum(axis=1) \
                                -self.DealCashflow[("Residual", "repaymentCash")]
        

        # metrics
        
        self.StructureStats["metrics"]["debtCost"] = self.DealCashflow[("Debt", "debtCostDollar")].sum() / self.DealCashflow[("Debt", "eopBal")].sum() * 12
        
        self.StructureStats["metrics"]["effectiveAdvRate"] = self.DealCashflow[("Debt", "eopBal")].sum()/ self.DealCashflow[("Asset", "eopBal")].sum() * 100
        
        self.StructureStats["metrics"]["cnl"]  = self.DealCashflow[("Asset", "cnl")].max()

        self.StructureStats["metrics"]["lossTiming"] = self.DealCashflow.groupby(("Asset","periodYears"))[[("Asset", "lossPrin")]].sum() / self.DealCashflow[("Asset","lossPrin")].sum(axis = 0)
        
        self.StructureStats["metrics"]["lossTiming"] = "/".join(map(lambda x: f'{x[0]:.0f}', self.StructureStats["metrics"]["lossTiming"].iloc[1:].values * 100))


        self.StructureStats["metrics"]["defaultTiming"] = self.DealCashflow.groupby(("Asset","periodYears"))[[("Asset", "lossPrin")]].sum() / self.DealCashflow[("Asset","lossPrin")].sum(axis = 0)
        
        self.StructureStats["metrics"]["defaultTiming"] = "/".join(map(lambda x: f'{x[0]:.0f}', self.StructureStats["metrics"]["defaultTiming"].iloc[1:].values * 100))        

        for _class in self.capTable.effectiveClass:
            self.StructureStats["metrics"][f"{_class}_remainingBalance"] = self.DealCashflow[(_class, 'eopBal')].tail(1).values[0]
            self.StructureStats["metrics"][f"{_class}_remainingFactor"] = self.StructureStats["metrics"][f"{_class}_remainingBalance"] / self.DealCashflow[(_class, 'eopBal')].head(1).values[0]
            self.StructureStats["metrics"][f"{_class}_WAL"] = (self.DealCashflow[(_class, "principalPaid")] * self.DealCashflow.index).sum()/self.DealCashflow[(_class, "principalPaid")].sum() / 12.0
            self.StructureStats["metrics"][f"{_class}_Size"] = self.DealCashflow[(_class, 'eopBal')].head(1).values[0]
            self.StructureStats["metrics"][f"{_class}_Coupon"] = self.coupon[_class]
            self.StructureStats["metrics"][f"{_class}_OrigAdv"] = self.advRate[_class]
            if len(self.DealCashflow[self.DealCashflow[(_class, 'principalPaid')]>0]) > 0:
                self.StructureStats["metrics"][f"{_class}_Paywindow"] = str(self.DealCashflow[self.DealCashflow[(_class, 'principalPaid')]>0].head(1).index.values[0]) \
                    + " - " \
                        + str(self.DealCashflow[self.DealCashflow[(_class, 'principalPaid')]>0].tail(1).index.values[0])
            else:
                self.StructureStats["metrics"][f"{_class}_Paywindow"] = "0 - 0"
        
        self.StructureStats["metrics"]["residual_yield"] =  npf.irr(self.DealCashflow[("Residual", "investmentCF")].values) * 12

        # filtered metrics
        for k in ['debtCost', 'effectiveAdvRate','cnl',"defaultTiming", "lossTiming"]:
            self.StructureStats["filteredMetrics"].update({k:self.StructureStats["metrics"][k]})
        
        for k in ["remainingFactor", "WAL", "Paywindow"]:
            for _class in self.capTable.effectiveClass:
                classK = f"{_class}_{k}"
                self.StructureStats["filteredMetrics"].update({classK:self.StructureStats["metrics"][classK]})
        
        self.StructureStats["filteredMetrics"]['residual_yield'] = self.StructureStats["metrics"]['residual_yield']