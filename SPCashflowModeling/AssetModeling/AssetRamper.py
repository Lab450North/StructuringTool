import pandas as pd
import numpy as np

class AssetContainer:
    def __init__(self, notional, purchasePx, cashflow):
        self.next = None
        self.notional = notional
        self.purchasePx = purchasePx
        self.cashflow = cashflow

class AssetRamper:
    def __init__(self) -> None:
        self.assetCount = 0

    def popAsset(self):
        if self.assetCount == 0:
            return None
        else:
            asset = self.head
            self.head = self.head.next
            self.assetCount -= 1
            return asset

    def clearAllAsset(self):
        while self.assetCount > 0:
            self.popAsset()

    def appendAsset(self, notional, purchasePx, cashflow):
        if self.assetCount == 0:
            self.head = AssetContainer(notional, purchasePx, cashflow)
            self.tail = self.head
        else:
            self.tail.next = AssetContainer(notional, purchasePx, cashflow)
            self.tail = self.tail.next
        self.assetCount += 1
    
    def getAssetCount(self):
        return self.assetCount    
    
    def getAsset(self, periodIndex):
        if periodIndex >= self.assetCount:
            print("index out of bound")
            return None
        else:
            asset = self.head
            for _ in range(periodIndex):
                asset = asset.next
            return asset

    def aggregateCashflows(self):
        if self.assetCount == 0:
            return None

        concatCashflow = self.head.cashflow.copy()
        current_asset = self.head.next
        i = 1
        while current_asset is not None:

            cashflow = current_asset.cashflow.copy()
            cashflow.loc[:, 'period'] = cashflow['period'] + i

            concatCashflow = pd.concat([concatCashflow, cashflow])
            current_asset = current_asset.next
            i+=1
        
        concatCashflow = concatCashflow.groupby('period').sum().reset_index()
        if "periodYears" in concatCashflow.columns:
            concatCashflow.loc[:, "periodYears"] = np.floor_divide(concatCashflow.loc[:, "period"]-1, 12) + 1

        if "cumulativeInvestmentCash" in concatCashflow.columns:
            concatCashflow["cumulativeInvestmentCash"] = concatCashflow["investmentCash"].cumsum()

        if "cumulativeLossPrin" in concatCashflow.columns:
            concatCashflow["cumulativeLossPrin"] = concatCashflow["lossPrin"].cumsum()
            
        return concatCashflow