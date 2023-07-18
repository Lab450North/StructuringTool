import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from PyPDF2 import PdfMerger

class ABSStructureCompChartingUtils:
    def __init__(self, ABSStructList, ABSStructNames, pdfFile):
        self.ABSStructList = ABSStructList
        self.ABSStructNames = ABSStructNames
        self.pdfFile = pdfFile
    
    def plotStructureComp(self):
        # 4: 18, 10
        fig, ax = plt.subplots(len(self.ABSStructList),6, figsize=(20,10))
        fig.suptitle('Financing Structure Comp', fontsize=15)
        for i in range(0, len(self.ABSStructList)):
            _absStruct = self.ABSStructList[i]
            _absStructName = self.ABSStructNames[i]

            ax[i,0].axis('off')
            capStackDf  = _absStruct.baseCase['ABSCapitalStack']
            capStackDf = capStackDf.drop("size", axis = 1)
            _1 = ax[i,0].table(cellText=capStackDf.values,colLabels=capStackDf.columns,loc='center')
            ax[i,0].set_title(f"{str(_absStructName)} Structure")
        
            balDf = _absStruct.baseCase['ABSStatsDict']['ts_metrics']['balances'].copy()
            balDf.plot(y=('Asset','eopBal'), ax = ax[i,1], grid = True)
            balDf.drop(('Asset','eopBal'), axis = 1).plot.area(ax = ax[i,1], grid = True, stacked = True, title="Debt Balance")
            
            _absStruct.baseCase['ABSStatsDict']['ts_metrics']['effectiveAdv'].plot(ax = ax[i,2], grid = True, title="Adv Rate")
            
            cfDf = _absStruct.baseCase['ABSStatsDict']['ts_metrics']['totalCF'].copy()
            cfDf.plot(y=('Asset','totalCF'), ax = ax[i,3], grid = True)
            cfDf.drop(('Asset','totalCF'), axis = 1).plot.area(ax = ax[i,3], grid = True, stacked = True, title="Total CF")


            cnlCurves = _absStruct.baseStructCollatMoveRes['cnlCurves']
            cnlCurves.plot(y = "cnlTrigger", ax = ax[i,4], grid = True, title="CNL Curve", style = "--")
            cnlCurves = cnlCurves.drop("cnlTrigger", axis = 1)
            max_columns = 5
            if len(cnlCurves.columns) < max_columns:
                cnlCurves.plot(ax = ax[i,4], grid = True)
            else:
                step = len(cnlCurves.columns) // (max_columns - 1)
                cols_to_print = [cnlCurves.columns[i*step] for i in range(max_columns-1)]  # take evenly spaced columns
                cols_to_print.append(cnlCurves.columns[-1])
                cnlCurves[cols_to_print].plot(ax = ax[i,4], grid = True)
            
            breakevenCnlMult = _absStruct.baseStructCollatMoveRes['breakevenCnlMult'].copy()
            breakevenCnlMult[['breakCnl', "cnlMultiple", "class"]].plot.scatter(x="cnlMultiple", y="breakCnl", ax = ax[i,5], grid = True, title="Tranche Breakeven CNL Multiple")
            scenariosDf = _absStruct.baseStructCollatMoveRes['scenariosDf']

            for idx, row in  breakevenCnlMult.iterrows():
                ax[i,5].annotate(row['class'] + "(" + "{:.2f}x".format(row['cnlMultiple']) + ")", (row['cnlMultiple'] + 0 , row['breakCnl'] - 0.03))
                ax[i,5].set_xlim(scenariosDf[['cnlMultiple']].min()[0], scenariosDf[['cnlMultiple']].max()[0])
                ax[i,5].set_ylim(scenariosDf[['cnl']].min()[0], scenariosDf[['cnl']].max()[0])

            
        for _ in ax.flat:
            _.legend(fontsize="6")
            _.set(xlabel = None)
                                
        plt.tight_layout()
        plt.savefig(self.pdfFile, format="pdf", bbox_inches="tight")


class ABSChartingUtils:
    def __init__(self, TermABSStruct, pdfFile):
        self.TermABSStruct = TermABSStruct
        self.pdfFile = pdfFile

    def plotABS(self):
        pageNum = 1; pageFile = f"Page{pageNum}.pdf"

        # ****************** Page CollatEcon ******************
        figPageCollatEcon, axPageCollatEcon = plt.subplots(3,3, figsize=(10,8))
        figPageCollatEcon.suptitle('Collateral Credit Matrics Trend', fontsize=15)

        self.TermABSStruct.baseCase['collatStatsDict']['ts_metrics']['cdrCurve'].plot(x = "period", y = "cdrVector", ax = axPageCollatEcon[0,0], grid = True, title="CDR")
        self.TermABSStruct.baseCase['collatStatsDict']['ts_metrics']['cprCurve'].plot(x = "period", y = "cprVector", ax = axPageCollatEcon[0,1], grid = True, title = "CPR")
        self.TermABSStruct.baseCase['collatStatsDict']['ts_metrics']['dqCurve'].plot(x = "period", y = "dqVector", ax = axPageCollatEcon[1,0], grid = True, title = "DQ")
        self.TermABSStruct.baseCase['collatStatsDict']['ts_metrics']['sevCurve'].plot(x = "period", y = "sevVector", ax = axPageCollatEcon[1,1], grid = True, title = "SEV")
        self.TermABSStruct.baseCase['collatStatsDict']['ts_metrics']['cnlCurve'].plot(x = "period", y = "cnl", ax = axPageCollatEcon[2,0], grid = True, title = 'CNL')
        self.TermABSStruct.baseCase['collatStatsDict']['ts_metrics']['ltlCurve'].plot(x = "period", y = "ltl", ax  = axPageCollatEcon[2,1], grid = True, title = "Loss to Liquidation")
        
        axPageCollatEcon[0,2].axis('off')
        collatStatic  = self.TermABSStruct.baseCase['collatStats']
        _1 = axPageCollatEcon[0,2].table(cellText=collatStatic.values,colLabels=collatStatic.columns,loc='center')
        axPageCollatEcon[0,2].set_title("Collateral Economics")
        


        gs = axPageCollatEcon[1, 2].get_gridspec()
        # remove the underlying axes
        for ax in axPageCollatEcon[1:, -1]: ax.remove()
        axbig = figPageCollatEcon.add_subplot(gs[1:, -1])
        axbig.axis('off')
        
        collatYT = self.TermABSStruct.baseCase['collatYT']
        _2 = axbig.table(cellText=collatYT.values,colLabels=collatYT.columns,loc='center')
        axbig.set_title("Collateral Yield Table")
        
        for _ in axPageCollatEcon.flat:
            _.legend(fontsize="6")
            _.set(xlabel = None)

        plt.tight_layout()
        plt.savefig(pageFile, format="pdf", bbox_inches="tight")
        
        
        # ****************** Page LevEcon ******************
        pageNum += 1; pageFile = f"Page{pageNum}.pdf"
        
        figPageLevEcon, axPageLevEcon = plt.subplots(3,3, figsize=(10,8))
        figPageLevEcon.suptitle('Structure Credit Matrics Trend', fontsize=15)
        
        balDf = self.TermABSStruct.baseCase['ABSStatsDict']['ts_metrics']['balances'].copy()
        balDf.plot(y=('Asset','eopBal'), ax = axPageLevEcon[0,0], grid = True)
        balDf.drop(('Asset','eopBal'), axis = 1).plot.area(ax = axPageLevEcon[0,0], grid = True, stacked = True, title="Debt Balance")
        
        self.TermABSStruct.baseCase['ABSStatsDict']['ts_metrics']['effectiveAdv'].plot(ax = axPageLevEcon[1,0], grid = True, title="Adv RAte")
        
        cfDf = self.TermABSStruct.baseCase['ABSStatsDict']['ts_metrics']['totalCF'].copy()
        cfDf.plot(y=('Asset','totalCF'), ax = axPageLevEcon[2,0], grid = True)
        cfDf.drop(('Asset','totalCF'), axis = 1).plot.area(ax = axPageLevEcon[2,0], grid = True, stacked = True, title="Total CF")
        
        
        self.TermABSStruct.baseCase['ABSStatsDict']['ts_metrics']['CNLTest'].plot(y=("AMTriggerTest", "CNLTrigger"), ax = axPageLevEcon[0,1], grid = True, style = "--")
        self.TermABSStruct.baseCase['ABSStatsDict']['ts_metrics']['CNLTest'].plot(y=("AMTriggerTest", "CNLActual"), ax = axPageLevEcon[0,1], grid = True, style = "-", title="CNL Trigger")
        
        self.TermABSStruct.baseCase['ABSStatsDict']['ts_metrics']['CEBuild'].plot(ax = axPageLevEcon[1,1], grid = True, style = "-", title="OC Build")
        
        self.TermABSStruct.baseCase['ABSStatsDict']['ts_metrics']['ExcessSpread'].plot(ax = axPageLevEcon[2,1], grid = True, title="Excess Spread")

        for _ in axPageLevEcon.flat:
            _.set_xlim(self.TermABSStruct.ABSCashflow.index.values.min(), self.TermABSStruct.ABSCashflow.index.values.max())
            
                    
        
        axPageLevEcon[0,2].axis('off')
        capStackDf  = self.TermABSStruct.baseCase['ABSCapitalStack']
        _1 = axPageLevEcon[0,2].table(cellText=capStackDf.values,colLabels=capStackDf.columns,loc='center')
        # _1.auto_set_font_size(False); _1.set_fontsize(10)
        axPageLevEcon[0,2].set_title("Capital Structure") 
               
        gs = axPageLevEcon[1, 2].get_gridspec()
        # remove the underlying axes
        for ax in axPageLevEcon[1:, -1]: ax.remove()
        axbig = figPageLevEcon.add_subplot(gs[1:, -1])
        axbig.axis('off')
        
        leveredEcon = self.TermABSStruct.baseCase['ABSStats']
        _2 = axbig.table(cellText=leveredEcon.values,colLabels=leveredEcon.columns,loc='center')
        axbig.set_title("Levered Economics Summary")

        
        for _ in axPageLevEcon.flat:
            _.set(xlabel = None)
            _.legend(fontsize="6")
        
        plt.tight_layout()
        plt.savefig(pageFile, format="pdf", bbox_inches="tight")
        


        # ****************** Page CollatScenario ******************
        if self.TermABSStruct.baseStructCollatMoveRes is None:
            pass
        else:
            pageNum += 1; pageFile = f"Page{pageNum}.pdf"
            figPageCollatScenario, axPageCollatScenario = plt.subplots(3,3, figsize=(10,8))
            figPageCollatScenario.suptitle('Structure Test with Collateral Scenarios', fontsize=15)

            
            scenariosDf = self.TermABSStruct.baseStructCollatMoveRes['scenariosDf']
            breakevenCnlMult = self.TermABSStruct.baseStructCollatMoveRes['breakevenCnlMult']
            cnlCurves = self.TermABSStruct.baseStructCollatMoveRes['cnlCurves']
            lossTimingCurves = self.TermABSStruct.baseStructCollatMoveRes['lossTimingCurves']
            
            
            scenariosDf[['cnlMultiple','cnl']].plot.scatter(x="cnlMultiple", y="cnl", ax = axPageCollatScenario[0,0], grid = True, title="CNL vs CNL Multiple (base)")
            breakevenCnlMult[['breakCnl', "cnlMultiple", "class"]].plot.scatter(x="cnlMultiple", y="breakCnl", ax = axPageCollatScenario[0,1], grid = True, title="Tranche Breakeven CNL Multiple")

            for idx, row in  breakevenCnlMult.iterrows():
                axPageCollatScenario[0,1].annotate(row['class'] + "(" + "{:.2f}x".format(row['cnlMultiple']) + ")", (row['cnlMultiple'] + 0 , row['breakCnl'] - 0.01))

            # for i, txt in enumerate(breakevenCnlMult['class']):
            #     axPageCollatScenario[0,1].annotate(txt, (breakevenCnlMult.cnlMultiple.iat[i]+0, breakevenCnlMult.breakCnl.iat[i] - 0.02))

            cnlCurves.plot(y = "cnlTrigger", ax = axPageCollatScenario[0,2], grid = True, title="CNL Curve", style = "--")
            cnlCurves = cnlCurves.drop("cnlTrigger", axis = 1)
            max_columns = 5
            if len(cnlCurves.columns) < max_columns:
                cnlCurves.plot(ax = axPageCollatScenario[0,2], grid = True)
            else:
                step = len(cnlCurves.columns) // (max_columns - 1)
                cols_to_print = [cnlCurves.columns[i*step] for i in range(max_columns-1)]  # take evenly spaced columns
                cols_to_print.append(cnlCurves.columns[-1])
                cnlCurves[cols_to_print].plot(ax = axPageCollatScenario[0,2], grid = True)
            
            scenariosDf[['defaultShockMult','cnlMultiple']].plot.scatter(x="defaultShockMult", y="cnlMultiple", ax = axPageCollatScenario[1,0], grid = True, title="Curve Shock and CNL Multiple")
            
            lossTimingCurves.plot.area(ax = axPageCollatScenario[1,1], grid = True, stacked = True, title="Loss Timing Distribution")

            axPageCollatScenario[1,2].axis('off')
            
            collatBoundaryDf = pd.DataFrame(list(self.TermABSStruct.collatScenariosBoundary.items()), columns=['boundary', 'values'])
            _1 = axPageCollatScenario[1,2].table(cellText=collatBoundaryDf.values,colLabels=collatBoundaryDf.columns,loc='center')
            axPageCollatScenario[1,2].set_title("Collateral Scenarios Boundary")


            axPageCollatScenario[0,1].set_ylim(axPageCollatScenario[0,0].get_ylim())
            axPageCollatScenario[0,1].set_xlim(axPageCollatScenario[0,0].get_xlim())

            axPageCollatScenario[2,0].axis('off'); axPageCollatScenario[2,1].axis('off'); axPageCollatScenario[2,2].axis('off');
            
            for _ in axPageCollatScenario.flat:
                _.legend(fontsize="6")
            
            plt.tight_layout()
            plt.savefig(pageFile, format="pdf", bbox_inches="tight")


        merger = PdfMerger()
        for i in range(1, pageNum+1):
            pdf_file = f"Page{i}.pdf"        
            merger.append(pdf_file)
        self.pdfFile
        merger.write(self.pdfFile)
        merger.close()
        
        return self
        