import pandas as pd
import numpy as np
import numpy_financial as npf
from AssetModeling.Asset import Asset


class AmortizationAsset(Asset):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.assetType = self.assumptionSet.get("assetType") 
        self.notional = self.assumptionSet.get("notional")
        self.term = self.assumptionSet.get("term")
        self.intRate = self.assumptionSet.get("intRate")
        self.cdrVector = self.assumptionSet.get("cdrVector")
        self.cprVector = self.assumptionSet.get("cprVector")
        self.sevVector = self.assumptionSet.get("sevVector")
        self.dqVector = self.assumptionSet.get("dqVector")
        self.totalDefault = self.assumptionSet.get("totalDefault")
        self.defaultTimingCurve = self.assumptionSet.get("defaultTimingCurve")
        self.servicingFeesRatio = self.assumptionSet.get("servicingFeesRatio")

        self.cashflow = self.buildCashflow()
        self.assetStats = self.buildStats()


    def buildCashflow(self, workingNotional = None, purchasePx = 100):
        workingNotional = self.notional if workingNotional is None else workingNotional

        amortSchedPeriodic = np.concatenate(
            [
                np.array([0]),
                npf.ppmt(
                    self.intRate / 12,
                    np.arange(self.term) + 1,
                    self.term,
                    -workingNotional,
                ),
            ]
        )
        periods = np.array(range(0, self.term + 1))
        # adjust periodYears, so that 0 convert to 0 rather than 1
        periodsYears = np.floor_divide(periods-1, 12) + 1
        # periodsYears = np.floor_divide(periods, 12) + 1
        cprVector = np.concatenate([np.array([0]), np.array(self.cprVector)])
        smmVector = 1 - (1 - cprVector) ** (1 / 12)
        sevVector = np.concatenate([np.array([0]), np.array(self.sevVector)])
        dqVector = np.concatenate([np.array([0]), np.array(self.dqVector)])

        if self.cdrVector is None:
            cdrVector = np.concatenate([np.array([0]), np.array([self.cdrVector] * self.term)])
            mdrVector = np.concatenate([np.array([0]), np.array([self.cdrVector] * self.term)])
        else:        
            cdrVector = np.concatenate([np.array([0]), np.array(self.cdrVector)])
            mdrVector = 1 - (1 - cdrVector) ** (1 / 12)

        if self.defaultTimingCurve is None:
            self.defaultTimingCurve = [self.defaultTimingCurve] * self.term
            
        defaultTimingVector = np.concatenate([np.array([0]), np.array(self.defaultTimingCurve)])
        

        cashflow = pd.DataFrame(
            list(
                zip(
                    periods,
                    periodsYears,
                    amortSchedPeriodic,
                    cdrVector,
                    mdrVector,
                    defaultTimingVector,
                    cprVector,
                    smmVector,
                    sevVector,
                    dqVector,
                )
            ),
            columns=[
                "period",
                "periodYears",
                "amortSchedPeriodic",
                "cdrVector",
                "mdrVector",
                "defaultTimingVector",
                "cprVector",
                "smmVector",
                "sevVector",
                "dqVector",
            ],
        )

        cashflow["amortBalPeriodic"] = (
            workingNotional - cashflow["amortSchedPeriodic"].cumsum()
        )
        cashflow["balFactor"] = (
            cashflow["amortBalPeriodic"]
            .div(cashflow["amortBalPeriodic"].shift())
            .fillna(1)
        )

        cashflow[
            [
                "bopBal",
                "perfBal",
                "dqBal",
                "prepayPrin",
                "intCF",
                "servicingFees",
                "netIntCF",
                "defaultPrin",
                "lossPrin",
                "recoveryPrin",
                "schedPrin",
                "prinCF",
                "eopBal",
            ]
        ] = np.nan
        cashflow[["servicingFeesRatio"]] = self.servicingFeesRatio

        for i, row in cashflow.iterrows():

            if row["period"] == 0:
                cashflow.loc[
                    i,
                    [
                        "bopBal",
                        "perfBal",
                        "dqBal",
                        "prepayPrin",
                        "intCF",
                        "servicingFees",
                        "netIntCF",
                        "defaultPrin",
                        "lossPrin",
                        "recoveryPrin",
                        "schedPrin",
                        "prinCF",
                    ],
                ] = 0
                cashflow.at[i, "eopBal"] = workingNotional
            else:
                cashflow.at[i, "bopBal"] = cashflow.loc[i - 1, "eopBal"]

                
                if np.isnan(cashflow.at[i, "mdrVector"]):
                    
                    cashflow.at[i, "defaultPrin"] = min((
                        workingNotional * cashflow.at[i, "defaultTimingVector"] * self.totalDefault
                    ), cashflow.at[i, "bopBal"])
                else:
                    cashflow.at[i, "defaultPrin"] = (
                        cashflow.at[i, "bopBal"] * cashflow.at[i, "mdrVector"]
                    )


                nonDefaultPrin = (
                    cashflow.at[i, "bopBal"] - cashflow.at[i, "defaultPrin"]
                )

                cashflow.at[i, "lossPrin"] = (
                    cashflow.at[i, "defaultPrin"] * cashflow.at[i, "sevVector"]
                )
                cashflow.at[i, "recoveryPrin"] = (
                    cashflow.at[i, "defaultPrin"] - cashflow.at[i, "lossPrin"]
                )

                cashflow.at[i, "perfBal"] = nonDefaultPrin * (
                    1 - cashflow.at[i, "dqVector"]
                )
                cashflow.at[i, "dqBal"] = nonDefaultPrin - cashflow.at[i, "perfBal"]

                cashflow.at[i, "intCF"] = cashflow.at[i, "perfBal"] * self.intRate / 12

                cashflow.at[i, "prepayPrin"] = (
                    cashflow.at[i, "perfBal"] * cashflow.at[i, "smmVector"]
                )
                cashflow.at[i, "schedPrin"] = (
                    nonDefaultPrin - cashflow.at[i, "prepayPrin"]
                ) * (1 - cashflow.at[i, "balFactor"])

                cashflow.at[i, "prinCF"] = (
                    cashflow.at[i, "schedPrin"]
                    + cashflow.at[i, "recoveryPrin"]
                    + cashflow.at[i, "prepayPrin"]
                )
                cashflow.at[i, "eopBal"] = (
                    cashflow.at[i, "bopBal"]
                    - cashflow.at[i, "schedPrin"]
                    - cashflow.at[i, "defaultPrin"]
                    - cashflow.at[i, "prepayPrin"]
                )

                servicingFeesDue = (
                    np.average([cashflow.at[i, "bopBal"], cashflow.at[i, "eopBal"]])
                    * cashflow.at[i, "servicingFeesRatio"]
                    / 12.0
                )
                cashflow.at[i, "servicingFees"] = min(cashflow.at[i, "intCF"], servicingFeesDue)

                cashflow.at[i, "netIntCF"] = (
                    cashflow.at[i, "intCF"] - cashflow.at[i, "servicingFees"]
                )
                        
        cashflow["grossTotalCF"] = cashflow["intCF"] + cashflow["prinCF"]
        cashflow["totalCF"] = cashflow["netIntCF"] + cashflow["prinCF"]

        cashflow["cumulativeLossPrin"] = cashflow["lossPrin"].cumsum()
        cashflow["cgl"] = cashflow["defaultPrin"].cumsum() / workingNotional
        cashflow["cnl"] = cashflow["cumulativeLossPrin"] / workingNotional
        cashflow["factor"] = cashflow["eopBal"] / workingNotional
        cashflow["ltl"] = cashflow["cnl"] / (1 - cashflow["factor"])

        if self.cdrVector is None:
            cashflow.loc[:, "mdrVector"] = cashflow.loc[:, "defaultPrin"] / cashflow.loc[:, "bopBal"]
            cashflow.loc[:, "cdrVector"] = cashflow.loc[:, "mdrVector"].apply(lambda x: 1 - (1 - x) ** (12))
        else:
            cashflow.loc[:, "defaultTimingVector"] = cashflow.loc[:, "defaultPrin"] / cashflow.loc[:, "defaultPrin"].sum()
        
        
        cashflow["purchaseBalance"] = np.concatenate([np.array([workingNotional]), np.array([0] * self.term)])
        cashflow["purchaseCash"] = np.concatenate([np.array([workingNotional * purchasePx / 100.0]), np.array([0] * self.term)])
        cashflow["investmentCash"] = -cashflow["purchaseCash"] + cashflow["totalCF"]
        cashflow["cumulativeInvestmentCash"] = cashflow["investmentCash"].cumsum()

        self.dollarColumns = [
            "bopBal",
            "eopBal",
            "perfBal",
            "dqBal",
            "prepayPrin",
            "intCF",
            "servicingFees",
            "netIntCF",
            "defaultPrin",
            "lossPrin",
            "recoveryPrin",
            "schedPrin",
            "prinCF",
            "grossTotalCF",
            "totalCF",
            "cumulativeLossPrin",
            "purchaseBalance",
            "purchaseCash",
            "investmentCash",
            "cumulativeInvestmentCash",
        ]
        return cashflow

    def buildStats(self):
        assetStats = {"metrics": {}, "ts_metrics": {}}
        assetStats["metrics"]["notional"] = self.notional
        assetStats["metrics"]["wal"] = (
            (self.cashflow["prinCF"] * self.cashflow["period"]).sum()
            / self.cashflow["prinCF"].sum()
            / 12.0
        )

        assetStats["metrics"]["intRate"] = self.intRate
        assetStats["metrics"]["term"] = self.term

        assetStats["metrics"]["intPmt"] = self.cashflow["intCF"].sum()
        assetStats["metrics"]["prinPmt"] = self.cashflow["prinCF"].sum()
        assetStats["metrics"]["totalPmt"] = self.cashflow["totalCF"].sum()

        assetStats["metrics"]["totalDefault"] = self.cashflow["defaultPrin"].sum()
        assetStats["metrics"]["totalLoss"] = self.cashflow["lossPrin"].sum()
        
        assetStats["metrics"]["cnl"] = self.cashflow["lossPrin"].sum() / self.notional
        assetStats["metrics"]["cgl"] = self.cashflow["defaultPrin"].sum() / self.notional
        
        assetStats["metrics"]["lossTiming"] = self.cashflow.groupby("periodYears")["lossPrin"].sum() / self.cashflow["lossPrin"].sum()
        assetStats["metrics"]["lossTiming"] = "/".join(map(lambda x: f'{x:.0f}', assetStats["metrics"]["lossTiming"].iloc[1:].values * 100))

        assetStats["metrics"]["defaultTiming"] = self.cashflow.groupby("periodYears")["defaultPrin"].sum() / self.cashflow["defaultPrin"].sum()
        assetStats["metrics"]["defaultTiming"] = "/".join(map(lambda x: f'{x:.0f}', assetStats["metrics"]["defaultTiming"].iloc[1:].values * 100))

        assetStats["ts_metrics"]["cdrCurve"] = self.cashflow[["period", "cdrVector"]]
        assetStats["ts_metrics"]["cprCurve"] = self.cashflow[["period", "cprVector"]]
        assetStats["ts_metrics"]["sevCurve"] = self.cashflow[["period", "sevVector"]]
        assetStats["ts_metrics"]["dqCurve"] = self.cashflow[["period", "dqVector"]]
        assetStats["ts_metrics"]["cnlCurve"] = self.cashflow[["period", "cnl"]]
        assetStats["ts_metrics"]["cnlLtLCurve"] = self.cashflow[["period", "cnl", "ltl"]]
        assetStats["ts_metrics"]["ltlCurve"] = self.cashflow[["period", "ltl"]]
        assetStats["ts_metrics"]["factorCurve"] = self.cashflow[["period", "factor"]]

        return assetStats

    def buildRampStats(self):
        rampAssetStats = {"metrics": {}, "ts_metrics": {}}
        rampAssetStats['metrics']['purchasePeriod'] = (self.rampCashflow['purchaseCash']>0).sum()
        rampAssetStats['metrics']['totalPurchaseBalance'] = self.rampCashflow['purchaseBalance'].sum()
        rampAssetStats['metrics']['totalPurchaseBasis'] = self.rampCashflow['purchaseCash'].sum()
        rampAssetStats['metrics']['avgPurchasePx'] = 100 * (
            rampAssetStats["metrics"]["totalPurchaseBasis"]
            / rampAssetStats["metrics"]["totalPurchaseBalance"]
        )
        rampAssetStats['metrics']['peakBalance'] = self.rampCashflow['eopBal'].max()
        rampAssetStats['metrics']['peakBalancePeriod'] = self.rampCashflow.loc[self.rampCashflow['eopBal'].idxmax(), 'period']
        rampAssetStats['metrics']['wal'] = (
            (self.rampCashflow["prinCF"] * self.rampCashflow["period"]).sum()
            / self.rampCashflow["prinCF"].sum()
            / 12.0
        )
        rampAssetStats['metrics']['breakevenPeriod'] = self.rampCashflow.loc[(self.rampCashflow['cumulativeInvestmentCash'] > 0).idxmax(), 'period']
        rampAssetStats['metrics']['totalPnL'] = self.rampCashflow['cumulativeInvestmentCash'].iloc[-1]
        rampAssetStats['metrics']['yield'] = npf.irr(self.rampCashflow["investmentCash"].values) * 12
        rampAssetStats['metrics']['moic'] = 1.0 + rampAssetStats['metrics']['totalPnL'] / rampAssetStats['metrics']['totalPurchaseBasis']

        rampAssetStats['ts_metrics']['periodicNetCF'] = self.rampCashflow[["period", "investmentCash"]]
        rampAssetStats['ts_metrics']['cumulativeCF'] = self.rampCashflow[["period", "cumulativeInvestmentCash"]]
        rampAssetStats['ts_metrics']['portfolioBalance'] = self.rampCashflow[["period", "eopBal"]]
        
        return rampAssetStats

