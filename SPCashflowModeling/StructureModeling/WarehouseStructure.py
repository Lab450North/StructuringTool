import pandas as pd
import numpy as np
import numpy_financial as npf
import itertools
from copy import deepcopy
from Utils import SPCFUtils

# to be modeled
# exit (could be modeled on ramper level, instead of warehouse financing level)
# covenant breach


class WarehouseStructure:
    def __init__(self, rampPool, whTerms, exitDetails):
        self.rampPool = rampPool

        self.commitDetails = whTerms.get("commitDetails", {"period": 1})

        self.advRate = whTerms.get("advRate", {"Senior": 70, "Mezz": 85})

        self.coupon = whTerms.get("coupon", {"Senior": 0.05, "Mezz": 0.1})

        self.undrawnFee = whTerms.get("undrawnFee", {"Senior": 0.000, "Mezz": 0.000})

        self.facilitySize = whTerms.get(
            "facilitySize", {"Senior": 200 * 1e6, "Mezz": 100 * 1e6}
        )

        self.transactionFees = whTerms.get(
            "transactionFees",
            {
                "feeRatios": {
                    "trustee": 0.0025,
                    "verificationAgent": 0.0025,
                    "backupServicingStandby": 0.0025,
                },
                "feeDollars": {
                    "legalClosing": 100000,
                    "trustSetup": 5000,
                    "verificationAgentSetup": 5000,
                    "backupServicerSetup": 5000,
                },
            },
        )

        self.covenants = whTerms.get("covenants", {"CNL": [], "DQ": []})

        self.exitPeriods = exitDetails.get("exitPeriods", {"periods": []})
        self.exitPx = exitDetails.get("exitPx", {"netPx": []})
        self.exitCreditBox = exitDetails.get(
            "exitCreditBox",
            {
                "WALA": [],
                "DQ": [],
            },
        )

        self._enrichWhTerms()
        self._buildQuickLambda()
        self._extendCashflowFramework()
        self._buildCashflow()
        self._buildAnalysis()
        self._buildStats()
        self._formatStats()

    def _enrichWhTerms(self):
        self.upfrontFeesDollar = deepcopy(self.transactionFees["feeDollars"])
        self.periodicFeesRatio = deepcopy(self.transactionFees["feeRatios"])

        self.advRateConvert = {}
        pre_adv = 0
        for tranche, adv in self.advRate.items():
            advCut = adv - pre_adv

            if advCut > 0:
                self.advRateConvert[tranche] = advCut
            pre_adv = adv

        self.effectiveLender = [k for k, v in self.advRateConvert.items() if v > 0]
        return self

    def _buildQuickLambda(self):
        self.lenderColumnsGroup = lambda x: list(
            itertools.product(self.effectiveLender, [x])
        )

        self.lenderWhTerms = lambda x: [x[k] for k in self.effectiveLender]

        def combinDebtFunc(x):
            self.warehouseCashflow[("Debt", x)] = self.warehouseCashflow[
                self.lenderColumnsGroup(x)
            ].sum(axis=1)

        self.combineDebt = combinDebtFunc


        return self

    def _extendCashflowFramework(self):
        self.warehouseCashflow = self.rampPool.rampCashflow.copy().set_index(
            "rampPeriod"
        )

        # Asset Related Columns
        self.warehouseCashflow.columns = pd.MultiIndex.from_product(
            [["Asset"], self.warehouseCashflow.columns]
        )

        # Facility Additional Related Columns
        facilityColumns = list(
            itertools.product(
                ["Facility"],
                ["adjAssetBal"],
            )
        )
        self.warehouseCashflow[facilityColumns] = np.nan
        # reference work: use reindex
        # self.warehouseCashflow = self.warehouseCashflow.reindex(
        #     self.warehouseCashflow.columns.tolist() + facilityColumns,
        #     axis=1,
        # )

        # Fees Related Columns
        feesColumns = list(
            itertools.product(
                ["Fees"],
                list(self.transactionFees["feeRatios"].keys())
                + list(self.transactionFees["feeDollars"].keys()),
            )
        )
        self.warehouseCashflow[feesColumns] = np.nan

        # Lenders Related Columns
        lenderColumns = list(
            itertools.product(
                self.effectiveLender,
                [
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
                    "paidDownPrin",
                    "eopUndrawnAmount",
                    "overdrawnAmount",
                    "eopBal",
                    "eopFacilitySize",
                    "maxDrawAmount",
                ],
            )
        )

        self.warehouseCashflow[lenderColumns] = np.nan

        # Residual Related Columns
        residualColumns = list(
            itertools.product(
                ["Residual"], ["cashInvestment", "repaymentCash", "investmentCF"]
            )
        )

        self.warehouseCashflow[residualColumns] = np.nan

        # Available Cashflow Helper Dataframe
        self.availCashflowHelper = pd.DataFrame(
            columns=[
                "fromAsset",
                "afterFees",
                "afterDebtCoupon",
                "afterDebtPrin",
                "afterResidual",
            ],
            index=self.warehouseCashflow.index,
        )

        # subset of useful quick reference columns
        self.bopColumns = [
            col
            for col in self.warehouseCashflow.columns
            if ("bop" in col[1]) & (col[0] != "Asset")
        ]

        self.eopColumns = [
            (col[0], col[1].replace("bop", "eop")) for col in self.bopColumns
        ]

        self.periodicFeesRatioColumns = list(
            itertools.product(["Fees"], self.periodicFeesRatio.keys())
        )

        self.upfrontFeesDollarColumns = list(
            itertools.product(["Fees"], self.upfrontFeesDollar.keys())
        )

        self.feesColumns = self.periodicFeesRatioColumns + self.upfrontFeesDollarColumns

    def _buildCashflow(self):

        # loop through rampPeriod to calculate periodic cashflow
        for i, row in self.warehouseCashflow.iterrows():
            availCashCF = {}
            availcash = 0

            if i == 0:
                # set facility initial status
                row[self.bopColumns] = 0

            else:
                # set bop balance
                row[self.bopColumns] = np.array(
                    self.warehouseCashflow.loc[i - 1, self.eopColumns]
                )

            availcash = row[("Asset", "repaymentCash")]
            availCashCF["fromAsset"] = availcash

            # facility : adjusted balance
            row[("Facility", "adjAssetBal")] = np.maximum(
                0, np.array(row[("Asset", "eopBal")] - row[("Asset", "dqBal")])
            )

            # set upfront fees
            row[self.upfrontFeesDollarColumns] = np.array(
                [*self.upfrontFeesDollar.values()]
            ) * (i == 0)

            # periodic fees
            row[self.periodicFeesRatioColumns] = (
                row[("Asset", "bopBal")]
                * np.array(list(self.periodicFeesRatio.values()))
                / 12.0
            )

            # trick here:
            # if no cashflow from asset, fees paid from residual pocket
            # otherwise from asset, i.e. top of waterfall distribution

            feesDue = sum(row[self.feesColumns])
            if availcash == 0:
                row[("Residual", "cashInvestment")] = -feesDue
            else:
                row[("Residual", "cashInvestment")] = 0
                availcash = availcash - feesDue

            availCashCF["afterFees"] = availcash

            # facility fee and coupon due
            row[self.lenderColumnsGroup("undrawnFeeDue")] = (
                np.array(row[self.lenderColumnsGroup("bopUndrawnAmount")])
                * np.array(self.lenderWhTerms(self.undrawnFee))
                / 12.0
            )

            row[self.lenderColumnsGroup("couponDue")] = (
                np.array(row[self.lenderColumnsGroup("bopBal")])
                * np.array(self.lenderWhTerms(self.coupon))
                / 12.0
            )

            for lender in self.effectiveLender:

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

            availCashCF["afterDebtCoupon"] = availcash

            # calculate principal payment requirement
            row[self.lenderColumnsGroup("eopFacilitySize")] = np.array(
                self.lenderWhTerms(self.facilitySize)
            ) * (i < self.commitDetails["period"])

            row[self.lenderColumnsGroup("maxDrawAmount")] = np.minimum(
                np.array(row[self.lenderColumnsGroup("eopFacilitySize")]),
                row[("Facility", "adjAssetBal")]
                * np.array([*self.advRateConvert.values()])
                / 100.0,
            )

            row[self.lenderColumnsGroup("beforePaidDownBal")] = (
                np.array(row[self.lenderColumnsGroup("bopBal")])
                + np.array(row[self.lenderColumnsGroup("undrawnFeeShortfall")])
                + np.array(row[self.lenderColumnsGroup("couponShortfall")])
            )

            for lender in self.effectiveLender:
                if row[(lender, "maxDrawAmount")] > row[(lender, "beforePaidDownBal")]:
                    row[(lender, "newDrawn")] = (
                        row[(lender, "maxDrawAmount")]
                        - row[(lender, "beforePaidDownBal")]
                    )
                else:
                    row[(lender, "newDrawn")] = 0

            for lender in self.effectiveLender:
                if row[(lender, "maxDrawAmount")] <= row[(lender, "beforePaidDownBal")]:
                    row[(lender, "requiredPaidDown")] = (
                        row[(lender, "beforePaidDownBal")]
                        - row[(lender, "maxDrawAmount")]
                    )
                else:
                    row[(lender, "requiredPaidDown")] = 0

            # pay principal
            for lender in self.effectiveLender:
                row[(lender, "paidDownPrin")] = min(
                    availcash, row[(lender, "requiredPaidDown")]
                )

                availcash = availcash - row[(lender, "paidDownPrin")]

            availCashCF["afterDebtPrin"] = availcash

            # calculate eop balance and facility size
            row[self.lenderColumnsGroup("eopBal")] = (
                np.array(row[self.lenderColumnsGroup("beforePaidDownBal")])
                - np.array(row[self.lenderColumnsGroup("paidDownPrin")])
                + row[self.lenderColumnsGroup("newDrawn")]
            )

            row[self.lenderColumnsGroup("eopUndrawnAmount")] = np.maximum(
                0,
                np.array(row[self.lenderColumnsGroup("eopFacilitySize")])
                - np.array(row[self.lenderColumnsGroup("eopBal")]),
            )

            row[self.lenderColumnsGroup("overdrawnAmount")] = np.maximum(
                0,
                np.array(row[self.lenderColumnsGroup("eopBal")])
                - np.array(row[self.lenderColumnsGroup("eopFacilitySize")]),
            )

            # residual cashflow
            row[("Residual", "cashInvestment")] = (
                -row[("Asset", "purchaseCash")]
                + sum(row[self.lenderColumnsGroup("newDrawn")])
                + row[("Residual", "cashInvestment")]
            )

            row[("Residual", "repaymentCash")] = availcash

            availcash = availcash - row[("Residual", "repaymentCash")]
            availCashCF["afterResidual"] = availcash

            row[("Residual", "investmentCF")] = (
                row[("Residual", "cashInvestment")] + row[("Residual", "repaymentCash")]
            )

            # row = row.fillna(0)
            rowAvailCashflow = [
                availCashCF[k] for k in list(self.availCashflowHelper.columns)
            ]

            self.warehouseCashflow.loc[i] = row
            self.availCashflowHelper.loc[i] = rowAvailCashflow

        return self

    def _buildAnalysis(self):

        self.warehouseCashflow[("Fees", "feesCollected")] = self.warehouseCashflow[
            self.feesColumns
        ].sum(axis=1)

        self.warehouseCashflow[("Asset", "investmentCashDeductFees")] = (
            self.warehouseCashflow[("Asset", "investmentCash")]
            - self.warehouseCashflow[("Fees", "feesCollected")]
        )

        self.warehouseCashflow[self.lenderColumnsGroup("effectiveAdvRate")] = (
            np.array(self.warehouseCashflow[self.lenderColumnsGroup("eopBal")])
            / np.expand_dims(np.array(self.warehouseCashflow[("Asset", "eopBal")]), 1)
        ).cumsum(axis=1)

        self.warehouseCashflow[self.lenderColumnsGroup("debtCostDollar")] = np.array(
            (self.warehouseCashflow[self.lenderColumnsGroup("couponPaid")])
        ) + np.array(self.warehouseCashflow[self.lenderColumnsGroup("undrawnFeePaid")])

        self.warehouseCashflow[self.lenderColumnsGroup("debtCF")] = np.array(
            self.warehouseCashflow[self.lenderColumnsGroup("paidDownPrin")]
        ) + np.array(self.warehouseCashflow[self.lenderColumnsGroup("debtCostDollar")])

        self.combineDebt("eopBal")
        self.combineDebt("debtCostDollar")
        self.combineDebt("paidDownPrin")
        self.combineDebt("debtCF")
        self.combineDebt("eopUndrawnAmount")

        self.warehouseCashflow[("Debt", "effectiveDebtCost")] = (
            np.array(self.warehouseCashflow[("Debt", "debtCostDollar")])
            / np.array(
                self.warehouseCashflow[self.lenderColumnsGroup("bopBal")].sum(axis=1)
            )
            * 12.0
        )

        self.warehouseCashflow[
            ("Facility", "inCommitPeriod")
        ] = self.warehouseCashflow.index.to_series().apply(
            lambda x: 1 if x <= self.commitDetails["period"] else 0
        )

        self.warehouseCashflow[
            ("Facility", "commitEnd")
        ] = self.warehouseCashflow.index.to_series().apply(
            lambda x: 1 if x == self.commitDetails["period"] else 0
        )

        return self

    def _buildStats(self):
        self.warehouseStats = {"metrics": {}, "ts_metrics": {}}

        # ts_metrics

        self.warehouseStats["ts_metrics"]["balances"] = self.warehouseCashflow[
            [("Asset", "eopBal")] + self.lenderColumnsGroup("eopBal")
        ]

        self.warehouseStats["ts_metrics"]["effectiveAdv"] = self.warehouseCashflow[
            self.lenderColumnsGroup("effectiveAdvRate")
        ]

        self.warehouseStats["ts_metrics"]["cashDistribution"] = self.warehouseCashflow[
            [
                ("Asset", "repaymentCash"),
                ("Debt", "debtCF"),
                ("Residual", "repaymentCash"),
            ]
        ]

        self.warehouseStats["ts_metrics"][
            "cashDistributionGranular"
        ] = self.warehouseCashflow[
            [("Asset", "repaymentCash"), ("Fees", "feesCollected")]
            + self.lenderColumnsGroup("debtCostDollar")
            + self.lenderColumnsGroup("paidDownPrin")
            + [("Residual", "repaymentCash")]
        ]

        # metrics
        self.warehouseStats["metrics"]["facilityCommitPeriod"] = {
            "value": self.commitDetails["period"],
            "format": "comma",
        }

        for lender in self.effectiveLender:
            self.warehouseStats["metrics"][f"{lender}_facilitySize"] = {
                "value": self.facilitySize[lender],
                "format": "comma",
            }

            self.warehouseStats["metrics"][f"{lender}_coupon"] = {
                "value": self.coupon[lender],
                "format": "pct2",
            }

            self.warehouseStats["metrics"][f"{lender}_undrawnFee"] = {
                "value": self.undrawnFee[lender],
                "format": "pct2",
            }

            self.warehouseStats["metrics"][f"{lender}_couponCollected"] = {
                "value": self.warehouseCashflow[(lender, "couponPaid")].sum(),
                "format": "comma",
            }

            self.warehouseStats["metrics"][f"{lender}_undrawnFeeCollected"] = {
                "value": self.warehouseCashflow[(lender, "undrawnFeePaid")].sum(),
                "format": "comma",
            }

        self.warehouseStats["metrics"]["totalCashflow"] = {
            "value": (self.warehouseCashflow[("Asset", "repaymentCash")].sum().sum()),
            "format": "comma",
        }

        self.warehouseStats["metrics"]["feesCashflow"] = {
            "value": (self.warehouseCashflow[self.feesColumns].sum().sum()),
            "format": "comma",
        }

        self.warehouseStats["metrics"]["debtCouponCashflow"] = {
            "value": (
                self.warehouseCashflow[self.lenderColumnsGroup("couponPaid")]
                .sum()
                .sum()
                + self.warehouseCashflow[self.lenderColumnsGroup("undrawnFeePaid")]
                .sum()
                .sum()
            ),
            "format": "comma",
        }

        self.warehouseStats["metrics"]["debtPrinCashflow"] = {
            "value": (self.warehouseCashflow[self.feesColumns].sum().sum()),
            "format": "comma",
        }

        self.warehouseStats["metrics"]["residCashflow"] = {
            "value": (
                self.warehouseCashflow[("Residual", "repaymentCash")].sum().sum()
            ),
            "format": "comma",
        }

        self.warehouseStats["metrics"]["assetNetYield"] = {
            "value": self.rampPool.rampStats["metrics"]["Unlevered Yield"],
            "format": "pct2",
        }

        self.warehouseStats["metrics"]["assetNetYieldPostFees"] = {
            "value": (
                npf.irr(
                    self.warehouseCashflow[("Asset", "investmentCashDeductFees")].values
                )
                * 12
            ),
            "format": "pct2",
        }

        self.warehouseStats["metrics"]["debtCost"] = {
            "value": (
                self.warehouseCashflow[("Debt", "debtCostDollar")].sum()
                / self.warehouseCashflow[("Debt", "eopBal")].sum()
                * 12
            ),
            "format": "pct2",
        }

        self.warehouseStats["metrics"]["effectiveAdvRate"] = {
            "value": (
                self.warehouseCashflow[("Debt", "eopBal")].sum()
                / self.warehouseCashflow[("Asset", "eopBal")].sum()
                * 100
            ),
            "format": "comma2",
        }

        self.warehouseStats["metrics"]["leverageRatio"] = {
            "value": 1
            / (1 - self.warehouseStats["metrics"]["effectiveAdvRate"]["value"] / 100.0),
            "format": "comma2",
        }

        self.warehouseStats["metrics"]["NIM"] = {
            "value": (
                self.warehouseStats["metrics"]["assetNetYieldPostFees"]["value"]
                - self.warehouseStats["metrics"]["debtCost"]["value"]
                * self.warehouseStats["metrics"]["effectiveAdvRate"]["value"]
                / 100.0
            ),
            "format": "pct2",
        }

        self.warehouseStats["metrics"]["impliedROE"] = {
            "value": (
                self.warehouseStats["metrics"]["NIM"]["value"]
                * self.warehouseStats["metrics"]["leverageRatio"]["value"]
            ),
            "format": "pct2",
        }

        self.warehouseStats["metrics"]["assetPurchased"] = {
            "value": self.warehouseCashflow[("Asset", "rampSize")].sum(),
            "format": "comma",
        }

        self.warehouseStats["metrics"]["peakDebt"] = {
            "value": self.warehouseCashflow[("Debt", "eopBal")].max(),
            "format": "comma",
        }

        self.warehouseStats["metrics"]["peakDebtPeriod"] = {
            "value": self.warehouseCashflow[("Debt", "eopBal")].idxmax(),
            "format": "comma",
        }

        self.warehouseStats["metrics"]["debtPaidDownPeriod"] = {
            "value": self.warehouseCashflow[("Debt", "eopBal")].idxmin(),
            "format": "comma",
        }

        self.warehouseStats["metrics"]["residROE"] = {
            "value": (
                npf.irr(self.warehouseCashflow[("Residual", "investmentCF")].values)
                * 12
            ),
            "format": "pct2",
        }

        self.warehouseStats["metrics"]["residPnL"] = {
            "value": self.warehouseCashflow[("Residual", "investmentCF")].sum(),
            "format": "comma",
        }

        self.warehouseStats["metrics"]["residInvestmented"] = {
            "value": -1.0
            * self.warehouseCashflow[("Residual", "cashInvestment")].sum(),
            "format": "comma",
        }

        self.warehouseStats["metrics"]["residMOIC"] = {
            "value": self.warehouseCashflow[("Residual", "repaymentCash")].sum()
            / self.warehouseStats["metrics"]["residInvestmented"]["value"],
            "format": "comma2",
        }

    def _formatStats(self):
        for k, v in self.warehouseStats["metrics"].items():

            self.warehouseStats["metrics"][k][
                "formatValue"
            ] = SPCFUtils.SPCFUtils.financeFormatNumber(v["value"], v["format"])

        self.formatWarehouseEcoStats = pd.DataFrame(
            self.warehouseStats["metrics"]
        ).T.reset_index()
        self.formatWarehouseEcoStats = self.formatWarehouseEcoStats[
            ["index", "formatValue"]
        ]
        self.formatWarehouseEcoStats = self.formatWarehouseEcoStats.rename(
            columns={"index": "metrics", "formatValue": "value"}
        )

        return self