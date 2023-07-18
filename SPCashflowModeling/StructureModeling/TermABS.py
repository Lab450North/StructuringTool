from StructureModeling.Structure import Structure
import StructureModeling.StructureComponent as StructureComponent
from Utils.SPCFUtils import SPCFUtils

import pandas as pd
import numpy as np
import itertools
import os, sys; sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

class TermABS(Structure):
    def __init__(self, collateralRampCF, **kwargs):
        super().__init__(collateralRampCF, **kwargs)
        self.collateralRampCF = collateralRampCF
        self.dealNotional = self.collateralRampCF.loc[0, "eopBal"]
        self.readFinancingTerms()
        self.runCalcSteps()
    
    def calcCollatMetrics(self):
        self.collateralRampCF.loc[:, "dqVector"] = self.collateralRampCF.loc[:, "dqBal"] / self.collateralRampCF.loc[:, "bopBal"]
        self.collateralRampCF.loc[:, "cnl"] = self.collateralRampCF.loc[:, "cumulativeLossPrin"] / self.dealNotional

    def enrichABSTerms(self):
        self.capTable = StructureComponent.CapitalStructure(advRate = self.advRate, coupon = self.coupon)
        self.capTable.effectiveCapitalStructure()
        self.periodicFeesDetail = StructureComponent.PeriodicFee(self.periodicFees)
        

    def SetDealCashflowDF(self):
        self.DealCashflow = self.collateralRampCF.copy().set_index(
            "period"
        )

        # Asset Related Columns
        self.DealCashflow.columns = pd.MultiIndex.from_product(
            [["Asset"], self.DealCashflow.columns]
        )

        for k,v in DEALCOLUMNS.items():
            if k == "Debt":
                cols = list(itertools.product(self.capTable.effectiveClass, v))
            else:
                cols = list(itertools.product([k], v))            
            self.DealCashflow[cols] = np.nan

        dfLen = self.DealCashflow.shape[0]

        self.DealCashflow[('AMTriggerTest', "DelinquencyTrigger")] = SPCFUtils.leadZeroCleanEnd(dfLen, self.amTrigger["delinquency"])
        self.DealCashflow[('AMTriggerTest', "CNLTrigger")] = SPCFUtils.leadZeroCleanEnd(dfLen, self.amTrigger["cnl"])
        

        # subset of useful quick reference columns
        self.debtBopColumns = [
            col
            for col in self.DealCashflow.columns
            if ("bop" in col[1]) & (col[0] != "Asset")
        ]

        self.debtEopColumns = [
            (col[0], col[1].replace("bop", "eop")) for col in self.debtBopColumns
        ]

        self.feesColumns = list(itertools.product(["Fees"], DEALCOLUMNS['Fees']))
        
    def buildCashflow(self):

        # loop through period to calculate periodic cashflow
        eodBreached = False

        for i, row in self.DealCashflow.iterrows():
            availCashCF = {}

            if i == 0:
                # initial status balance
                row[self.debtBopColumns] = 0                
                row[self.debtEopColumns] = row[("Asset", "eopBal")] * np.array(list(self.capTable.capitalStructure['thickness'])) / 100.0
                
            else:
                # set bop balance
                row[self.debtBopColumns] = np.array(
                    self.DealCashflow.loc[i - 1, self.debtEopColumns]
                )
            
            # available cash = asset cashflow + reserve account
            availcash = row[("Asset", "totalCF")] + \
                self.DealCashflow.loc[i - 1, ('ReserveAccount', 'rsvBal')] if i > 0 else 0
            row[("AvailCash", "fromAsset")] = availcash


            # *********************** periodic fees ***********************
            # note that closing transaction fees (which would impact residual economics) is not handeled
            if i >0:
                for feeIdx, feeRow in self.periodicFeesDetail.fees.iterrows():
                    if feeRow['isRatio']:
                        row[("Fees", feeRow['feeName'])] = row[("Asset", "bopBal")] * feeRow['feeAmount'] / 12.0
                    else:
                        row[("Fees", feeRow['feeName'])] = feeRow['feeAmount']
                feesDue = sum(row[self.feesColumns])
            else:
                feesDue = 0

            
            availcash = availcash - feesDue

            row[("AvailCash", "afterFees")] = availcash


            # *********************** Debt Coupon ***********************

            row[self.capTable.classColumnsGroup("couponDue")] = (
                np.array(row[self.capTable.classColumnsGroup("bopBal")])
                * np.array(self.capTable.capitalStructure["coupon"])
                / 12.0
            )

            for _class in self.capTable.effectiveClass:

                # pay coupon
                row[(_class, "couponPaid")] = min(availcash, row[(_class, "couponDue")])

                row[(_class, "couponShortfall")] = (
                    row[(_class, "couponDue")] - row[(_class, "couponPaid")]
                )
                availcash = availcash - row[(_class, "couponPaid")]
            

            row[("AvailCash", "afterDebtCoupon")] = availcash


            # *********************** AM and EOD Test ***********************
            # check EOD Trigger Test
            if self.eodTrigger['couponShortfall']:
                eodBreached = eodBreached | (row[self.capTable.classColumnsGroup("couponShortfall")].sum() > 0)
            
            row[("EODTriggerTest", "couponShortFallBreached")] = eodBreached
            row[("EODTriggerTest", "EODBreached")] = row[("EODTriggerTest", "couponShortFallBreached")]
            
            
            # check AM Trigger Test
            row[("AMTriggerTest", "DelinquencyActual")] = row[("Asset", "dqVector")]
            row[("AMTriggerTest", "DelinquencyBreached")] = True if (i>0) & (row[("AMTriggerTest", "DelinquencyActual")] >= row[("AMTriggerTest", "DelinquencyTrigger")]) else False
            
            row[("AMTriggerTest", "CNLActual")] = row[("Asset", "cnl")]
            row[("AMTriggerTest", "CNLBreached")] = True if (i>0) & (row[("AMTriggerTest", "CNLActual")] >= row[("AMTriggerTest", "CNLTrigger")]) else False
            
            # assumpion: if eodBreached, then AMBreached
            row[("AMTriggerTest", "AMBreached")] = row[("AMTriggerTest", "DelinquencyBreached")] | row[("AMTriggerTest", "CNLBreached")] | eodBreached
            
            
            # *********************** Replenish Reserve Account ***********************
            if row[("AMTriggerTest", "AMBreached")]:
                requiredReplenish = 0
            else:
                requiredReplenish = self.reserveAccount['percent'] * self.dealNotional
            
            row[('ReserveAccount', 'rsvBal')] = min(availcash, requiredReplenish)
            availcash = availcash - row[('ReserveAccount', 'rsvBal')]
            row[("AvailCash", "afterReserveAccount")] = availcash
            

            # *********************** Debt Principal ***********************
            
            # calculate OC
            row[("CreditEnhancement", "targetOCPct")] = 1.00 if row[("AMTriggerTest", "AMBreached")] else (self.creditEnhancement["targetOC"] / 100.0)
            row[("CreditEnhancement", "targetOCDollar")] = row[("CreditEnhancement", "targetOCPct")] * row[("Asset", "eopBal")]
            row[("CreditEnhancement", "minOCDollar")] = self.creditEnhancement["OCFloor"] * self.dealNotional
            row[("CreditEnhancement", "targetOC")] = max(row[("CreditEnhancement", "minOCDollar")], row[("CreditEnhancement", "targetOCDollar")])

            requirePaydown = max(0, row[("CreditEnhancement", "targetOC")] - (row[("Asset", "eopBal")] - row[self.debtBopColumns].sum()))
            
            distributionToDebt = min(availcash, requirePaydown)
            paidToDebt = 0
            
            
            for _class in self.capTable.effectiveClass:
                row[(_class, "principalPaid")] = min(
                    distributionToDebt, row[(_class, "bopBal")]
                )

                distributionToDebt = distributionToDebt - row[(_class, "principalPaid")]
                paidToDebt += row[(_class, "principalPaid")]

            availcash = availcash - paidToDebt
            row[("AvailCash", "afterDebtPrin")] = availcash

            # calculate eop balance of debt
            if i > 0:
                row[self.capTable.classColumnsGroup("eopBal")] = (
                    np.array(row[self.capTable.classColumnsGroup("bopBal")])
                    - np.array(row[self.capTable.classColumnsGroup("principalPaid")])
                    + np.array(row[self.capTable.classColumnsGroup("couponShortfall")])
                )
            for _class in self.capTable.effectiveClass:
                if row[(_class, "eopBal")] < 0.5:
                    row[(_class, "eopBal")] = 0

            # *********************** Residual Cashflow ***********************
            if i == 0:
                row[("Residual", "cashInvestment")] = -row[("Asset", "purchaseCash")] + row[self.debtEopColumns].sum()
            else:
                row[("Residual", "cashInvestment")] = 0

            row[("Residual", "repaymentCash")] = availcash

            availcash = availcash - row[("Residual", "repaymentCash")]
            row[("AvailCash", "afterResidual")] = availcash
            

            row[("Residual", "investmentCF")] = (
                row[("Residual", "cashInvestment")] + row[("Residual", "repaymentCash")]
            )

            self.DealCashflow.loc[i] = row

        return self

    def buildAnalysis(self):
        super().buildAnalysis()
        

    def buildStats(self):
        super().buildStats()


# ************************************************************************************************************************

DEALCOLUMNS = {}
DEALCOLUMNS['Debt'] = [
                    "bopBal",
                    "couponDue",
                    "couponPaid",
                    "couponShortfall",
                    "principalPaid",
                    "eopBal",
                ]

DEALCOLUMNS['Fees'] = ['trustee',
                       'servicing']

DEALCOLUMNS['ReserveAccount'] = ['rsvBal']

DEALCOLUMNS['CreditEnhancement'] = [
                    "targetOCPct",
                    "targetOCDollar",
                    "minOCDollar",
                    "targetOC",
                    "actualOC",
                    "actualOCPct"
                ]

DEALCOLUMNS['AMTriggerTest'] = [
                    "DelinquencyTrigger",
                    "DelinquencyActual",
                    "DelinquencyBreached",
                    "CNLTrigger",
                    "CNLActual",
                    "CNLBreached",
                    "AMBreached",
                ]

DEALCOLUMNS['EODTriggerTest'] = [
                    "couponShortFallBreached",
                    "EODBreached",
                ]

DEALCOLUMNS['Residual'] = ["cashInvestment", "repaymentCash", "investmentCF"]
DEALCOLUMNS['AvailCash'] = [
                "fromAsset",
                "afterFees",
                "afterDebtCoupon",
                "afterDebtPrin",
                "afterResidual",
            ]