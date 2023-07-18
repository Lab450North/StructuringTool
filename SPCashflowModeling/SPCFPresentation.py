from AssetModeling.Asset import Asset
from AssetModeling.Storage import AssetStore
from StructureModeling.Structure import Structure
from StructureModeling.Storage import StructureStore
from DealManager.DealManager import DealManager
from Utils.SPCFUtils import SPCFUtils
import matplotlib.pyplot as plt
from tabulate import tabulate
tabulatePrint = lambda x: print(tabulate(x, headers='keys', tablefmt='psql'))

import warnings
warnings.filterwarnings("ignore")

dealConsumerLoanABS = DealManager(dealName = "UPST2302",
                    dealDescriptive = {"dealSubsector":"consumer loan",
                                       "dealSector":"Consumer",
                                       "assetOriginator":"Upstart"                                       
                        },
                    rampSchedule = {"ramp": "204", "px":100},
                    dealMisc = {"upfrontFees": 1e6},
                    assetScenarios = {"base": AssetStore.ASSETSTORE['consumerLoanUpstart2302']},
                    financingTerms = StructureStore.STRUCTURESTORE['ConsumerABS']
                    )

dealConsumerLoanABS.copyAssetWithNewAssumption("base", "frontLoad", {"defaultTimingCurve": SPCFUtils.timingCurveParse("50/35/10/5", term = 56)})
dealConsumerLoanABS.copyAssetWithNewAssumption("base", "backLoad", {"defaultTimingCurve": SPCFUtils.timingCurveParse("25/40/20/15", term = 56)})
dealConsumerLoanABS.addSeriesDefaultScenario(startingMultiple=1.5, endingMultiple=3.5, step=0.5)



print(dealConsumerLoanABS.getCapitalStack())
print("*" * 100)
print(dealConsumerLoanABS.getAssetStaticMetrics(pxList = range(100, 89, -1)))
print("*" * 100)
print(dealConsumerLoanABS.getStructureStaticMetrics())
print("*" * 100)
print(dealConsumerLoanABS.getAssetStaticMetrics(ramp = True))

