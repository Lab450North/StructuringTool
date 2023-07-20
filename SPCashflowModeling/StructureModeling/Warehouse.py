from StructureModeling.Structure import Structure
import StructureModeling.StructureComponent as StructureComponent
import numpy_financial as npf
import pandas as pd
import numpy as np
import itertools

# to be modeled
# exit (could be modeled on ramper level, instead of warehouse financing level)
# covenant breach


class Warehouse(Structure):
    def __init__(self, asset, **kwargs):
        super().__init__(asset, **kwargs)
        self.asset = asset
        self.readFinancingTerms()
        self.runCalcSteps()
        
    def calcCollatMetrics(self):
        self.asset.rampCashflow.loc[:, "dqVector"] = self.asset.rampCashflow.loc[:, "dqBal"] / self.asset.rampCashflow.loc[:, "bopBal"]
        self.asset.rampCashflow.loc[:, "cnl"] = self.asset.rampCashflow.loc[:, "cumulativeLossPrin"] / self.asset.rampCashflow.loc[:, "purchaseBalance"].cumsum().shift(1)

    def enrichFinancingTerms(self):
        self.capTable = StructureComponent.RevolvingCapitalStructure\
            (advRate = self.advRate,
             coupon = self.coupon,
             undrawnFee = self.undrawnFee,
             commitPeriod = self.commitPeriod,
             facilitySize = self.facilitySize
             )
        
        self.periodicFeesDetail = StructureComponent.PeriodicFee(self.periodicFees)

    def setDealCashflowDF(self):
        self.DealCashflow = self.asset.rampCashflow.copy().set_index(
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

        # loop through rampPeriod to calculate periodic cashflow
        for i, row in self.DealCashflow.iterrows():
            availcash = 0

            if i == 0:
                # set facility initial status
                row[self.debtBopColumns] = 0

            else:
                # set bop balance
                row[self.debtBopColumns] = np.array(
                    self.DealCashflow.loc[i - 1, self.debtEopColumns]
                )

            availcash = row[("Asset", "totalCF")]
            row[("AvailCash", "fromAsset")] = availcash

            # facility : adjusted balance
            row[("Facility", "adjAssetBal")] = np.maximum(
                0, np.array(row[("Asset", "eopBal")] - row[("Asset", "dqBal")])
            )


            # *********************** periodic fees ***********************
            if i >0:
                for feeIdx, feeRow in self.periodicFeesDetail.fees.iterrows():
                    if feeRow['isRatio']:
                        row[("Fees", feeRow['feeName'])] = row[("Asset", "bopBal")] * feeRow['feeAmount'] / 12.0
                    else:
                        row[("Fees", feeRow['feeName'])] = feeRow['feeAmount'] * (row[("Asset", "bopBal")] > 0)
                feesDue = sum(row[self.feesColumns])
            else:
                feesDue = 0

            availcash = availcash - feesDue

            row[("AvailCash", "afterFees")] = availcash

            # *********************** Facility Fee & Debt Coupon ***********************

            # facility fee and coupon due
            row[self.capTable.classColumnsGroup("undrawnFeeDue")] = (
                np.array(row[self.capTable.classColumnsGroup("bopUndrawnAmount")])
                * np.array(self.capTable.capitalStructure['undrawnFee'])
                / 12.0
            )

            row[self.capTable.classColumnsGroup("couponDue")] = (
                np.array(row[self.capTable.classColumnsGroup("bopBal")])
                * np.array(self.capTable.capitalStructure['coupon'])
                / 12.0
            )

            for lender in self.capTable.effectiveClass:

                # pay undrawn fee
                row[(lender, "undrawnFeePaid")] = min(
                    availcash, row[(lender, "undrawnFeeDue")]
                )
                row[(lender, "undrawnFeeShortfall")] = (
                    row[(lender, "undrawnFeeDue")] - row[(lender, "undrawnFeePaid")]
                )
                availcash = availcash - row[(lender, "undrawnFeePaid")]

                # pay coupon
                row[(lender, "couponPaid")] = min(availcash, row[(lender, "couponDue")])

                row[(lender, "couponShortfall")] = (
                    row[(lender, "couponDue")] - row[(lender, "couponPaid")]
                )
                availcash = availcash - row[(lender, "couponPaid")]

            row[("AvailCash", "afterDebtCoupon")] = availcash


            # *********************** Debt Principal ***********************

            # calculate principal payment requirement
            row[self.capTable.classColumnsGroup("eopFacilitySize")] = np.array(
                self.capTable.capitalStructure['facilitySize']
            ) * (i <= self.capTable.capitalStructure['commitPeriod'])

            row[self.capTable.classColumnsGroup("maxDrawAmount")] = np.minimum(
                np.array(row[self.capTable.classColumnsGroup("eopFacilitySize")]),
                row[("Facility", "adjAssetBal")]
                * self.capTable.capitalStructure['thickness']
                / 100.0,
            )

            row[self.capTable.classColumnsGroup("beforePaidDownBal")] = (
                np.array(row[self.capTable.classColumnsGroup("bopBal")])
                + np.array(row[self.capTable.classColumnsGroup("undrawnFeeShortfall")])
                + np.array(row[self.capTable.classColumnsGroup("couponShortfall")])
            )

            for lender in self.capTable.effectiveClass:
                if row[(lender, "maxDrawAmount")] > row[(lender, "beforePaidDownBal")]:
                    row[(lender, "newDrawn")] = (
                        row[(lender, "maxDrawAmount")]
                        - row[(lender, "beforePaidDownBal")]
                    )
                else:
                    row[(lender, "newDrawn")] = 0

            for lender in self.capTable.effectiveClass:
                if row[(lender, "maxDrawAmount")] <= row[(lender, "beforePaidDownBal")]:
                    row[(lender, "requiredPaidDown")] = (
                        row[(lender, "beforePaidDownBal")]
                        - row[(lender, "maxDrawAmount")]
                    )
                else:
                    row[(lender, "requiredPaidDown")] = 0

            # pay principal
            for lender in self.capTable.effectiveClass:
                row[(lender, "principalPaid")] = min(
                    availcash, row[(lender, "requiredPaidDown")]
                )

                availcash = availcash - row[(lender, "principalPaid")]

            row[("AvailCash", "afterDebtPrin")] = availcash


            # calculate eop balance and facility size
            row[self.capTable.classColumnsGroup("eopBal")] = (
                np.array(row[self.capTable.classColumnsGroup("beforePaidDownBal")])
                - np.array(row[self.capTable.classColumnsGroup("principalPaid")])
                + row[self.capTable.classColumnsGroup("newDrawn")]
            )

            row[self.capTable.classColumnsGroup("eopUndrawnAmount")] = np.maximum(
                0,
                np.array(row[self.capTable.classColumnsGroup("eopFacilitySize")])
                - np.array(row[self.capTable.classColumnsGroup("eopBal")]),
            )

            row[self.capTable.classColumnsGroup("overdrawnAmount")] = np.maximum(
                0,
                np.array(row[self.capTable.classColumnsGroup("eopBal")])
                - np.array(row[self.capTable.classColumnsGroup("eopFacilitySize")]),
            )



            # *********************** Residual Cashflow ***********************

            row[("Residual", "cashInvestment")] = -row[("Asset", "purchaseCash")] + sum(row[self.capTable.classColumnsGroup("newDrawn")])

            row[("Residual", "repaymentCash")] = availcash

            availcash = availcash - row[("Residual", "repaymentCash")]
            row[("AvailCash", "afterResidual")] = availcash

            row[("Residual", "investmentCF")] = (
                row[("Residual", "cashInvestment")] + row[("Residual", "repaymentCash")]
            )

            self.DealCashflow.loc[i] = row


        return self

    def buildSpecificAnalysis(self):
        
        # -calc- ******************* Debt Cost and Cashflow ******************* 
        self.DealCashflow[self.capTable.classColumnsGroup("debtCostDollar")] = np.array(
            (self.DealCashflow[self.capTable.classColumnsGroup("couponPaid")])
        ) + np.array(self.DealCashflow[self.capTable.classColumnsGroup("undrawnFeePaid")])
        
        self.DealCashflow[self.capTable.classColumnsGroup("totalCF")] = np.array(self.DealCashflow[self.capTable.classColumnsGroup("couponPaid")]) + np.array(self.DealCashflow[self.capTable.classColumnsGroup("principalPaid")])

        # -calc- ******************* Advance Rate ******************* 
        self.DealCashflow[self.capTable.classColumnsGroup("effectiveAdvRate")] = (
            np.array(self.DealCashflow[self.capTable.classColumnsGroup("eopBal")])
            / np.expand_dims(np.array(self.DealCashflow[("Asset", "eopBal")]), 1)
        ).cumsum(axis=1)

        self.DealCashflow[("Debt", "effectiveDebtCost")] = (
            np.array(self.DealCashflow[self.capTable.classColumnsGroup("debtCostDollar")].sum(axis=1))
            / np.array(
                self.DealCashflow[self.capTable.classColumnsGroup("bopBal")].sum(axis=1)
            )
            * 12.0
        )

        # -calc- ******************* Combine together debt CF ******************* 
        self.DealCashflow[self.capTable.classColumnsGroup("debtCF")] = np.array(
            self.DealCashflow[self.capTable.classColumnsGroup("principalPaid")]
        ) + np.array(self.DealCashflow[self.capTable.classColumnsGroup("debtCostDollar")])


        # -calc- ******************* Lending Facility ******************* 
        self.DealCashflow[
            ("Facility", "inCommitPeriod")
        ] = self.DealCashflow.index.to_series().apply(
            lambda x: 1 if x <= (self.capTable.capitalStructure['commitPeriod'].max()) else 0
        )

        self.DealCashflow[
            ("Facility", "commitEnd")
        ] = self.DealCashflow.index.to_series().apply(
            lambda x: 1 if x == (self.capTable.capitalStructure['commitPeriod'].max()) else 0
        )

        # -calc- ******************* Combine Debt ******************* 
        self.combineDebt("eopBal")
        self.combineDebt("debtCostDollar")
        self.combineDebt("principalPaid")
        self.combineDebt("debtCF")
        self.combineDebt("eopUndrawnAmount")
        

    def buildSpecificStats(self):


        # -calc- metrics
        self.StructureStats["metrics"]["facilityCommitPeriod"] = self.capTable.capitalStructure['commitPeriod'].max()

        prevEffAdv = 0
        for _class in self.capTable.effectiveClass:
            self.StructureStats["metrics"][f"{_class}_facilitySize"] = self.capTable.getTerm(_class, "facilitySize")
            
            self.StructureStats["metrics"][f"{_class}_commitPeriod"] = self.capTable.getTerm(_class, "commitPeriod")

            self.StructureStats["metrics"][f"{_class}_undrawnFee"] = self.capTable.getTerm(_class, "undrawnFee")

            self.StructureStats["metrics"][f"{_class}_couponCollected"] = self.DealCashflow[(_class, "couponPaid")].sum()

            self.StructureStats["metrics"][f"{_class}_undrawnFeeCollected"] = self.DealCashflow[(_class, "undrawnFeePaid")].sum()

            self.StructureStats["metrics"][f"{_class}_effectiveAdvRate"] = prevEffAdv + self.DealCashflow[(_class, "eopBal")].sum() / self.DealCashflow[("Asset", "eopBal")].sum()
            
            prevEffAdv = self.StructureStats["metrics"][f"{_class}_effectiveAdvRate"]


        self.StructureStats["metrics"]["debtCostCollected"] = \
            self.DealCashflow[self.capTable.classColumnsGroup("couponPaid")].sum().sum()\
                + \
                    self.DealCashflow[self.capTable.classColumnsGroup("undrawnFeePaid")].sum().sum()
                
        

        self.StructureStats["metrics"]["residCashflow"] = self.DealCashflow[("Residual", "repaymentCash")].sum().sum()
        self.StructureStats["metrics"]["assetNetYield"] = npf.irr(self.asset.rampCashflow["investmentCash"].values) * 12


        self.StructureStats["metrics"]["assetNetYieldPostFees"] = npf.irr(
                    self.DealCashflow[("Asset", "investmentCashDeductFees")].values
                ) * 12

        self.StructureStats["metrics"]["debtCost"] = self.DealCashflow[("Debt", "debtCostDollar")].sum() / self.DealCashflow[("Debt", "eopBal")].sum() * 12

        self.StructureStats["metrics"]["leverageRatio"] = 1.0 / (1 - self.StructureStats["metrics"]["effectiveAdvRate"] / 100.0)

        self.StructureStats["metrics"]["NIM"] = self.StructureStats["metrics"]["assetNetYieldPostFees"] \
                - self.StructureStats["metrics"]["debtCost"] \
                * self.StructureStats["metrics"]["effectiveAdvRate"] \
                / 100.0

        self.StructureStats["metrics"]["impliedROE"] = self.StructureStats["metrics"]["NIM"] * self.StructureStats["metrics"]["leverageRatio"]

        self.StructureStats["metrics"]["assetPurchased"] = self.DealCashflow[("Asset", "purchaseBalance")].sum()

        self.StructureStats["metrics"]["peakDebt"] = self.DealCashflow[("Debt", "eopBal")].max()

        self.StructureStats["metrics"]["peakDebtPeriod"] = self.DealCashflow[("Debt", "eopBal")].idxmax()

        self.StructureStats["metrics"]["debtPaidDownPeriod"] = self.DealCashflow[("Debt", "eopBal")].idxmin()

        self.StructureStats["metrics"]["residROE"] = npf.irr(self.DealCashflow[("Residual", "investmentCF")].values) * 12

        self.StructureStats["metrics"]["residPnL"] = self.DealCashflow[("Residual", "investmentCF")].sum()



        # -calc- filtered metrics
        for k in ['debtCost', 'effectiveAdvRate', "assetNetYieldPostFees","debtCost", "effectiveAdvRate", "NIM", "leverageRatio", "impliedROE",
                  "assetPurchased", "peakDebt","peakDebtPeriod", "debtPaidDownPeriod", "residInvestmented", "residYield","residMOIC"]:
            self.StructureStats["filteredMetrics"].update({k:self.StructureStats["metrics"][k]})
        
        for k in ["remainingFactor", "wal", "paywindow"]:
            for _class in self.capTable.effectiveClass:
                classK = f"{_class}_{k}"
                self.StructureStats["filteredMetrics"].update({classK:self.StructureStats["metrics"][classK]})


    def getCapitalStack(self):
        super().getCapitalStack()
        
        df = pd.DataFrame(columns = ["class", "commitPeriod", "facilitySize", "coupon", "undrawnFee", "paywindow", "advRate", "effectiveAdvRate"])
        for _class in self.capTable.effectiveClass:
            df.loc[len(df)] = [
                _class,
                self.capTable.getTerm(_class, "commitPeriod"),
                self.capTable.getTerm(_class, "facilitySize"),
                self.capTable.getTerm(_class, "coupon"),
                self.capTable.getTerm(_class, "undrawnFee"),
                self.StructureStats["metrics"][f"{_class}_paywindow"],
                self.capTable.getTerm(_class, "advRate"),
                self.StructureStats["metrics"][f"{_class}_effectiveAdvRate"],
            ]
            
        return df

# ************************************************************************************************************************

DEALCOLUMNS = {}

DEALCOLUMNS['Facility'] = [
    "adjAssetBal"
    ]

DEALCOLUMNS['Fees'] = ['trustee',
                       'verificationAgent',
                       'backupServicer',
                       'trusteeFixed'
                       ]

DEALCOLUMNS['Debt'] = [
                    "bopFacilitySize",
                    "bopBal",
                    "bopUndrawnAmount",
                    "undrawnFeeDue",
                    "undrawnFeePaid",
                    "undrawnFeeShortfall",
                    "couponDue",
                    "couponPaid",
                    "couponShortfall",
                    "newDrawn",
                    "beforePaidDownBal",
                    "requiredPaidDown",
                    "principalPaid",
                    "eopUndrawnAmount",
                    "overdrawnAmount",
                    "eopBal",
                    "eopFacilitySize",
                    "maxDrawAmount"   
                ]


DEALCOLUMNS['Residual'] = ["cashInvestment", "repaymentCash", "investmentCF"]

DEALCOLUMNS['AvailCash'] = [
                "fromAsset",
                "afterFees",
                "afterDebtCoupon",
                "afterDebtPrin",
                "afterResidual",
            ]
