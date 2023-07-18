from AssetModeling.Asset import Asset
from AssetModeling import AssetStore
from StructureModeling.Structure import Structure
from StructureModeling import StructureStore
from DealManager.DealManager import DealManager
from Utils.SPCFUtils import SPCFUtils
import matplotlib.pyplot as plt

dealABCut = DealManager(dealName = "ABCutonConsumerLoan",
                    dealDescriptive = {"dealSubsector":"consumer loan",
                                       "dealSector":"Consumer",
                                       "assetOriginator":"SuperLoan"                                       
                        },
                    dealMisc = {"upfrontFees": 1e6},
                    assetScenarios = {"base": AssetStore.ASSETSTORE['consumerLoan58']},
                    financingTerms = StructureStore.STRUCTURESTORE['ABCut']
                    )

dealABCut.copyAssetWithNewAssumption("base", "frontLoad", {"defaultTimingCurve": SPCFUtils.timingCurveParse("50/35/10", term = 58)})
dealABCut.copyAssetWithNewAssumption("base", "backLoad", {"defaultTimingCurve": SPCFUtils.timingCurveParse("10/10/10", term = 58)})
dealABCut.addSeriesDefaultScenario(startingMultiple=1.0, endingMultiple=2.5, step=0.25)

print(dealABCut.getCapitalStack())
print("*" * 100)
print(dealABCut.getAssetStaticMetrics(pxList = range(100, 89, -1)))
print("*" * 100)
print(dealABCut.getStructureStaticMetrics())
print("*" * 100)
print(dealABCut.getAssetStaticMetrics(ramp = True))
